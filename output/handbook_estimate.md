# Handbook Estimate: Tokens and Cost

**File:** `data/shop_handbook.md` (the Campus Customs Shop Handbook)
**Model:** gpt-6-luna (prices from `data/prices.json`)

## Bottom line

| | Tokens | 1 call | 1,000 calls |
|---|---|---|---|
| **Without caching** | 10,058 | **$0.0010** | **$1.01** |
| **With caching** | 10,058 | $0.0013 (first call, writes the cache) / $0.0001 (later calls, read the cache) | **$0.10** |

Caching cuts the handbook's cost on 1,000 calls by about **90%**, from $1.01 to $0.10.

---

## 1. Token count: 10,058 tokens

### How I got it (ELI5)

A model doesn't read letters or whole words. It reads **tokens**, which are small chunks of text. A common word like "the" is one token. A long or unusual word gets split into pieces. Numbers, symbols and punctuation often count as tokens of their own.

To count tokens, you run the text through the same chopping tool (the **tokenizer**) that the model uses, then count the pieces.

**What I did:**
1. Loaded `data/shop_handbook.md`.
2. Ran it through OpenAI's tokenizer library, `tiktoken`, with the `o200k_base` encoding. That's the tokenizer for OpenAI's current models (GPT-4o and later). gpt-6-luna is an OpenAI model, and tiktoken has no entry for it by name, so this is the closest match.
3. Counted the pieces: **10,058 tokens.**

The script is `count_handbook_tokens.py`. Run it with `.venv/Scripts/python count_handbook_tokens.py`.

### Sanity checks

| Check | Result |
|---|---|
| Characters | 28,903 |
| Words | 6,127 |
| Tokens (o200k_base, current tokenizer) | **10,058** |
| Tokens (cl100k_base, older GPT-4 tokenizer) | 10,184 |
| Characters per token | 2.87 |

- The assignment says the handbook is "about 10,000 tokens," which matches.
- Plain English usually runs about 4 characters per token. This handbook runs only 2.87, because about two-thirds of it is tables. Pipes (`|`), SKU codes like `CC-HD-001`, prices like `$29.48` and dates all break into many small tokens.
- The old and new tokenizers differ by about 1%, so the count isn't sensitive to which tokenizer you pick.

---

## 2. How cached tokens work (ELI5)

Imagine handing the same 10,000-token handbook to the model before every question. Without caching, the model reads every page from scratch each time, and you pay full price each time.

With **prompt caching**, the model keeps its notes the first time it reads the handbook. On the next call, if the prompt **starts with the exact same text**, it uses those saved notes and doesn't read the handbook again. Reading saved notes is much cheaper.

The gpt-6-luna price list has three input prices:

| Price type | When you pay it | Price per 1M tokens |
|---|---|---|
| **Normal input** | Text the model reads fresh, with no caching | $0.10 |
| **Cache write** | The first time text is saved to the cache, a little **more** than normal | $0.125 |
| **Cached input (cache read)** | Every later call that reuses the saved text, **90% cheaper** than normal | $0.01 |
| Output | Text the model writes back (not part of the handbook estimate) | $0.50 |

**Rules that make caching work:**
- The cached part has to be at the **start** of the prompt and match **exactly**, down to the character. So the agent should send the handbook first and the vendor document after it. Changing even one character in the handbook breaks the match.
- The cache is temporary. It clears after a few minutes with no calls. If that happens in the middle of a run, the next call pays for another cache write.
- OpenAI only caches prompts of at least 1,024 tokens. At 10,058 tokens, the handbook is well over that.

---

## 3. Cost math

Prices are per **1 million** tokens, so first convert each price to a per-token price:

| Price type | Per 1M tokens | Per token |
|---|---|---|
| Normal input | $0.10 | $0.10 ÷ 1,000,000 = $0.0000001 |
| Cache write | $0.125 | $0.125 ÷ 1,000,000 = $0.000000125 |
| Cached input (read) | $0.01 | $0.01 ÷ 1,000,000 = $0.00000001 |

**Cost = tokens × price per token.** Every call sends the handbook's 10,058 tokens.

### Without caching

**One call:**
10,058 × $0.10 ÷ 1,000,000 = **$0.0010058** (about a tenth of a cent)

**1,000 calls:** each call pays full price.
$0.0010058 × 1,000 = **$1.0058** (about $1.01)

### With caching

**One call:** the first call has nothing to reuse yet, so it pays the cache **write** price.
10,058 × $0.125 ÷ 1,000,000 = **$0.0012573**

Each **later call** reads from the cache:
10,058 × $0.01 ÷ 1,000,000 = **$0.0001006** (about a hundredth of a cent)

So a single call by itself costs a little **more** with caching ($0.00126 vs $0.00101). The savings only show up once the handbook is reused.

**1,000 calls:** 1 cache write, then 999 cache reads.

| Step | Math | Cost |
|---|---|---|
| Call 1 (cache write) | 10,058 × $0.125 ÷ 1,000,000 | $0.0012573 |
| Calls 2–1,000 (999 cache reads) | 999 × 10,058 × $0.01 ÷ 1,000,000 | $0.1004794 |
| **Total** | $0.0012573 + $0.1004794 | **$0.1017** (about $0.10) |

### Side-by-side

| | 1 call | 1,000 calls |
|---|---|---|
| Without caching | $0.0010058 | $1.0058 |
| With caching | $0.0012573 (first call) / $0.0001006 (each later call) | $0.1017 |
| **Savings from caching** | n/a: one call alone costs 25% more | **$0.9041 saved (about 90%)** |

---

## 4. What to expect in Problem 4 (real runs)

- **Prompt tokens will be higher than 10,058.** A real call also sends the system instructions, the vendor document and a few formatting tokens. This estimate covers **the handbook alone**.
- **Output tokens are extra,** at $0.50 per 1M. They aren't counted here.
- **The reported cached-token count may be a little under 10,058.** OpenAI caches in blocks of 128 tokens, so a few tokens at the end of the cached part can be read at the normal price.
- **The first call won't show any cached tokens.** Cached tokens should appear on the calls after it, as long as they run within a few minutes and the handbook comes first in the prompt.
