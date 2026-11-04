"""Problem 2: count how many tokens the shop handbook is, and what it costs.

Run:  .venv/Scripts/python count_handbook_tokens.py

gpt-6-luna is an OpenAI model. tiktoken has no entry for it by name, so we use
o200k_base, the tokenizer OpenAI uses for its current models (GPT-4o and later).
"""

import json
from pathlib import Path

import tiktoken

DATA = Path(__file__).parent / "data"

handbook = (DATA / "shop_handbook.md").read_text(encoding="utf-8")
prices = json.loads((DATA / "prices.json").read_text(encoding="utf-8"))["gpt-6-luna"]

enc = tiktoken.get_encoding("o200k_base")
tokens = len(enc.encode(handbook))

print(f"Characters: {len(handbook):,}")
print(f"Words:      {len(handbook.split()):,}")
print(f"Tokens (o200k_base): {tokens:,}")
print(f"Older tokenizer for comparison (cl100k_base): {len(tiktoken.get_encoding('cl100k_base').encode(handbook)):,}")
print(f"Characters per token: {len(handbook) / tokens:.2f}")
print()

per_token = {k: v / 1_000_000 for k, v in prices.items()}
uncached_one = tokens * per_token["input_per_1m"]
cache_write_one = tokens * per_token["cache_write_per_1m"]
cache_read_one = tokens * per_token["cached_input_per_1m"]

print(f"1 call, no caching:          ${uncached_one:.6f}")
print(f"1 call, writes the cache:    ${cache_write_one:.6f}")
print(f"1 call, reads from cache:    ${cache_read_one:.6f}")
print(f"1,000 calls, no caching:     ${uncached_one * 1000:.4f}")
print(f"1,000 calls, with caching:   ${cache_write_one + cache_read_one * 999:.4f}  (1 write + 999 reads)")
