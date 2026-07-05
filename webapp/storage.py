"""
Persistent storage for user feedback (like / dislike) on job postings.

Each job is identified by its ``job_url`` (stable across searches), so a
like/dislike survives new searches and container restarts. The data lives in a
single SQLite file whose path is configurable via ``FEEDBACK_DB`` (defaults to
``feedback.db`` in the working directory); in Docker this is mounted on a volume.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any, Literal

Verdict = Literal["like", "dislike"]

_DB_PATH = os.environ.get("FEEDBACK_DB", "feedback.db")
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they don't exist yet."""
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                job_url   TEXT PRIMARY KEY,
                verdict   TEXT NOT NULL CHECK (verdict IN ('like', 'dislike')),
                title     TEXT,
                company   TEXT,
                site      TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Raw job postings seen across searches (deduped by job_url).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_url     TEXT PRIMARY KEY,
                site        TEXT,
                title       TEXT,
                company     TEXT,
                location    TEXT,
                is_remote   TEXT,
                job_type    TEXT,
                date_posted TEXT,
                description TEXT,
                seen_at     TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # DeepSeek analysis, one row per job_url (cache: never re-pay).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis (
                job_url         TEXT PRIMARY KEY,
                tags            TEXT,   -- JSON array
                summary         TEXT,
                relevance_score INTEGER,
                reasons         TEXT,   -- JSON array
                analyzed_at     TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Current CV text (single row, id=1).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cv (
                id         INTEGER PRIMARY KEY CHECK (id = 1),
                text       TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def set_feedback(
    job_url: str,
    verdict: Verdict | None,
    *,
    title: str = "",
    company: str = "",
    site: str = "",
) -> None:
    """
    Store or update the verdict for a job.

    Passing ``verdict=None`` clears any existing feedback (toggle off).
    """
    if not job_url:
        raise ValueError("job_url is required")

    with _lock, _connect() as conn:
        if verdict is None:
            conn.execute("DELETE FROM feedback WHERE job_url = ?", (job_url,))
            return
        if verdict not in ("like", "dislike"):
            raise ValueError(f"invalid verdict: {verdict!r}")
        conn.execute(
            """
            INSERT INTO feedback (job_url, verdict, title, company, site, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(job_url) DO UPDATE SET
                verdict = excluded.verdict,
                title   = excluded.title,
                company = excluded.company,
                site    = excluded.site,
                updated_at = datetime('now')
            """,
            (job_url, verdict, title, company, site),
        )


def get_all_feedback() -> dict[str, str]:
    """Return a mapping ``{job_url: verdict}`` for every stored job."""
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT job_url, verdict FROM feedback").fetchall()
    return {row["job_url"]: row["verdict"] for row in rows}


# --------------------------------------------------------------------------- #
# Jobs                                                                         #
# --------------------------------------------------------------------------- #

_JOB_FIELDS = (
    "site",
    "title",
    "company",
    "location",
    "is_remote",
    "job_type",
    "date_posted",
    "description",
)


def upsert_jobs(records: list[dict[str, Any]]) -> None:
    """Insert/update raw job rows, keyed by ``job_url``. Rows without a URL are skipped."""
    if not records:
        return
    with _lock, _connect() as conn:
        for rec in records:
            url = rec.get("job_url")
            if not url:
                continue
            values = [rec.get(f) for f in _JOB_FIELDS]
            # Stringify non-text values (is_remote may be bool) for stable storage.
            values = [None if v is None else str(v) for v in values]
            conn.execute(
                """
                INSERT INTO jobs (job_url, site, title, company, location,
                                  is_remote, job_type, date_posted, description, seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(job_url) DO UPDATE SET
                    site        = excluded.site,
                    title       = excluded.title,
                    company     = excluded.company,
                    location    = excluded.location,
                    is_remote   = excluded.is_remote,
                    job_type    = excluded.job_type,
                    date_posted = excluded.date_posted,
                    description = excluded.description
                """,
                (url, *values),
            )


def get_all_jobs() -> list[dict[str, Any]]:
    """
    Return every stored job as a record, newest first (by ``seen_at``).

    The ``description`` column is intentionally omitted: the frontend never
    displays it and it keeps the payload small.
    """
    with _lock, _connect() as conn:
        rows = conn.execute(
            """
            SELECT job_url, site, title, company, location,
                   is_remote, job_type, date_posted
            FROM jobs
            ORDER BY seen_at DESC
            """
        ).fetchall()
    jobs: list[dict[str, Any]] = []
    for row in rows:
        rec = dict(row)
        # is_remote is stored as text ("True"/"False"); normalise to bool.
        rec["is_remote"] = str(rec.get("is_remote")).lower() == "true"
        jobs.append(rec)
    return jobs


# --------------------------------------------------------------------------- #
# Analysis                                                                     #
# --------------------------------------------------------------------------- #


def get_analyzed_urls() -> set[str]:
    """Return the set of job_urls that already have a stored analysis."""
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT job_url FROM analysis").fetchall()
    return {row["job_url"] for row in rows}


def set_analysis(job_url: str, analysis: dict[str, Any]) -> None:
    """Store (or replace) the analysis for a job."""
    if not job_url:
        return
    tags = json.dumps(analysis.get("tags", []), ensure_ascii=False)
    reasons = json.dumps(analysis.get("reasons", []), ensure_ascii=False)
    summary = analysis.get("summary", "")
    score = analysis.get("relevance_score")
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO analysis (job_url, tags, summary, relevance_score, reasons, analyzed_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(job_url) DO UPDATE SET
                tags            = excluded.tags,
                summary         = excluded.summary,
                relevance_score = excluded.relevance_score,
                reasons         = excluded.reasons,
                analyzed_at     = datetime('now')
            """,
            (job_url, tags, summary, score, reasons),
        )


def get_all_analysis() -> dict[str, dict[str, Any]]:
    """Return ``{job_url: {tags, summary, relevance_score, reasons}}`` for all analyzed jobs."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT job_url, tags, summary, relevance_score, reasons FROM analysis"
        ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result[row["job_url"]] = {
            "tags": _loads_list(row["tags"]),
            "summary": row["summary"] or "",
            "relevance_score": row["relevance_score"],
            "reasons": _loads_list(row["reasons"]),
        }
    return result


def _loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []


# --------------------------------------------------------------------------- #
# CV                                                                          #
# --------------------------------------------------------------------------- #


def set_cv_text(text: str) -> None:
    """Store the current CV text (single row)."""
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO cv (id, text, updated_at)
            VALUES (1, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                text = excluded.text,
                updated_at = datetime('now')
            """,
            (text,),
        )


def get_cv_text() -> str:
    """Return the stored CV text, or an empty string if none."""
    with _lock, _connect() as conn:
        row = conn.execute("SELECT text FROM cv WHERE id = 1").fetchone()
    return row["text"] if row else ""
