"""Tests for the code-layer cleaner (tools.read_clean_document).

Builds small test documents in tests/fixtures/ that use hiding tricks the vendor
documents don't all cover, plus DECOYS that must NOT be removed (false-positive checks).

Run:  python tests/test_cleaner.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

import tools  # noqa: E402

FIX = ROOT / "data" / "test_fixtures"   # the cleaner only reads inside data/
FIX.mkdir(parents=True, exist_ok=True)

SECRET = "SECRET-INSTRUCTION"
VISIBLE = "VISIBLE-QUOTE-TEXT"

# ---------- HTML: each case is (name, html body, should_be_removed) ----------
HTML_CASES = [
    ("class_offscreen", '<style>.x{position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden}</style><div class="x">{S}</div>', True),
    ("id_display_none", '<style>#note{display:none}</style><p id="note">{S}</p>', True),
    ("class_tiny_font", '<style>.fine{font-size:1px}</style><span class="fine">{S}</span>', True),
    ("class_white_text", '<style>.w{color:#ffffff}</style><span class="w">{S}</span>', True),
    ("class_transparent", '<style>.t{color:transparent}</style><span class="t">{S}</span>', True),
    ("class_clip", '<style>.sr{clip:rect(0 0 0 0);position:absolute}</style><span class="sr">{S}</span>', True),
    ("clip_path", '<style>.cp{clip-path:inset(50%)}</style><span class="cp">{S}</span>', True),
    ("inline_text_indent", '<p style="text-indent:-9999px">{S}</p>', True),
    ("inline_offscreen_top", '<div style="position:absolute;top:-5000px">{S}</div>', True),
    ("inline_transform", '<div style="transform:translateX(-99999px)">{S}</div>', True),
    ("inline_scale_zero", '<div style="transform:scale(0)">{S}</div>', True),
    ("one_px_box", '<div style="width:1px;height:1px;overflow:hidden">{S}</div>', True),
    ("media_wrapped_rule", '<style>@media screen{.m{display:none}}</style><p class="m">{S}</p>', True),
    ("multi_selector", '<style>h1, .y {visibility:hidden}</style><h1>{S}</h1>', True),
    # Decoys: normal styling a person CAN see. These must stay.
    ("decoy_white_on_dark_button", '<style>.btn{color:#fff;background:#003366;padding:8px}</style><a class="btn">{S}</a>', False),
    ("decoy_normal_css", '<style>th{background:#eef2f6} .deal{border-left:4px solid green}</style><p class="deal">{S}</p>', False),
    ("decoy_small_negative_margin", '<p style="margin-left:-10px">{S}</p>', False),
    ("decoy_aria_hidden_text", '<span aria-hidden="true">{S}</span>', False),
    ("decoy_overflow_hidden_big_box", '<div style="width:300px;height:80px;overflow:hidden">{S}</div>', False),
]


def make_pdf(name: str, draw) -> Path:
    path = FIX / f"{name}.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 11)
    c.drawString(60, 700, VISIBLE)
    draw(c)
    c.save()
    return path


def invisible_mode(c):
    t = c.beginText(60, 650)
    t.setTextRenderMode(3)  # Tr 3: invisible text, still in the text layer
    t.textLine(SECRET)
    c.drawText(t)


def white_box_on_top(c):
    c.setFillColorRGB(0, 0, 0)
    c.drawString(60, 600, SECRET)
    c.setFillColorRGB(1, 1, 1)
    c.rect(55, 595, 300, 16, stroke=0, fill=1)  # white box drawn AFTER the text, covering it


def decoy_white_box_underneath(c):
    c.setFillColorRGB(1, 1, 1)
    c.rect(55, 595, 300, 16, stroke=0, fill=1)  # white background drawn BEFORE the text
    c.setFillColorRGB(0, 0, 0)
    c.drawString(60, 600, SECRET)


def decoy_grey_box_on_top(c):
    c.setFillColorRGB(0, 0, 0)
    c.drawString(60, 600, SECRET)
    c.setFillColorRGB(0.85, 0.85, 0.85)
    c.rect(55, 560, 300, 16, stroke=0, fill=1)  # a box elsewhere on the page, not over the text


def decoy_white_box_elsewhere(c):
    c.setFillColorRGB(0, 0, 0)
    c.drawString(60, 600, SECRET)
    c.setFillColorRGB(1, 1, 1)
    c.rect(55, 300, 300, 16, stroke=0, fill=1)  # white box drawn after, but somewhere else


PDF_CASES = [
    ("pdf_invisible_render_mode", invisible_mode, True),
    ("pdf_white_box_on_top", white_box_on_top, True),
    ("decoy_pdf_white_background_underneath", decoy_white_box_underneath, False),
    ("decoy_pdf_box_not_over_text", decoy_grey_box_on_top, False),
    ("decoy_pdf_white_box_elsewhere", decoy_white_box_elsewhere, False),
]


def main() -> int:
    results = []
    for name, body, should_remove in HTML_CASES:
        path = FIX / f"{name}.html"
        path.write_text(f"<html><body><p>{VISIBLE}</p>{body.replace('{S}', SECRET)}</body></html>", encoding="utf-8")
        results.append((name, path, should_remove))
    for name, draw, should_remove in PDF_CASES:
        results.append((name, make_pdf(name, draw), should_remove))

    failures = 0
    for name, path, should_remove in results:
        text, removed = tools.read_clean_document(f"data/test_fixtures/{path.name}")
        removed_secret = SECRET not in text
        kept_visible = VISIBLE in text
        ok = (removed_secret == should_remove) and kept_visible
        failures += not ok
        want = "remove" if should_remove else "KEEP"
        print(f"{'PASS' if ok else 'FAIL'}  {name:40} want={want:6} removed={removed_secret}  "
              f"{removed[0][:70] if removed else ''}")
    print(f"\n{len(results) - failures}/{len(results)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
