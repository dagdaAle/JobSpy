"""Markdown CV -> PDF, pure Python (xhtml2pdf) so the slim image needs no system libs."""

from __future__ import annotations

import io

import markdown as md
from xhtml2pdf import pisa

_CSS = """
@page { size: A4; margin: 1.6cm 1.8cm; }
body { font-family: Helvetica; font-size: 10pt; line-height: 1.35; color: #222; }
h1 { font-size: 20pt; margin: 0 0 4pt 0; }
h2 { font-size: 12pt; color: #1f4e79; border-bottom: 1px solid #1f4e79;
     margin: 12pt 0 4pt 0; padding-bottom: 1pt; }
h3 { font-size: 10.5pt; margin: 8pt 0 2pt 0; }
p { margin: 2pt 0; }
ul { margin: 2pt 0 2pt 0; padding-left: 14pt; }
li { margin: 0 0 1pt 0; }
a { color: #1f4e79; }
"""


def markdown_to_pdf(text: str) -> bytes:
    body = md.markdown(text, extensions=["extra", "sane_lists"])
    html = f"<html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>{body}</body></html>"
    out = io.BytesIO()
    result = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError("Generazione PDF fallita")
    return out.getvalue()
