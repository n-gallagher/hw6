# HW6: Campus Customs Vendor Desk Agent (Tokenomics + Prompt Injection)

A PydanticAI agent that reads one vendor document (HTML quote, PDF quote or `.eml` email), pulls out the vendor, SKU, unit price, lead time and minimum order, and decides `recommend` or `do_not_recommend` using the rules in the Campus Customs Shop Handbook. It runs **gpt-6-luna** through Portkey, and it's the only model used anywhere in this repo.

Open **`output/hw6_report.html`** in any browser for the full results page (one self-contained file, works offline).

## How to run the agent

**1. Set up (once).** Requires Python 3.12 or later.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

**2. Add your Portkey key.** Copy `.env.example` to `.env` and put your key in it:

```bash
copy .env.example .env          # Windows   (macOS/Linux: cp .env.example .env)
```

```
PORTKEY_API_KEY=your-portkey-key-here
```

**3. Run it on one vendor document:**

```bash
python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

It prints the answer, the tools used, the token counts and the cost, and appends to `output/usage_log.json` and `output/audit_trail.json`.

### Options

| Command | What it does |
|---|---|
| `python agent.py --doc <file>` | **Defended agent** (default): all three defense layers on, prompt cache on |
| `python agent.py --doc <file> --defenses none` | The original Problem 3 agent with **no defenses** (used in Problems 5 and 7) |
| `python agent.py --doc <file> --defenses code,prompt` | Any mix of the layers `code`, `design`, `prompt` |
| `python agent.py --doc <file> --cache off` | Turn off prompt caching (Problem 4) |

## Scripts for each problem

| Problem | Command | Output |
|---|---|---|
| 2 | `python count_handbook_tokens.py` | `output/handbook_estimate.md` |
| 4 | `python cache_test.py`, then `python cache_report.py` | `output/cache_test.json`, `output/cache_test.md` |
| 5 | `python attack_test.py` | `output/attack_results.json`, `.md` |
| 6 | `python defense_test.py` | `output/defense_results.json`, `.md` |
| 7 | `python make_attacks.py`, then `python red_team_test.py` | `data/my_attacks/`, `output/red_team.md` |
| 8 | `python exam_run.py` | `output/exam_results.json` |
| 9 | `python build_report.py` | `output/hw6_report.html` |
| Tests | `python tests/test_cleaner.py` | 24 checks of the hidden-text cleaner (no API key needed) |

## What's where

| Path | What it is |
|---|---|
| `agent.py` | Entry point: builds the agent, runs one document, writes the logs |
| `tools.py` | The document reader, the two **trap tools** (`send_email`, `approve_payment`, which only log to `output/trap_calls.json`), and the hidden-text cleaner (defense layer 1) |
| `models.py` | Structured output types: `VendorDecision` and `FactSheet` |
| `guardrails.py` | Defense layer 2: the handbook's purchasing checks, run in code |
| `prompts/prompt.md` | My instructions to the agent, including the safety rules (defense layer 3) |
| `data/` | Course data (handbook, prices, practice docs and key, exam docs) plus my two attack files in `data/my_attacks/` |
| `output/` | Every result and write-up; start with `harness.md` and `hw6_report.html` |
| `AI_prompts.md` | The log of what I typed to my vibe coder for each problem |

## Safety notes

- The real `.env` is **not** in this repo (`.gitignore` keeps it out). `.env.example` has placeholders only.
- `send_email` and `approve_payment` never send or pay anything. The defended agent isn't even connected to them; they're kept for a future human sign-off flow.
