"""Markdown CV -> PDF, pure Python (xhtml2pdf) so the slim image needs no system libs."""

from __future__ import annotations

import io
import re

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
    # Imported PDFs contain plain extracted lines rather than Markdown blocks.
    # Preserve those line breaks instead of exporting one run-on paragraph.
    body = md.markdown(text, extensions=["extra", "sane_lists", "nl2br"])
    html = f"<html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>{body}</body></html>"
    out = io.BytesIO()
    result = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError("Generazione PDF fallita")
    return out.getvalue()


def check_pdf(text: str) -> dict:
    """Inspect the actual export, independently of the language model."""
    import pdfplumber
    with pdfplumber.open(io.BytesIO(markdown_to_pdf(text))) as pdf:
        extracted = "\n\n".join(page.extract_text() or "" for page in pdf.pages)
        pages = len(pdf.pages)
    warnings = []
    if not extracted.strip():
        warnings.append("Il PDF esportato non contiene testo estraibile")
    if pages > 1:
        warnings.append(f"Il PDF esportato occupa {pages} pagine: controlla le interruzioni nell'anteprima")
    if "\ufffd" in extracted:
        warnings.append("Sono presenti caratteri non riconosciuti nel testo estratto")
    emails = re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    if any(email not in extracted for email in emails):
        warnings.append("Un indirizzo email presente nel CV non è stato estratto dal PDF")
    return {"pages": pages, "chars": len(extracted), "text": extracted, "warnings": warnings,
            "scope": "PDF esportato da JobSpy; non è una verifica su ATS esterni né sul PDF originale"}
