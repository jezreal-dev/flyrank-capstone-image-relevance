"""API routes for running and querying the labeled evaluation precision benchmark."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.services.matching_engine import matching_engine
from app.models.matching_schema import GuardDecision
from app.core.database import get_db_connection

router = APIRouter(prefix="/api/eval", tags=["evaluation"])

@router.post("/run")
def run_evaluation_benchmark():
    """Executes evaluation across corpus/eval_set.json and returns Top-1 Precision metrics."""
    eval_file = Path(__file__).resolve().parent.parent.parent / "corpus" / "eval_set.json"
    if not eval_file.exists():
        raise HTTPException(status_code=404, detail="corpus/eval_set.json not found")

    with open(eval_file, "r") as f:
        cases = json.load(f)

    total_positive_cases = 0
    correct_top1_matches = 0
    guard_rejections_tested = 0
    guard_rejections_passed = 0
    case_results = []

    with get_db_connection() as conn:
        for case in cases:
            eval_id = case["eval_id"]
            test_type = case["test_type"]

            # Ensure post exists in database
            slug = f"eval-post-{eval_id}"
            post_row = conn.execute("SELECT id FROM posts WHERE slug = ?", (slug,)).fetchone()
            if not post_row:
                post_id = f"post_{eval_id}"
                conn.execute(
                    """
                    INSERT INTO posts (id, title, slug, content, target_subject)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (post_id, case["post_title"], slug, case["post_content"], case.get("target_subject"))
                )
                conn.commit()
            else:
                post_id = post_row["id"]

            # Run matching engine
            suggestions_resp = matching_engine.rank_and_guard_candidates(post_id)

            if test_type in ("positive_top1", "semantic_concept_equivalence"):
                total_positive_cases += 1
                expected_img = case["expected_top_image_id"]
                top_rec = suggestions_resp.top_recommendation
                
                matched = bool(top_rec and top_rec.image_id == expected_img)
                if matched:
                    correct_top1_matches += 1

                case_results.append({
                    "eval_id": eval_id,
                    "test_type": test_type,
                    "expected": expected_img,
                    "actual": top_rec.image_id if top_rec else None,
                    "status": "PASS" if matched else "FAIL",
                    "similarity": top_rec.similarity_score if top_rec else 0.0
                })

            elif test_type == "adversarial_guard_rejection":
                guard_rejections_tested += 1
                candidate_img_id = case["candidate_image_id"]
                
                # Fetch candidate image details and evaluate forced pairing
                cand_row = conn.execute(
                    """
                    SELECT meta.subject, meta.category, meta.confidence, emb.vector_json
                    FROM image_metadata meta
                    JOIN embeddings emb ON meta.image_id = emb.entity_id AND emb.entity_type = 'image'
                    WHERE meta.image_id = ?
                    """,
                    (candidate_img_id,)
                ).fetchone()

                post_vector = json.loads(conn.execute(
                    "SELECT vector_json FROM embeddings WHERE entity_type = 'post' AND entity_id = ?",
                    (post_id,)
                ).fetchone()["vector_json"])

                from app.core.vector_math import cosine_similarity
                from app.services.mismatch_guard import mismatch_guard
                cand_sim = cosine_similarity(post_vector, json.loads(cand_row["vector_json"]))

                decision, reason = mismatch_guard.evaluate_candidate(
                    post_title=case["post_title"],
                    post_content=case["post_content"],
                    target_subject=case.get("target_subject") or "red fox",
                    image_subject=cand_row["subject"],
                    image_category=cand_row["category"],
                    image_confidence=float(cand_row["confidence"]),
                    similarity_score=cand_sim
                )

                passed = bool(
                    decision != GuardDecision.ACCEPTED and
                    case["expected_reason_contains"].lower() in reason.lower()
                )
                if passed:
                    guard_rejections_passed += 1

                case_results.append({
                    "eval_id": eval_id,
                    "test_type": test_type,
                    "candidate_image_id": candidate_img_id,
                    "guard_decision": decision.value,
                    "explanation": reason,
                    "status": "PASS" if passed else "FAIL"
                })

            elif test_type == "no_match_rejection":
                guard_rejections_tested += 1
                passed = bool(
                    suggestions_resp.status == "NO_CONFIDENT_MATCH" and
                    case["expected_reason_contains"].lower() in suggestions_resp.explanation.lower()
                )
                if passed:
                    guard_rejections_passed += 1

                case_results.append({
                    "eval_id": eval_id,
                    "test_type": test_type,
                    "engine_status": suggestions_resp.status,
                    "explanation": suggestions_resp.explanation,
                    "status": "PASS" if passed else "FAIL"
                })

    top1_precision = (correct_top1_matches / total_positive_cases) if total_positive_cases > 0 else 0.0
    guard_accuracy = (guard_rejections_passed / guard_rejections_tested) if guard_rejections_tested > 0 else 0.0

    return {
        "headline_metrics": {
            "top1_precision": round(top1_precision, 4),
            "top1_precision_pct": f"{round(top1_precision * 100, 1)}%",
            "positive_eval_cases": total_positive_cases,
            "correct_matches": correct_top1_matches,
            "guard_rejection_accuracy_pct": f"{round(guard_accuracy * 100, 1)}%",
            "adversarial_cases_tested": guard_rejections_tested
        },
        "case_details": case_results
    }

@router.get("/latest")
def get_latest_evaluation():
    return run_evaluation_benchmark()
