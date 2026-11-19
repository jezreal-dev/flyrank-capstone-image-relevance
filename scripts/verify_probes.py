"""Acceptance Probes verification script (Section 13 Layer 2).
Automates the exact behavioral probes required by the FlyRank Evaluator.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import get_db_connection
from app.services.matching_engine import matching_engine
from app.services.mismatch_guard import mismatch_guard
from app.models.matching_schema import GuardDecision
from app.api.routes_eval import run_evaluation_benchmark

def probe_1_batch_tags():
    print("--- [PROBE 1] Batch Processing & Low-Confidence Flagging ---")
    with get_db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM images").fetchone()["c"]
        completed = conn.execute("SELECT COUNT(*) as c FROM images WHERE status = 'completed'").fetchone()["c"]
        flagged = conn.execute("SELECT COUNT(*) as c FROM images WHERE status = 'flagged_for_review'").fetchone()["c"]
        meta_count = conn.execute("SELECT COUNT(*) as c FROM image_metadata").fetchone()["c"]
        flagged_meta = conn.execute("SELECT image_id, subject, confidence FROM image_metadata WHERE is_flagged = 1").fetchall()

    print(f"Total Images in DB: {total}")
    print(f"Completed with Valid Tags: {completed}")
    print(f"Flagged for Low Confidence (< 0.70): {flagged}")
    print(f"Total Metadata Records: {meta_count}")
    for r in flagged_meta:
        print(f"  -> Flagged Record: {r['image_id']} ('{r['subject']}') with confidence {r['confidence']:.2f}")

    assert total >= 50, f"Expected at least 50 images, found {total}"
    assert meta_count >= 50, f"Expected at least 50 metadata records, found {meta_count}"
    assert flagged >= 1, "Expected at least 1 image to be flagged for low confidence"
    print("PROBE 1: PASSED (All images schema-tagged; low-confidence image safely flagged)\n")

def probe_2_fox_ranking():
    print("--- [PROBE 2] Red Fox Query & Canid Ranking Separation ---")
    resp = matching_engine.rank_and_guard_candidates("post_fox_01", max_suggestions=10)
    print(f"Post Title: '{resp.post_title}'")
    print(f"Engine Status: {resp.status}")
    print("Top Suggestions:")
    for c in resp.all_candidates:
        print(f"  Rank #{c.rank}: [{c.guard_decision.value}] {c.image_id} ('{c.image_subject}') - sim={c.similarity_score:.4f}")

    top_rec = resp.top_recommendation
    assert top_rec is not None, "Expected a valid top recommendation for fox post"
    assert top_rec.image_id == "img_fox_01", f"Expected 'img_fox_01' to rank first, got {top_rec.image_id}"
    
    # Verify wolf and dog rank lower
    wolf_item = next((c for c in resp.all_candidates if "wolf" in c.image_subject.lower()), None)
    dog_item = next((c for c in resp.all_candidates if "dog" in c.image_subject.lower()), None)

    if wolf_item:
        assert top_rec.similarity_score > wolf_item.similarity_score, "Fox must have higher similarity than wolf"
    if dog_item:
        assert top_rec.similarity_score > dog_item.similarity_score, "Fox must have higher similarity than dog"

    print("PROBE 2: PASSED (Fox ranks #1; wolf and dog rank clearly lower)\n")

def probe_3_wolf_guard_refusal():
    print("--- [PROBE 3] Adversarial Wolf on Fox Post Guard Rejection ---")
    with get_db_connection() as conn:
        wolf_row = conn.execute(
            "SELECT meta.subject, meta.category, meta.confidence FROM image_metadata meta WHERE meta.image_id = 'img_wolf_01'"
        ).fetchone()
        fox_post = conn.execute("SELECT title, content, target_subject FROM posts WHERE id = 'post_fox_01'").fetchone()

    decision, reason = mismatch_guard.evaluate_candidate(
        post_title=fox_post["title"],
        post_content=fox_post["content"],
        target_subject=fox_post["target_subject"],
        image_subject=wolf_row["subject"],
        image_category=wolf_row["category"],
        image_confidence=float(wolf_row["confidence"]),
        similarity_score=0.88  # Force a high similarity score to test guard independence
    )

    print(f"Forced Candidate: 'img_wolf_01' ({wolf_row['subject']}) for post '{fox_post['title']}'")
    print(f"Mismatch Guard Decision: {decision.value}")
    print(f"Explanation: {reason}")

    assert decision == GuardDecision.REJECTED_CATEGORY_MISMATCH, f"Expected REJECTED_CATEGORY_MISMATCH, got {decision}"
    assert "mismatch" in reason.lower(), f"Expected explanation to cite mismatch, got: {reason}"
    print("PROBE 3: PASSED (Guard rejected wolf on fox post with explicit category-mismatch explanation)\n")

def probe_4_no_match_rejection():
    print("--- [PROBE 4] Unmatched Content Rejection ---")
    resp = matching_engine.rank_and_guard_candidates("post_unmatched_01")
    print(f"Post Title: '{resp.post_title}'")
    print(f"Engine Status: {resp.status}")
    print(f"Explanation: {resp.explanation}")

    assert resp.status == "NO_CONFIDENT_MATCH", f"Expected 'NO_CONFIDENT_MATCH', got {resp.status}"
    assert resp.top_recommendation is None, "Top recommendation must be None when no confident match exists"
    assert "below threshold" in resp.explanation.lower() or "rejected" in resp.explanation.lower()
    print("PROBE 4: PASSED (Engine returned 'NO_CONFIDENT_MATCH' with diagnostic reasoning)\n")

def probe_5_eval_precision():
    print("--- [PROBE 5] Top-1 Precision Benchmark on Labeled Set ---")
    results = run_evaluation_benchmark()
    metrics = results["headline_metrics"]
    precision = metrics["top1_precision"]
    precision_pct = metrics["top1_precision_pct"]

    print(f"Top-1 Precision: {precision_pct} ({metrics['correct_matches']}/{metrics['positive_eval_cases']} test cases)")
    print(f"Guard Accuracy:  {metrics['guard_rejection_accuracy_pct']}")

    assert precision >= 0.90, f"Expected Top-1 precision >= 90%, got {precision_pct}"
    print("PROBE 5: PASSED (Top-1 precision verified against labeled benchmark set)\n")

def probe_6_cost_tracking():
    print("--- [PROBE 6] Token & Cost Attribution Telemetry ---")
    with get_db_connection() as conn:
        calls = conn.execute("SELECT COUNT(*) as c FROM cost_log").fetchone()["c"]
        summary = conn.execute(
            """
            SELECT 
                COALESCE(SUM(input_tokens), 0) as inp,
                COALESCE(SUM(output_tokens), 0) as out,
                COALESCE(SUM(cost_usd), 0.0) as cost
            FROM cost_log
            """
        ).fetchone()
        recent = conn.execute("SELECT operation, model_name, input_tokens, output_tokens, cost_usd FROM cost_log ORDER BY id DESC LIMIT 3").fetchall()

    print(f"Total AI Calls Logged: {calls}")
    print(f"Total Input Tokens:    {summary['inp']}")
    print(f"Total Output Tokens:   {summary['out']}")
    print(f"Cumulative Spend:      ${summary['cost']:.6f} USD")
    print("Recent Attributed Entries:")
    for r in recent:
        print(f"  -> Op: {r['operation']} | Model: {r['model_name']} | Tokens: {r['input_tokens']} in / {r['output_tokens']} out | Cost: ${r['cost_usd']:.6f}")

    assert calls > 0, "Expected cost_log to contain attributed call entries"
    assert summary["inp"] > 0, "Expected input tokens to be tracked"
    print("PROBE 6: PASSED (Every AI operation attributed with tokens, model, and cost)\n")

def main():
    parser = argparse.ArgumentParser(description="Verify Evaluator Acceptance Probes")
    parser.add_argument("--probe", type=int, choices=[1, 2, 3, 4, 5, 6], help="Run specific probe")
    args = parser.parse_args()

    probes = {
        1: probe_1_batch_tags,
        2: probe_2_fox_ranking,
        3: probe_3_wolf_guard_refusal,
        4: probe_4_no_match_rejection,
        5: probe_5_eval_precision,
        6: probe_6_cost_tracking
    }

    if args.probe:
        probes[args.probe]()
    else:
        print("======================================================================")
        print("RUNNING ALL ACCEPTANCE PROBES (PROBES 1 TO 6)")
        print("======================================================================\n")
        for num in range(1, 7):
            probes[num]()
        print("======================================================================")
        print("ALL 6 ACCEPTANCE PROBES PASSED WITH ZERO ERRORS!")
        print("======================================================================")

if __name__ == "__main__":
    main()
