"""Defense layer 2 (design): the purchasing decision is made in code, not by the model.

The model only reports facts (a FactSheet). This file:
  1. checks every fact against the document text the code itself read (grounding), and
  2. applies the four handbook purchasing checks using tables parsed from the handbook.
A document can lie to the model, but it cannot change the handbook or this code.
"""

import re
from functools import lru_cache
from pathlib import Path

from models import FactSheet, VendorDecision

HANDBOOK = Path(__file__).parent / "data" / "shop_handbook.md"
MAX_LEAD_DAYS = 21
MAX_MIN_ORDER = 600


@lru_cache
def handbook_tables() -> dict:
    """Approved vendors (section 5), removed/pending vendors (section 6), catalogue max costs (section 9)."""
    text = HANDBOOK.read_text(encoding="utf-8")
    sections = re.split(r"\n## ", text)
    sec = {m.group(1): s for s in sections if (m := re.match(r"(\d+)\.", s))}

    def rows(section: str) -> list[list[str]]:
        out = []
        for line in section.splitlines():
            if line.startswith("|") and not line.startswith("|---"):
                out.append([c.strip() for c in line.strip("|").split("|")])
        return out[1:]  # skip header

    approved = {r[1].lower(): r[1] for r in rows(sec["5"])}
    removed = {r[0].lower(): (r[0], r[1]) for r in rows(sec["6"])}
    catalogue = {r[0]: {"item": r[1], "max_cost": float(r[4].strip("$")), "vendor": r[5]} for r in rows(sec["9"])}
    return {"approved": approved, "removed": removed, "catalogue": catalogue}


def _grounded(value, doc_text: str, kind: str) -> bool:
    """Does the value really appear in the document text the code read?"""
    if value is None:
        return True
    t = doc_text.lower()
    if kind == "vendor":
        return str(value).lower() in t
    if kind == "sku":
        return str(value).upper() in doc_text.upper()
    if kind == "price":
        v = float(value)
        return any(abs(float(m) - v) < 0.005 for m in re.findall(r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)", doc_text.replace(",", "")))
    # whole numbers: lead time, minimum order
    return any(int(n.replace(",", "")) == int(value) for n in re.findall(r"\d[\d,]*", doc_text))


def decide(facts: FactSheet, doc_text: str) -> tuple[VendorDecision, list[str]]:
    """Apply the handbook rules in code. Returns the decision and a list of guardrail notes."""
    tables = handbook_tables()
    notes: list[str] = []

    # Grounding: a fact the code can't find in the document is treated as unknown.
    vendor, sku, price, lead, moq = facts.vendor, facts.sku, facts.unit_price, facts.lead_time_days, facts.min_order
    checks = [("vendor", vendor, "vendor"), ("sku", sku, "sku"), ("unit_price", price, "price"),
              ("lead_time_days", lead, "int"), ("min_order", moq, "int")]
    ungrounded = [name for name, val, kind in checks if not _grounded(val, doc_text, kind)]
    for name in ungrounded:
        notes.append(f"{name}={locals_map(facts)[name]!r} not found in the document text; treated as unknown")
    g = {name: (None if name in ungrounded else val) for name, val, _ in checks}

    def result(decision: str, reason: str) -> VendorDecision:
        return VendorDecision(vendor=facts.vendor, sku=facts.sku, unit_price=facts.unit_price,
                              lead_time_days=facts.lead_time_days, min_order=facts.min_order,
                              decision=decision, reason=reason)

    v = (g["vendor"] or "").strip().lower()
    # 1. Approved vendor
    if v in tables["removed"]:
        name, status = tables["removed"][v]
        return result("do_not_recommend",
                      f"Approved-vendor check failed: {name} is on the removed/pending list ({status.split('.')[0]})."), notes
    if v not in tables["approved"]:
        shown = facts.vendor or "unknown"
        return result("do_not_recommend",
                      f"Approved-vendor check failed: {shown} is not on the approved vendor list."), notes
    # 2. Price
    item = tables["catalogue"].get((g["sku"] or "").upper())
    if item is None:
        return result("do_not_recommend",
                      f"Price check failed: SKU {facts.sku or 'unknown'} is not in the catalogue, so there is no max unit cost to compare."), notes
    if g["unit_price"] is None:
        return result("do_not_recommend", f"Price check failed: the unit price for {facts.sku} is unknown."), notes
    if g["unit_price"] > item["max_cost"]:
        return result("do_not_recommend",
                      f"Price check failed: ${g['unit_price']:.2f} is above the ${item['max_cost']:.2f} max unit cost for {facts.sku}."), notes
    # 3. Lead time
    if g["lead_time_days"] is None:
        return result("do_not_recommend", "Lead-time check failed: the lead time is unknown."), notes
    if g["lead_time_days"] > MAX_LEAD_DAYS:
        return result("do_not_recommend",
                      f"Lead-time check failed: {g['lead_time_days']} days is more than the {MAX_LEAD_DAYS}-day limit."), notes
    # 4. Minimum order
    if g["min_order"] is None:
        return result("do_not_recommend", "Minimum-order check failed: the minimum order is unknown."), notes
    if g["min_order"] > MAX_MIN_ORDER:
        return result("do_not_recommend",
                      f"Minimum-order check failed: {g['min_order']} units is more than the {MAX_MIN_ORDER}-unit limit."), notes
    return result("recommend",
                  f"All four checks passed: {facts.vendor} is approved, ${g['unit_price']:.2f} is at or below the "
                  f"${item['max_cost']:.2f} max for {facts.sku}, {g['lead_time_days']} days is within {MAX_LEAD_DAYS}, "
                  f"and {g['min_order']} units is within {MAX_MIN_ORDER}."), notes


def locals_map(facts: FactSheet) -> dict:
    return facts.model_dump()
