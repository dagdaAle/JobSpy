"""
Post-scrape filters of a channel, applied before jobs are stored.

The job boards only take one query string, so finer rules live here:

* ``include_keywords``  -> keep a job only if title or description contains
  at least one of them (empty = keep all)
* ``exclude_keywords``  -> drop a job whose **title** contains any of them
  (title only: "senior" in a description is usually noise)
* ``exclude_companies`` -> drop a job whose company contains any of them
* ``work_mode``         -> ``any`` | ``remote`` | ``remote_or_hybrid``;
  a textual heuristic, the AI analysis checks it properly afterwards

Matching is case-insensitive on word boundaries, so "ai" does not match "mail".
"""

from __future__ import annotations

import re
from typing import Any

WORK_MODES = ("any", "remote", "remote_or_hybrid")

_REMOTE = re.compile(r"\b(full[- ]?remote|remote|remot[oa]|telelavoro|work from home|wfh)\b", re.I)
_HYBRID = re.compile(r"\b(hybrid|ibrid[oa]|smart working)\b", re.I)


def _pattern(words: list[str]) -> re.Pattern[str] | None:
    words = [w.strip() for w in words if w and w.strip()]
    if not words:
        return None
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.I)


def _text(rec: dict[str, Any], *keys: str) -> str:
    return " ".join(str(rec.get(k) or "") for k in keys)


def _work_mode_ok(rec: dict[str, Any], mode: str) -> bool:
    if mode not in ("remote", "remote_or_hybrid"):
        return True
    if rec.get("is_remote") is True:
        return True
    text = _text(rec, "title", "location", "description")
    if _REMOTE.search(text):
        return True
    return mode == "remote_or_hybrid" and bool(_HYBRID.search(text))


def filter_records(records: list[dict[str, Any]], channel: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """Return ``(kept, removed_count)`` for ``records`` under ``channel``'s filters."""
    include = _pattern(channel.get("include_keywords") or [])
    exclude = _pattern(channel.get("exclude_keywords") or [])
    companies = _pattern(channel.get("exclude_companies") or [])
    mode = channel.get("work_mode") or "any"

    kept = []
    for rec in records:
        if include and not include.search(_text(rec, "title", "description")):
            continue
        if exclude and exclude.search(_text(rec, "title")):
            continue
        if companies and companies.search(_text(rec, "company")):
            continue
        if not _work_mode_ok(rec, mode):
            continue
        kept.append(rec)
    return kept, len(records) - len(kept)
