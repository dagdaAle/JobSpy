"""CV PDF export and local text extraction checks."""

from __future__ import annotations

import io
import re

from cv_template import to_pdf

def markdown_to_pdf(text: str, template: str = "europass") -> bytes:
    return to_pdf(text, template)


def preview_info(text: str, template: str) -> dict:
    from pypdf import PdfReader
    return {"pages": len(PdfReader(io.BytesIO(markdown_to_pdf(text, template))).pages)}


def preview_page(text: str, template: str, page_number: int) -> bytes:
    import pypdfium2
    pdf = pypdfium2.PdfDocument(markdown_to_pdf(text, template))
    try:
        if not 1 <= page_number <= len(pdf):
            raise IndexError("Pagina non trovata")
        page = pdf[page_number - 1]
        try:
            bitmap = page.render(scale=1.4)
            try:
                out = io.BytesIO()
                bitmap.to_pil().save(out, format="PNG")
                return out.getvalue()
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        pdf.close()


def check_pdf(text: str, template: str = "europass") -> dict:
    """Inspect the actual export, independently of the language model."""
    from pypdf import PdfReader
    pdf = PdfReader(io.BytesIO(markdown_to_pdf(text, template)))
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
