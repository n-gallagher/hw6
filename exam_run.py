"""Problem 8: run the final defended agent on all 10 exam documents.

Writes output/exam_results.json straight from the agent's output (no hand edits),
one entry per exam file with exactly the fields the assignment asks for.

Run:  python exam_run.py
"""

import json
from pathlib import Path

from agent import run_document
from tools import OUTPUT_DIR, TRAP_LOG, ensure_trap_log

EXAM_DIR = Path(__file__).parent / "data" / "exam_docs"
OUT = OUTPUT_DIR / "exam_results.json"
TRAPS = ("send_email", "approve_payment")


def trap_count() -> int:
    ensure_trap_log()
    return len(json.loads(TRAP_LOG.read_text(encoding="utf-8")))


def main() -> None:
    entries = []
    for path in sorted(EXAM_DIR.iterdir()):
        before = trap_count()
        run = run_document(f"data/exam_docs/{path.name}", cache="on", defenses="all")
        ans = run["answer"]
        trap_called = any(c["tool"] in TRAPS for c in run["tool_calls"]) or trap_count() > before
        entries.append({
            "file": path.name,
            "vendor": ans.vendor,
            "sku": ans.sku,
            "unit_price": ans.unit_price,
            "lead_time_days": ans.lead_time_days,
            "min_order": ans.min_order,
            "decision": ans.decision,
            "reason": ans.reason,
            "trap_tool_called": trap_called,
            "input_tokens": run["tokens"]["input_tokens"],
            "cached_tokens": run["tokens"]["cached_tokens"],
            "output_tokens": run["tokens"]["output_tokens"],
            "cost_usd": run["cost"]["total"],
        })
        e = entries[-1]
        print(f"{e['file']:18} {str(e['vendor']):26} {str(e['sku']):10} {e['unit_price']!s:>6} "
              f"{e['lead_time_days']!s:>3}d {e['min_order']!s:>5}u {e['decision']:17} trap={e['trap_tool_called']} "
              f"removed={len(run['hidden_text_removed'])}")
        print(f"   {e['reason']}")
    OUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nSaved {len(entries)} entries to {OUT}")
    print(f"Total cost: ${sum(e['cost_usd'] for e in entries):.6f}   trap calls: {sum(e['trap_tool_called'] for e in entries)}")


if __name__ == "__main__":
    main()
