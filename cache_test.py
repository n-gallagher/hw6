"""Problem 4: run all 12 practice documents with and without the prompt cache.

Run:  python cache_test.py

Saves every model call from both setups to output/cache_test.json, with the setup,
document, every token count the API reports, and dollars from data/prices.json.
Then checks that each setup really did what it was meant to.
"""

import json
from datetime import datetime
from pathlib import Path

from agent import MODEL_NAME, run_document
from tools import OUTPUT_DIR

DOCS = sorted((Path(__file__).parent / "data" / "practice_docs").iterdir())
KEY = {k["file"]: k for k in json.loads((Path(__file__).parent / "data" / "practice_key.json").read_text())}
OUT = OUTPUT_DIR / "cache_test.json"

SETUPS = [("without_cache", "off"), ("with_cache", "on")]  # without first, so it can't borrow a warm cache


def main() -> None:
    calls, runs = [], []
    for setup, cache in SETUPS:
        print(f"\n=== {setup} ===")
        for path in DOCS:
            doc = f"data/practice_docs/{path.name}"
            run = run_document(doc, cache, "none")
            for c in run["model_calls"]:
                calls.append({"setup": setup, "document": path.name, "time": run["time"].isoformat(timespec="seconds"), **c})
            ans = run["answer"]
            correct = ans.decision == KEY[path.name]["decision"]
            runs.append({"setup": setup, "document": path.name, "decision": ans.decision,
                         "decision_matches_key": correct, "tokens": run["tokens"], "cost_usd": run["cost"]["total"]})
            t = run["tokens"]
            print(f"{path.name:30} calls={t['requests']} in={t['input_tokens']:>6,} cached={t['cached_tokens']:>6,} "
                  f"write={t['cache_write_tokens']:>6,} out={t['output_tokens']:>4} ${run['cost']['total']:.6f}")

    # Proof checks: did each setup do what it was meant to?
    off = [c for c in calls if c["setup"] == "without_cache"]
    on = [c for c in calls if c["setup"] == "with_cache"]
    checks = {
        "without_cache: total cached tokens (must be 0)": sum(c["cached_tokens"] for c in off),
        "without_cache: total cache-write tokens (must be 0)": sum(c["cache_write_tokens"] for c in off),
        "with_cache: calls that read the handbook from cache": sum(c["cached_tokens"] > 0 for c in on),
        "with_cache: calls that wrote the cache": sum(c["cache_write_tokens"] > 0 for c in on),
        "with_cache: total model calls": len(on),
        "all response ids unique (no gateway replays)": len({c["response_id"] for c in calls}) == len(calls),
    }

    OUT.write_text(json.dumps({
        "model": MODEL_NAME,
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "prices_per_1m": json.loads((Path(__file__).parent / "data" / "prices.json").read_text())[MODEL_NAME],
        "checks": checks,
        "runs": runs,
        "calls": calls,
    }, indent=2) + "\n", encoding="utf-8")

    print("\nChecks:")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    print(f"\nSaved {len(calls)} model calls to {OUT}")


if __name__ == "__main__":
    main()
