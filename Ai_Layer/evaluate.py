"""Score the agent on a labelled test set: Recall@3 and no-match accuracy. Calls the model.

Usage: python Ai_Layer/evaluate.py [path/to/test_cases.json]
An empty expected_case_ids list (or expect_no_match) means the right answer is no match;
a null list means the question is unlabelled and is skipped.
"""
import json
from pathlib import Path
import sys

from agent import run_agent

HERE = Path(__file__).resolve().parent


def main(path=HERE.parent / "tests" / "test_cases.json"):
    rows = []
    for case in json.loads(Path(path).read_text(encoding="utf-8")):
        expected = case.get("expected_case_ids")
        if expected is None and not case.get("expect_no_match"):
            continue
        out = run_agent(case["question"])
        returned = [r["case_id"] for r in out["results"]][:3]
        passed = bool(set(returned) & set(expected)) if expected else not returned
        rows.append({"id": case.get("id"), "question": case["question"], "expected": expected or [],
                     "returned_top3": returned, "passed": passed, "reason": out["reason"]})
        print(f"{'PASS' if passed else 'MISS'} {case.get('id')}: expected {expected or 'no match'}, got {returned or 'no match'}")
    positive = [r for r in rows if r["expected"]]
    negative = [r for r in rows if not r["expected"]]
    report = {"test_set": str(path),
              "recall_at_3": sum(r["passed"] for r in positive) / len(positive) if positive else None,
              "no_match_accuracy": sum(r["passed"] for r in negative) / len(negative) if negative else None,
              "cases": rows}
    (HERE / "logs").mkdir(exist_ok=True)
    (HERE / "logs" / "evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Recall@3: {sum(r['passed'] for r in positive)}/{len(positive)}. "
          f"No-match: {sum(r['passed'] for r in negative)}/{len(negative)}. Details: Ai_Layer/logs/evaluation.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:2])
