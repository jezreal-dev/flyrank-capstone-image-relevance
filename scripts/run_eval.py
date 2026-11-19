"""Command-line evaluation benchmark runner for Top-1 Precision & Mismatch Guard."""
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.api.routes_eval import run_evaluation_benchmark

def main():
    print("=" * 70)
    print("AI Image Matching Engine — Evaluation Benchmark Runner")
    print("=" * 70)

    results = run_evaluation_benchmark()
    metrics = results["headline_metrics"]

    print("\n[Headline Quality Metrics]")
    print(f"• Top-1 Precision:              {metrics['top1_precision_pct']} ({metrics['correct_matches']}/{metrics['positive_eval_cases']} positive articles)")
    print(f"• Mismatch Guard Accuracy:       {metrics['guard_rejection_accuracy_pct']} ({metrics['adversarial_cases_tested']} adversarial/out-of-domain cases)")

    print("\n[Individual Case Breakdown]")
    for c in results["case_details"]:
        eval_id = c["eval_id"]
        status = c["status"]
        test_type = c["test_type"]
        if "expected" in c:
            print(f"  [{status}] {eval_id} ({test_type}): expected={c['expected']} -> actual={c['actual']} (sim={c['similarity']:.3f})")
        else:
            print(f"  [{status}] {eval_id} ({test_type}): decision={c.get('guard_decision') or c.get('engine_status')}")

    print("\n" + "=" * 70)
    if metrics["top1_precision"] >= 0.90:
        print("RESULT: PASS — Top-1 precision meets production grading threshold (>= 90%).")
        sys.exit(0)
    else:
        print("RESULT: FAIL — Precision below target.")
        sys.exit(1)

if __name__ == "__main__":
    main()
