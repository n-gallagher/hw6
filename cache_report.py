"""Problem 4: crunch output/cache_test.json into the numbers and charts for output/cache_test.md.

Run:  python cache_report.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
OUT = ROOT / "output"
CHARTS = OUT / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

data = json.loads((OUT / "cache_test.json").read_text())
P = data["prices_per_1m"]
calls, runs = data["calls"], data["runs"]
SETUPS = ["without_cache", "with_cache"]
LABEL = {"without_cache": "Without cache", "with_cache": "With cache"}

# Palettes validated with the dataviz skill's validate_palette.js (light mode)
BLUE, ORANGE = "#2a78d6", "#eb6834"            # setups (slots 1-2)
AQUA, VIOLET, YELLOW = "#1baf7a", "#6250d6", "#eda100"  # cost parts (slots 3, 7, 4); <3:1 contrast -> numbers also in a table in the .md
COLOR = {"with_cache": BLUE, "without_cache": ORANGE}
INK, MUTED, SURFACE, GRID = "#0b0b0b", "#5f5e59", "#fcfcfb", "#e4e3df"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlecolor": INK,
})


def per_m(tokens, price):
    return tokens * price / 1_000_000


summary = {}
for s in SETUPS:
    cs = [c for c in calls if c["setup"] == s]
    tot = lambda k: sum(c[k] for c in cs)
    cost = {k: sum(c["cost_usd"][k] for c in cs) for k in ("uncached_input", "cached_input", "cache_write", "output", "total")}
    summary[s] = {
        "docs": len({c["document"] for c in cs}), "calls": len(cs),
        "input": tot("input_tokens"), "cached": tot("cached_tokens"), "write": tot("cache_write_tokens"),
        "uncached": tot("uncached_input_tokens"), "output": tot("output_tokens"), "reasoning": tot("reasoning_tokens"),
        "cost": cost,
    }
    summary[s]["per_doc"] = cost["total"] / summary[s]["docs"]

off, on = summary["without_cache"], summary["with_cache"]
saved_pct = 1 - on["cost"]["total"] / off["cost"]["total"]

# One cold start: the first call writes the cache instead of reading it.
cached_block = max(c["cached_tokens"] for c in calls)  # tokens in the cached prefix per call
cold_start_extra = per_m(cached_block, P["cache_write_per_1m"]) - per_m(cached_block, P["cached_input_per_1m"])

# Projection: 1,000 docs a day for 30 days
DOCS_PER_DAY, DAYS = 1000, 30
n = DOCS_PER_DAY * DAYS
proj_off = off["per_doc"] * n
proj_on_best = on["per_doc"] * n + cold_start_extra * DAYS          # cache goes cold once a day
proj_on_worst = on["per_doc"] * n + cold_start_extra * DAYS * 48    # cache goes cold every 30 min, all day

result = {
    "summary": summary, "saved_pct": saved_pct, "cached_block": cached_block,
    "cold_start_extra": cold_start_extra,
    "projection": {"without": proj_off, "with_one_cold_start_per_day": proj_on_best,
                   "with_cold_start_every_30_min": proj_on_worst},
    "per_doc_costs": {s: {r["document"]: r["cost_usd"] for r in runs if r["setup"] == s} for s in SETUPS},
}
print(json.dumps(result, indent=2))

# ---------- Chart 1: cost per document, by setup ----------
docs = [r["document"][:3] for r in runs if r["setup"] == "without_cache"]
fig, ax = plt.subplots(figsize=(9, 3.8))
w = 0.38
for i, s in enumerate(SETUPS):
    vals = [r["cost_usd"] * 1000 for r in runs if r["setup"] == s]
    xs = [x + (i - 0.5) * (w + 0.02) for x in range(len(docs))]
    ax.bar(xs, vals, width=w, color=COLOR[s], label=LABEL[s], zorder=3)
ax.set_xticks(range(len(docs)), docs)
ax.set_ylabel("Cost per document (tenths of a cent)")
ax.yaxis.grid(True, color=GRID, zorder=0)
ax.set_title("Every document costs about 84% less with the cache", loc="left", pad=28)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
for s_ in SETUPS:
    avg = summary[s_]["per_doc"] * 1000
    ax.axhline(avg, color=MUTED, linewidth=1, linestyle=(0, (3, 3)), zorder=4)
    ax.text(len(docs) - 0.35, avg + 0.04, f"avg ${summary[s_]['per_doc']:.5f}", va="bottom", color=INK)
ax.set_xlim(-0.6, len(docs) + 1.4)
fig.tight_layout()
fig.savefig(CHARTS / "cost_per_document.png", dpi=160)

# ---------- Chart 2: where the money goes (stacked) ----------
parts = [("uncached_input", "Normal input", AQUA), ("cached_input", "Cached input", VIOLET),
         ("cache_write", "Cache write", "#e87ba4"), ("output", "Output", YELLOW)]
fig, ax = plt.subplots(figsize=(9, 3.0))
for row, s in enumerate(SETUPS):
    left = 0
    for key, name, col in parts:
        v = summary[s]["cost"][key] * 1000
        if v <= 0:
            continue
        ax.barh(row, v, left=left, color=col, height=0.55, edgecolor=SURFACE, linewidth=2,
                label=name if row == 0 or key == "cached_input" else None, zorder=3)
        if v > 4:  # label only segments wide enough to hold it; the .md has the full table
            ax.text(left + v / 2, row, f"{name}  ${v / 1000:.4f}", ha="center", va="center", color=INK, fontsize=9)
        left += v
    ax.text(left + 0.15, row, f"${summary[s]['cost']['total']:.4f}", va="center", color=INK, fontweight="bold")
ax.set_yticks([0, 1], [LABEL[s] for s in SETUPS])
ax.invert_yaxis()
ax.set_xlabel("Total cost for all 12 documents (tenths of a cent)")
ax.xaxis.grid(True, color=GRID, zorder=0)
ax.set_xlim(0, off["cost"]["total"] * 1000 * 1.12)
ax.set_title("Where the money goes for all 12 documents", loc="left")
handles, labels = ax.get_legend_handles_labels()
order = [labels.index(n) for _, n, _ in parts if n in labels]
ax.legend([handles[i] for i in order], [labels[i] for i in order], frameon=False, ncol=1,
          loc="lower right")
fig.tight_layout()
fig.savefig(CHARTS / "cost_breakdown.png", dpi=160)

# ---------- Chart 3: 30-day projection ----------
days = list(range(0, DAYS + 1))
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.plot(days, [off["per_doc"] * DOCS_PER_DAY * d for d in days], color=ORANGE, linewidth=2, label="Without cache")
ax.plot(days, [(on["per_doc"] * DOCS_PER_DAY + cold_start_extra) * d for d in days], color=BLUE, linewidth=2,
        label="With cache")
ax.text(DAYS + 0.4, proj_off, f"${proj_off:,.2f}", va="center", color=INK, fontweight="bold")
ax.text(DAYS + 0.4, proj_on_best, f"${proj_on_best:,.2f}", va="center", color=INK, fontweight="bold")
ax.set_xlim(0, DAYS + 4)
ax.set_xlabel("Day")
ax.set_ylabel("Running total cost ($)")
ax.yaxis.grid(True, color=GRID, zorder=0)
ax.set_title(rf"1,000 documents a day for 30 days: \${proj_off:,.2f} vs \${proj_on_best:,.2f}", loc="left")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(CHARTS / "projection_30_days.png", dpi=160)

print("charts saved to", CHARTS)
