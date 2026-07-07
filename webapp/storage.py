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

# Rich columns added to the `jobs` table via idempotent migration. These are the
# extra fields JobSpy already returns but that the original app dropped; they
# power the detail page and richer cards. All are stored as TEXT (stringified).
_RICH_JOB_COLUMNS = (
    "job_url_direct",
    "company_url",
    "company_industry",
    "company_logo",
    "banner_photo_url",
    "job_level",
    "job_function",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_interval",
    "emails",
    "skills",
)


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
        # A "channel" = one site + one query, refreshed on a schedule.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT,
                site           TEXT NOT NULL,
                search_term    TEXT NOT NULL,
                location       TEXT DEFAULT '',
                distance_km    INTEGER DEFAULT 25,
                results_wanted INTEGER DEFAULT 25,
                hours_old      INTEGER,
                is_remote      INTEGER DEFAULT 0,
                created_at     TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Association channel <-> job, with per-channel first/last seen so we can
        # mark "new" jobs (first_seen == last_seen).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS channel_jobs (
                channel_id INTEGER NOT NULL,
                job_url    TEXT NOT NULL,
                first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen  TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (channel_id, job_url)
            )
            """
        )
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotently add the rich columns to the existing `jobs` table.

    Uses ``PRAGMA table_info`` + ``ALTER TABLE ADD COLUMN`` so an existing DB
    volume (with jobs already stored) keeps its data — we only add what's missing.
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
    for col in _RICH_JOB_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")


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
) + _RICH_JOB_COLUMNS


def _upsert_jobs_conn(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> None:
    """Insert/update raw job rows on an open connection (no locking)."""
    cols = ", ".join(_JOB_FIELDS)
    placeholders = ", ".join("?" for _ in _JOB_FIELDS)
    updates = ", ".join(f"{f} = excluded.{f}" for f in _JOB_FIELDS)
    sql = (
        f"INSERT INTO jobs (job_url, {cols}, seen_at) "
        f"VALUES (?, {placeholders}, datetime('now')) "
        f"ON CONFLICT(job_url) DO UPDATE SET {updates}"
    )
    for rec in records:
        url = rec.get("job_url")
        if not url:
            continue
        # Stringify non-text values (is_remote may be bool) for stable storage.
        values = [None if rec.get(f) is None else str(rec.get(f)) for f in _JOB_FIELDS]
        conn.execute(sql, (url, *values))


def upsert_jobs(records: list[dict[str, Any]]) -> None:
    """Insert/update raw job rows, keyed by ``job_url``. Rows without a URL are skipped."""
    if not records:
        return
    with _lock, _connect() as conn:
        _upsert_jobs_conn(conn, records)


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
                   is_remote, job_type, date_posted,
                   company_logo, salary_min, salary_max,
                   salary_currency, salary_interval
            FROM jobs
            ORDER BY seen_at DESC
            """
        ).fetchall()
    return [_row_to_card(row) for row in rows]


def _row_to_card(row: sqlite3.Row) -> dict[str, Any]:
    """Normalise a jobs row into a lightweight card record (no description)."""
    rec = dict(row)
    rec["is_remote"] = str(rec.get("is_remote")).lower() == "true"
    return rec


def get_job(job_url: str) -> dict[str, Any] | None:
    """Return a single job with **all** stored columns (for the detail page)."""
    if not job_url:
        return None
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_url = ?", (job_url,)
        ).fetchone()
    if row is None:
        return None
    rec = dict(row)
    rec["is_remote"] = str(rec.get("is_remote")).lower() == "true"
    return rec


# --------------------------------------------------------------------------- #
# Channels                                                                     #
# --------------------------------------------------------------------------- #

_CHANNEL_FIELDS = (
    "name",
    "site",
    "search_term",
    "location",
    "distance_km",
    "results_wanted",
    "hours_old",
    "is_remote",
)


def create_channel(
    *,
    site: str,
    search_term: str,
    name: str = "",
    location: str = "",
    distance_km: int = 25,
    results_wanted: int = 25,
    hours_old: int | None = None,
    is_remote: bool = False,
) -> int:
    """Create a channel and return its new id."""
    with _lock, _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO channels
                (name, site, search_term, location, distance_km,
                 results_wanted, hours_old, is_remote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name or f"{site}: {search_term}",
                site,
                search_term,
                location,
                distance_km,
                results_wanted,
                hours_old,
                1 if is_remote else 0,
            ),
        )
        return int(cur.lastrowid)


def _channel_from_row(row: sqlite3.Row) -> dict[str, Any]:
    rec = dict(row)
    rec["is_remote"] = bool(rec.get("is_remote"))
    return rec


def get_channel(channel_id: int) -> dict[str, Any] | None:
    """Return a single channel by id, or None."""
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM channels WHERE id = ?", (channel_id,)
        ).fetchone()
    return _channel_from_row(row) if row else None


def list_channels() -> list[dict[str, Any]]:
    """Return all channels with ``total_count`` and ``new_count`` per channel."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM channels ORDER BY created_at ASC"
        ).fetchall()
        channels: list[dict[str, Any]] = []
        for row in rows:
            ch = _channel_from_row(row)
            counts = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN first_seen = last_seen THEN 1 ELSE 0 END) AS new
                FROM channel_jobs WHERE channel_id = ?
                """,
                (ch["id"],),
            ).fetchone()
            ch["total_count"] = counts["total"] or 0
            ch["new_count"] = counts["new"] or 0
            channels.append(ch)
    return channels


def delete_channel(channel_id: int) -> None:
    """Delete a channel and its associations (jobs themselves are kept)."""
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM channel_jobs WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))


def upsert_channel_jobs(
    channel_id: int, records: list[dict[str, Any]]
) -> int:
    """Upsert jobs into `jobs` and link them to the channel.

    Returns the number of jobs that are **new** for this channel (i.e. seen for
    the first time). Existing links have their ``last_seen`` bumped so they are
    no longer flagged as new.
    """
    if not records:
        return 0
    new_count = 0
    with _lock, _connect() as conn:
        _upsert_jobs_conn(conn, records)
        for rec in records:
            url = rec.get("job_url")
            if not url:
                continue
            existing = conn.execute(
                "SELECT 1 FROM channel_jobs WHERE channel_id = ? AND job_url = ?",
                (channel_id, url),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE channel_jobs SET last_seen = datetime('now')
                    WHERE channel_id = ? AND job_url = ?
                    """,
                    (channel_id, url),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO channel_jobs (channel_id, job_url, first_seen, last_seen)
                    VALUES (?, ?, datetime('now'), datetime('now'))
                    """,
                    (channel_id, url),
                )
                new_count += 1
    return new_count


def get_channel_jobs(channel_id: int) -> list[dict[str, Any]]:
    """Return the card records for a channel's jobs, newest-first, with a
    per-channel ``is_new`` flag."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            """
            SELECT j.job_url, j.site, j.title, j.company, j.location,
                   j.is_remote, j.job_type, j.date_posted,
                   j.company_logo, j.salary_min, j.salary_max,
                   j.salary_currency, j.salary_interval,
                   cj.first_seen, cj.last_seen
            FROM channel_jobs cj
            JOIN jobs j ON j.job_url = cj.job_url
            WHERE cj.channel_id = ?
            ORDER BY cj.last_seen DESC, cj.first_seen DESC
            """,
            (channel_id,),
        ).fetchall()
    jobs: list[dict[str, Any]] = []
    for row in rows:
        rec = _row_to_card(row)
        rec["is_new"] = rec.pop("first_seen") == rec.pop("last_seen")
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
