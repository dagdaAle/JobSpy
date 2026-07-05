"""
DeepSeek-powered analysis of job postings against the user's CV.

For each job the model returns:
* ``tags``            -> short identifying labels (skills / seniority / domain)
* ``summary``         -> a concise Italian summary of the role
* ``relevance_score`` -> 0-100 fit vs. the CV
* ``reasons``         -> short bullet explanations for the score

DeepSeek exposes an OpenAI-compatible API, so we reuse the ``openai`` client
pointed at ``https://api.deepseek.com``. Configuration comes from the
environment (loaded from ``.env`` by the app):

* ``DEEPSEEK_API_KEY``  (required to actually call the API)
* ``DEEPSEEK_BASE_URL`` (default ``https://api.deepseek.com``)
* ``DEEPSEEK_MODEL``    (default ``deepseek-chat``)
* ``CV_PATH``           (default ``/data/cv.pdf``)

If no API key is configured the module degrades gracefully: CV extraction and
DB code still work, but :func:`analyze_job` raises so the caller can skip
analysis instead of crashing the search.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Environment-driven configuration (read once at import time).
_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
_CV_PATH = os.environ.get("CV_PATH", "/data/cv.pdf").strip()

# Keep prompt tokens (and cost) bounded: descriptions can be very long.
_MAX_DESC_CHARS = 6000
_MAX_CV_CHARS = 8000


class AnalyzerNotConfigured(RuntimeError):
    """Raised when analysis is requested but no API key is configured."""


def is_configured() -> bool:
    """True if a DeepSeek API key is present."""
    return bool(_API_KEY)


def _client():
    """Lazily build the OpenAI-compatible client for DeepSeek."""
    if not _API_KEY:
        raise AnalyzerNotConfigured("DEEPSEEK_API_KEY not set")
    # Import here so the module loads even if openai isn't installed yet.
    from openai import OpenAI

    return OpenAI(api_key=_API_KEY, base_url=_BASE_URL)


def extract_pdf_text(path: str | None = None) -> str:
    """
    Extract plain text from the CV PDF.

    Returns an empty string if the file is missing or unreadable, so callers
    can decide whether to proceed without a CV.
    """
    pdf_path = path or _CV_PATH
    if not pdf_path or not os.path.exists(pdf_path):
        return ""

    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text:
                parts.append(text)
    full = "\n".join(parts).strip()
    return full[:_MAX_CV_CHARS]


_SYSTEM_PROMPT = (
    "Sei un assistente che valuta annunci di lavoro per un candidato specifico, "
    "confrontandoli con il suo CV. Rispondi SEMPRE ed ESCLUSIVAMENTE con un "
    "oggetto JSON valido, senza testo aggiuntivo, con questa struttura:\n"
    "{\n"
    '  "tags": [stringhe brevi in italiano, max 6, es. "Python", "Junior", "Remote", "Fintech"],\n'
    '  "summary": "riassunto conciso del ruolo in italiano, max 3 frasi, citando azienda e mansioni chiave",\n'
    '  "relevance_score": intero da 0 a 100 su quanto il lavoro e adatto al candidato,\n'
    '  "reasons": [max 3 stringhe brevi che spiegano il punteggio]\n'
    "}\n"
    "Basa il punteggio su competenze, seniority, settore e modalita di lavoro rispetto al CV. "
    "Se la descrizione dell'annuncio e vuota o scarsa, abbassa il punteggio e segnalalo nei reasons."
)


def _build_user_prompt(job: dict[str, Any], cv_text: str) -> str:
    title = job.get("title") or ""
    company = job.get("company") or ""
    location = job.get("location") or ""
    is_remote = job.get("is_remote")
    job_type = job.get("job_type") or ""
    description = (job.get("description") or "")[:_MAX_DESC_CHARS]

    cv_block = cv_text.strip() or "(CV non disponibile)"

    return (
        "=== CV DEL CANDIDATO ===\n"
        f"{cv_block}\n\n"
        "=== ANNUNCIO DI LAVORO ===\n"
        f"Titolo: {title}\n"
        f"Azienda: {company}\n"
        f"Localita: {location}\n"
        f"Remote: {is_remote}\n"
        f"Tipo: {job_type}\n"
        f"Descrizione:\n{description or '(nessuna descrizione disponibile)'}\n\n"
        "Valuta questo annuncio per il candidato e rispondi solo con il JSON richiesto."
    )


def analyze_job(job: dict[str, Any], cv_text: str) -> dict[str, Any]:
    """
    Analyze a single job against the CV via DeepSeek.

    Returns a dict with keys: tags (list[str]), summary (str),
    relevance_score (int 0-100), reasons (list[str]).

    Raises :class:`AnalyzerNotConfigured` if no API key is set.
    """
    client = _client()

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(job, cv_text)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=800,
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    return _normalize(data)


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    """Coerce the model output into the expected shapes/ranges."""
    tags = data.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    tags = [str(t).strip() for t in tags if str(t).strip()][:6]

    summary = str(data.get("summary") or "").strip()

    try:
        score = int(round(float(data.get("relevance_score", 0))))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    reasons = data.get("reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]
    reasons = [str(r).strip() for r in reasons if str(r).strip()][:3]

    return {
        "tags": tags,
        "summary": summary,
        "relevance_score": score,
        "reasons": reasons,
    }
