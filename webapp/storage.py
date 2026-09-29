"""
Persistent storage for JobSpy: jobs, channels, AI analyses and user verdicts.

Nothing that happens is thrown away. Current-state tables (``jobs``,
``analysis``, ``feedback``, ``cv``) drive the UI, and append-only history
tables record every event next to them:

* ``job_sightings``   one row each time a job shows up in a scrape
* ``job_versions``    a snapshot of the scraped data whenever it changes
* ``analysis_runs``   every AI analysis attempt (failures included)
* ``feedback_events`` every like / dislike / undo
* ``cv_versions``     every distinct CV text
* ``refresh_log``     every refresh, analysis batch and feed clean-up

Jobs are never deleted: after ``FEED_DAYS`` without a verdict they are only
*archived* (hidden from the feed) and still count in analytics.

Each job is identified by its ``job_url`` (stable across searches), so a
like/dislike survives new searches and container restarts. The data lives in a
single SQLite file whose path is configurable via ``FEEDBACK_DB`` (defaults to
``feedback.db`` in the working directory); in Docker this is mounted on a volume.
"""

from __future__ import annotations

import datetime
from contextlib import contextmanager
import hashlib
import json
import os
import re
import sqlite3
import threading
import uuid
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


# Lifecycle columns on `jobs`: when we first/last saw a job, and when it left
# the feed (archived_at) and why. raw_json is the latest full JobSpy row.
_LIFECYCLE_COLUMNS = (
    "first_seen_at",
    "last_seen_at",
    "archived_at",
    "archive_reason",
    "raw_json",
    "feed_since",
)


@contextmanager
def _connect():
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _now() -> str:
    """UTC timestamp in SQLite's datetime('now') format."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# Backups live next to the DB (same persistent volume).
_BACKUP_DIR = os.environ.get(
    "BACKUP_DIR", os.path.join(os.path.dirname(os.path.abspath(_DB_PATH)), "backups")
)
_DAILY_BACKUPS_KEPT = 14


def backup_db(tag: str) -> str | None:
    """Consistent copy of the DB (SQLite online backup) into ``_BACKUP_DIR``.

    ``daily-*`` copies are rotated (last ``_DAILY_BACKUPS_KEPT`` kept); any
    other tag (e.g. the pre-migration copy) is kept forever.
    """
    if not os.path.exists(_DB_PATH):
        return None
    os.makedirs(_BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(_BACKUP_DIR, f"{tag}-{stamp}.db")
    src = sqlite3.connect(_DB_PATH, timeout=30)
    try:
        with sqlite3.connect(dest) as out:
            src.backup(out)
    finally:
        src.close()
    if tag == "daily":
        daily = sorted(f for f in os.listdir(_BACKUP_DIR) if f.startswith("daily-"))
        for old in daily[:-_DAILY_BACKUPS_KEPT]:
            os.remove(os.path.join(_BACKUP_DIR, old))
    return dest


def _needs_history_migration() -> bool:
    """True for an existing DB that predates the history tables."""
    if not os.path.exists(_DB_PATH):
        return False
    with _connect() as conn:
        has_jobs = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'"
        ).fetchone()
        has_meta = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
        ).fetchone()
        done = has_meta and conn.execute(
            "SELECT 1 FROM meta WHERE key = 'history_v1'"
        ).fetchone()
    return bool(has_jobs) and not done


def init_db() -> None:
    """Create all tables if they don't exist yet.

    Before migrating an existing DB to the history schema, a full copy is
    saved in ``_BACKUP_DIR`` (``pre-history-*.db``, never rotated).
    """
    if _needs_history_migration():
        path = backup_db("pre-history")
        print(f"[storage] backup before migration: {path}", flush=True)
    if os.path.exists(_DB_PATH):
        with _connect() as conn:
            jobs_exist = conn.execute("SELECT 1 FROM sqlite_master WHERE name='jobs'").fetchone()
            migrated = 'feed_since' in {r['name'] for r in conn.execute('PRAGMA table_info(jobs)')}
            app_columns = {r['name'] for r in conn.execute('PRAGMA table_info(applications)')}
        if jobs_exist and not migrated:
            backup_db('pre-workflow-v2')
        elif app_columns and 'cv_label' not in app_columns:
            backup_db('pre-application-history')
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
        # Current analysis cache; model, prompt and CV determine validity.
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
        # mark jobs first discovered in the latest successful refresh.
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
        # One row per update event (refresh, AI analysis batch, feed clean-up), shown
        # in the Log page. Kept forever.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at   TEXT NOT NULL,
                finished_at  TEXT NOT NULL DEFAULT (datetime('now')),
                kind         TEXT NOT NULL,   -- 'refresh' | 'analysis' | 'archive'
                trigger      TEXT NOT NULL,   -- 'scheduler' | 'manual' | 'create' | 'startup'
                channel_id   INTEGER,
                channel_name TEXT,
                site         TEXT,
                status       TEXT NOT NULL,   -- 'running' | 'ok' | 'error'
                found        INTEGER DEFAULT 0,
                new_count    INTEGER DEFAULT 0,
                analyzed     INTEGER DEFAULT 0,
                analysis_failed INTEGER DEFAULT 0,
                removed      INTEGER DEFAULT 0,
                duration_ms  INTEGER DEFAULT 0,
                error        TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_sightings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                job_url    TEXT NOT NULL,
                channel_id INTEGER,          -- NULL for ad-hoc /search results
                run_id     INTEGER,          -- refresh_log.id of the scrape
                seen_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_versions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                job_url      TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                data         TEXT NOT NULL,  -- JSON: every column JobSpy returned
                seen_at      TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                job_url         TEXT NOT NULL,
                provider        TEXT NOT NULL,
                model           TEXT,
                prompt_version  TEXT,
                cv_version_id   INTEGER,
                status          TEXT NOT NULL,   -- 'ok' | 'error' | 'imported'
                relevance_score INTEGER,
                tags            TEXT,            -- JSON array
                summary         TEXT,
                reasons         TEXT,            -- JSON array
                raw_response    TEXT,
                input_tokens    INTEGER,
                output_tokens   INTEGER,
                latency_ms      INTEGER,
                error           TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                job_url    TEXT NOT NULL,
                verdict    TEXT,             -- NULL = verdict removed
                previous   TEXT,
                source     TEXT NOT NULL,    -- user | propagated | inherited | import
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cv_versions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                sha256     TEXT NOT NULL UNIQUE,
                text       TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        for idx in (
            "CREATE INDEX IF NOT EXISTS ix_sightings_url ON job_sightings(job_url)",
            "CREATE INDEX IF NOT EXISTS ix_versions_url ON job_versions(job_url)",
            "CREATE INDEX IF NOT EXISTS ix_runs_url ON analysis_runs(job_url)",
            "CREATE INDEX IF NOT EXISTS ix_fbev_url ON feedback_events(job_url)",
        ):
            conn.execute(idx)
        _migrate(conn)
        _backfill_history(conn)
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotently add the rich columns to the existing `jobs` table.

    Uses ``PRAGMA table_info`` + ``ALTER TABLE ADD COLUMN`` so an existing DB
    volume (with jobs already stored) keeps its data — we only add what's missing.
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
    for col in _RICH_JOB_COLUMNS + _LIFECYCLE_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_jobs_archived ON jobs(archived_at)")
    for table, columns in {
        "channel_jobs": {"is_new": "INTEGER NOT NULL DEFAULT 0"},
        "analysis": {"context_key": "TEXT", "assessment": "TEXT"},
        "analysis_runs": {"context_key": "TEXT"},
    }.items():
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        for col, kind in columns.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")
    # Pre-migration analyses stay valid ('legacy') instead of being re-paid.
    # To re-analyse them: UPDATE analysis SET context_key = '' WHERE context_key = 'legacy'
    conn.execute("UPDATE analysis SET context_key = 'legacy' WHERE context_key IS NULL")
    conn.execute("""CREATE TABLE IF NOT EXISTS applications (
        job_url TEXT PRIMARY KEY, status TEXT NOT NULL,
        applied_on TEXT, notes TEXT NOT NULL DEFAULT '', next_step TEXT NOT NULL DEFAULT '',
        follow_up_on TEXT, updated_at TEXT NOT NULL
    )""")

    existing = {row["name"] for row in conn.execute("PRAGMA table_info(applications)")}
    for column in ("cv_label", "contact"):
        if column not in existing:
            conn.execute(f"ALTER TABLE applications ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    conn.execute("""CREATE TABLE IF NOT EXISTS application_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, job_url TEXT NOT NULL,
        kind TEXT NOT NULL, content TEXT NOT NULL, occurred_on TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_application_events_url ON application_events(job_url, id)")
    if not conn.execute("SELECT 1 FROM meta WHERE key='application_history_v1'").fetchone():
        for row in conn.execute("SELECT * FROM applications").fetchall():
            conn.execute("INSERT INTO application_events(job_url,kind,content,occurred_on,created_at) VALUES (?,?,?,?,?)",
                         (row['job_url'], 'imported', json.dumps(dict(row), ensure_ascii=False),
                          row['updated_at'][:10], _now()))
        conn.execute("INSERT INTO meta VALUES ('application_history_v1', ?)", (_now(),))


def _backfill_history(conn: sqlite3.Connection) -> None:
    """One-off import of what the DB already knew into the history tables.

    Runs once (guarded by ``meta.history_v1``) so an existing production DB
    keeps every analysis, verdict and sighting it had before this change.
    """
    if conn.execute("SELECT 1 FROM meta WHERE key = 'history_v1'").fetchone():
        return
    # First/last seen: earliest/latest channel sighting, else when first stored.
    conn.execute(
        """
        UPDATE jobs SET
            first_seen_at = COALESCE(
                (SELECT MIN(first_seen) FROM channel_jobs cj WHERE cj.job_url = jobs.job_url),
                seen_at),
            last_seen_at = COALESCE(
                (SELECT MAX(last_seen) FROM channel_jobs cj WHERE cj.job_url = jobs.job_url),
                seen_at)
        WHERE first_seen_at IS NULL
        """
    )
    conn.execute(
        """
        INSERT INTO job_sightings (job_url, channel_id, seen_at)
        SELECT job_url, channel_id, first_seen FROM channel_jobs
        UNION ALL
        SELECT job_url, channel_id, last_seen FROM channel_jobs WHERE last_seen != first_seen
        """
    )
    cv = conn.execute("SELECT text, updated_at FROM cv WHERE id = 1").fetchone()
    cv_id = None
    if cv and cv["text"]:
        cv_id = _cv_version_conn(conn, cv["text"], cv["updated_at"])
    conn.execute(
        """
        INSERT INTO analysis_runs
            (job_url, provider, model, prompt_version, cv_version_id, status,
             relevance_score, tags, summary, reasons, created_at)
        SELECT job_url, 'deepseek', 'deepseek-chat', 'v1', ?, 'imported',
               relevance_score, tags, summary, reasons, analyzed_at
        FROM analysis
        """,
        (cv_id,),
    )
    conn.execute(
        """
        INSERT INTO feedback_events (job_url, verdict, previous, source, created_at)
        SELECT job_url, verdict, NULL, 'import', updated_at FROM feedback
        """
    )
    conn.execute("INSERT INTO meta (key, value) VALUES ('history_v1', ?)", (_now(),))


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
        siblings = _sibling_rows(conn, job_url)
        prev = conn.execute(
            "SELECT verdict FROM feedback WHERE job_url = ?", (job_url,)
        ).fetchone()
        prev_verdict = prev["verdict"] if prev else None

        if verdict is None:
            _clear_feedback(conn, job_url, "user")
            # Toggling off clears the same verdict on the other copies.
            if prev_verdict:
                for sib in siblings:
                    _clear_feedback(conn, sib["job_url"], "propagated", only=prev_verdict)
            return
        if verdict not in ("like", "dislike"):
            raise ValueError(f"invalid verdict: {verdict!r}")
        _write_feedback(conn, job_url, verdict, title, company, site)
        for sib in siblings:
            # A dislike never overrides a like on another copy -- unless the
            # user is explicitly turning this very offer from like to dislike.
            if verdict == "dislike" and prev_verdict != "like":
                liked = conn.execute(
                    "SELECT 1 FROM feedback WHERE job_url = ? AND verdict = 'like'",
                    (sib["job_url"],),
                ).fetchone()
                if liked:
                    continue
            _write_feedback(
                conn, sib["job_url"], verdict,
                sib["title"] or "", sib["company"] or "", sib["site"] or "",
                source="propagated",
            )


def _log_feedback_event(
    conn: sqlite3.Connection, job_url: str, verdict: str | None,
    previous: str | None, source: str,
) -> None:
    if verdict == previous:
        return
    conn.execute(
        "INSERT INTO feedback_events (job_url, verdict, previous, source, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (job_url, verdict, previous, source, _now()),
    )


def _clear_feedback(
    conn: sqlite3.Connection, job_url: str, source: str, only: str | None = None,
) -> None:
    row = conn.execute("SELECT verdict FROM feedback WHERE job_url = ?", (job_url,)).fetchone()
    if row is None or (only and row["verdict"] != only):
        return
    conn.execute("DELETE FROM feedback WHERE job_url = ?", (job_url,))
    _log_feedback_event(conn, job_url, None, row["verdict"], source)


def _write_feedback(
    conn: sqlite3.Connection, job_url: str, verdict: str,
    title: str, company: str, site: str, source: str = "user",
) -> None:
    row = conn.execute("SELECT verdict FROM feedback WHERE job_url = ?", (job_url,)).fetchone()
    _log_feedback_event(conn, job_url, verdict, row["verdict"] if row else None, source)
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


def _upsert_jobs_conn(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
    channel_id: int | None = None,
    run_id: int | None = None,
) -> None:
    """Insert/update raw job rows on an open connection (no locking).

    Also records a sighting per job and, when the scraped data changed, a new
    snapshot in ``job_versions``. ``first_seen_at`` and ``archived_at`` are
    never touched by a re-scrape.
    """
    now = _now()
    cols = ", ".join(_JOB_FIELDS)
    placeholders = ", ".join("?" for _ in _JOB_FIELDS)
    updates = ", ".join(f"{f} = excluded.{f}" for f in _JOB_FIELDS)
    sql = (
        f"INSERT INTO jobs (job_url, {cols}, raw_json, seen_at, first_seen_at, last_seen_at) "
        f"VALUES (?, {placeholders}, ?, ?, ?, ?) "
        f"ON CONFLICT(job_url) DO UPDATE SET {updates}, "
        f"raw_json = COALESCE(excluded.raw_json, jobs.raw_json), "
        f"last_seen_at = excluded.last_seen_at"
    )
    for rec in records:
        url = rec.get("job_url")
        if not url:
            continue
        # Stringify non-text values (is_remote may be bool) for stable storage.
        values = [None if rec.get(f) is None else str(rec.get(f)) for f in _JOB_FIELDS]
        snapshot = rec.get("_raw") or {k: v for k, v in rec.items() if not k.startswith("_")}
        data = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
        conn.execute(sql, (url, *values, data, now, now, now))

        digest = hashlib.sha256(data.encode()).hexdigest()
        last = conn.execute(
            "SELECT content_hash FROM job_versions WHERE job_url = ? ORDER BY id DESC LIMIT 1",
            (url,),
        ).fetchone()
        if last is None or last["content_hash"] != digest:
            conn.execute(
                "INSERT INTO job_versions (job_url, content_hash, data, seen_at) VALUES (?, ?, ?, ?)",
                (url, digest, data, now),
            )
        conn.execute(
            "INSERT INTO job_sightings (job_url, channel_id, run_id, seen_at) VALUES (?, ?, ?, ?)",
            (url, channel_id, run_id, now),
        )
    _inherit_group_feedback(conn, [r.get("job_url") for r in records if r.get("job_url")])


def upsert_jobs(records: list[dict[str, Any]]) -> None:
    """Insert/update raw job rows, keyed by ``job_url``. Rows without a URL are skipped."""
    if not records:
        return
    with _lock, _connect() as conn:
        _upsert_jobs_conn(conn, records)


def get_all_jobs(include_archived: bool = False, archived_only: bool = False) -> list[dict[str, Any]]:
    """
    Return stored jobs as card records, newest first.

    Archived jobs (out of the feed) are left out unless ``include_archived``.
    The ``description`` column is intentionally omitted: the frontend never
    displays it and it keeps the payload small.
    """
    with _lock, _connect() as conn:
        rows = conn.execute(
            """
            SELECT j.job_url, j.site, j.title, j.company, j.location,
                   j.is_remote, j.job_type, j.date_posted,
                   j.company_logo, j.salary_min, j.salary_max,
                   j.salary_currency, j.salary_interval, j.first_seen_at, j.archived_at, j.feed_since,
                   j.job_url_direct,
                   EXISTS(
                       SELECT 1 FROM channel_jobs cj
                       WHERE cj.job_url = j.job_url
                         AND cj.is_new = 1
                   ) AS is_new
            FROM jobs j
            WHERE (? OR j.archived_at IS NULL) AND (NOT ? OR j.archived_at IS NOT NULL)
            ORDER BY j.date_posted DESC, j.seen_at DESC
            """,
            (int(include_archived or archived_only), int(archived_only)),
        ).fetchall()
        return _group_duplicates(conn, [_row_to_card(row) for row in rows])


def _row_to_card(row: sqlite3.Row) -> dict[str, Any]:
    """Normalise a jobs row into a lightweight card record (no description)."""
    rec = dict(row)
    rec["is_remote"] = _is_remote_true(rec.get("is_remote"))
    if "is_new" in rec:
        rec["is_new"] = bool(rec["is_new"])
    return rec


# --------------------------------------------------------------------------- #
# Duplicates                                                                   #
# --------------------------------------------------------------------------- #
# Only copies with matching content, location and work mode share feedback.
# A matching title and employer alone must not hide a different opening.

_DASHES = str.maketrans({"\u2013": "-", "\u2014": "-"})


def _dup_key(job: Any) -> tuple[str, ...] | None:
    """Conservative identity: different locations or descriptions stay separate."""
    norm = lambda v: " ".join(str(v or "").translate(_DASHES).lower().split())
    title, company = norm(job["title"]), norm(job["company"])
    description, location = norm(job["description"]), norm(job["location"])
    # A generic title is insufficient evidence to propagate a rejection.
    if not title or not company or len(description) < 100 or not location:
        return None
    return (title, company, location, str(_is_remote_true(job["is_remote"])),
            norm(job["job_type"]), hashlib.sha256(description.encode()).hexdigest())


def _sibling_rows(conn: sqlite3.Connection, job_url: str) -> list[sqlite3.Row]:
    """Other stored copies of the same offer as ``job_url``."""
    row = conn.execute(
        "SELECT * FROM jobs WHERE job_url = ?", (job_url,)
    ).fetchone()
    key = _dup_key(row) if row else None
    if key is None:
        return []
    rows = conn.execute(
        "SELECT * FROM jobs WHERE job_url != ?",
        (job_url,),
    ).fetchall()
    return [r for r in rows if _dup_key(r) == key]


def _inherit_group_feedback(conn: sqlite3.Connection, urls: list[str]) -> None:
    """New copies of an offer inherit the verdict already given to the group,
    so an offer the user dismissed doesn't come back under a new URL."""
    if not urls:
        return
    rows = conn.execute(
        """
        SELECT j.*, f.verdict
        FROM jobs j LEFT JOIN feedback f ON f.job_url = j.job_url
        """
    ).fetchall()
    verdicts: dict[tuple[str, ...], set[str]] = {}
    for r in rows:
        key = _dup_key(r)
        if key and r["verdict"]:
            verdicts.setdefault(key, set()).add(r["verdict"])
    by_url = {r["job_url"]: r for r in rows}
    for url in urls:
        r = by_url.get(url)
        if r is None or r["verdict"]:
            continue
        key = _dup_key(r)
        group = verdicts.get(key) if key else None
        if not group:
            continue
        verdict = "like" if "like" in group else "dislike"
        _write_feedback(
            conn, url, verdict, r["title"] or "", r["company"] or "", r["site"] or "",
            source="inherited",
        )


def _group_duplicates(
    conn: sqlite3.Connection, cards: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Collapse copies of the same offer into one card.

    The representative is the liked copy if any, then a disliked one, then one
    with an AI analysis, then the first (newest). Locations are merged.
    The group keeps the position of its first member.
    """
    feedback = {
        r["job_url"]: r["verdict"]
        for r in conn.execute("SELECT job_url, verdict FROM feedback")
    }
    analyzed = {r["job_url"] for r in conn.execute("SELECT job_url FROM analysis")}
    tracked = {r[0] for r in conn.execute("SELECT job_url FROM applications")}
    identities = {r["job_url"]: _dup_key(r) for r in conn.execute("SELECT * FROM jobs")}
    groups: dict[Any, list[tuple[int, dict[str, Any]]]] = {}
    order: list[Any] = []
    for i, card in enumerate(cards):
        key = ("application", card["job_url"]) if card["job_url"] in tracked else identities.get(card["job_url"]) or ("", card["job_url"])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((i, card))

    rank = {"like": 0, "dislike": 1}
    out: list[dict[str, Any]] = []
    for key in order:
        members = groups[key]
        if len(members) == 1:
            out.append(members[0][1])
            continue
        _, best = min(
            members,
            key=lambda m: (
                rank.get(feedback.get(m[1]["job_url"]), 2),
                m[1]["job_url"] not in analyzed,
                m[0],
            ),
        )
        card = dict(best)
        locations: list[str] = []
        for _, m in members:
            loc = (m.get("location") or "").strip()
            if loc and loc not in locations:
                locations.append(loc)
        card["location"] = " · ".join(locations)
        card["is_new"] = any(m.get("is_new") for _, m in members)
        card["duplicates"] = len(members)
        card["duplicate_urls"] = [m["job_url"] for _, m in members]
        out.append(card)
    return out


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
    rec["is_remote"] = _is_remote_true(rec.get("is_remote"))
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
    """Return all channels with per-channel counts.

    ``total_count`` / ``new_count`` only count jobs still to review (no like or
    dislike yet), so a channel empties out as the user triages it.
    """
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
                    SUM(CASE WHEN cj.is_new = 1 THEN 1 ELSE 0 END) AS new
                FROM channel_jobs cj
                JOIN jobs j ON j.job_url = cj.job_url
                WHERE cj.channel_id = ?
                  AND j.archived_at IS NULL
                  AND cj.job_url NOT IN (SELECT job_url FROM feedback)
                  AND cj.job_url NOT IN (SELECT job_url FROM applications)
                """,
                (ch["id"],),
            ).fetchone()
            ch["total_count"] = counts["total"] or 0
            ch["new_count"] = counts["new"] or 0
            last = conn.execute(
                """
                SELECT finished_at, status FROM refresh_log
                WHERE channel_id = ? AND kind = 'refresh'
                ORDER BY id DESC LIMIT 1
                """,
                (ch["id"],),
            ).fetchone()
            ch["last_refresh_at"] = last["finished_at"] if last else None
            ch["last_refresh_status"] = last["status"] if last else None
            channels.append(ch)
    return channels


def delete_channel(channel_id: int) -> None:
    """Delete a channel and its associations (jobs themselves are kept)."""
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM channel_jobs WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))


def set_hours_old_all(hours: int) -> int:
    """Set the recency window (hours_old) on every channel. Returns rows changed."""
    with _lock, _connect() as conn:
        cur = conn.execute("UPDATE channels SET hours_old = ?", (hours,))
        return cur.rowcount


def archive_stale_jobs(days: int = 7) -> int:
    """
    Take jobs out of the feed when they have waited more than ``days`` since
    first seen without a like or dislike. Nothing is deleted: the job, its
    analyses and sightings stay in the DB (``archived_at`` is set) and keep
    counting in analytics. Jobs with a verdict are never archived.

    Returns how many jobs were archived.
    """
    with _lock, _connect() as conn:
        cur = conn.execute(
            """
            UPDATE jobs SET archived_at = ?, archive_reason = 'no_verdict'
            WHERE archived_at IS NULL
              AND first_seen_at IS NOT NULL
              AND COALESCE(feed_since, first_seen_at) < datetime('now', ?)
              AND job_url NOT IN (SELECT job_url FROM feedback)
              AND job_url NOT IN (SELECT job_url FROM applications)
            """,
            (_now(), f"-{int(days)} days"),
        )
        return cur.rowcount


def upsert_channel_jobs(
    channel_id: int, records: list[dict[str, Any]], run_id: int | None = None
) -> int:
    """Upsert jobs into `jobs` and link them to the channel.

    Returns the number of jobs that are **new** for this channel (i.e. seen for
    the first time). Existing links have their ``last_seen`` bumped so they are
    no longer flagged as new.
    """
    new_count = 0
    with _lock, _connect() as conn:
        conn.execute("UPDATE channel_jobs SET is_new = 0 WHERE channel_id = ?", (channel_id,))
        _upsert_jobs_conn(conn, records, channel_id=channel_id, run_id=run_id)
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
                    INSERT INTO channel_jobs (channel_id, job_url, first_seen, last_seen, is_new)
                    VALUES (?, ?, datetime('now'), datetime('now'), 1)
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
                   j.salary_currency, j.salary_interval, j.first_seen_at, j.archived_at, j.feed_since,
                   j.job_url_direct,
                   cj.first_seen, cj.last_seen, cj.is_new
            FROM channel_jobs cj
            JOIN jobs j ON j.job_url = cj.job_url
            WHERE cj.channel_id = ? AND j.archived_at IS NULL
            ORDER BY cj.last_seen DESC, cj.first_seen DESC
            """,
            (channel_id,),
        ).fetchall()
        jobs: list[dict[str, Any]] = []
        for row in rows:
            rec = _row_to_card(row)
            jobs.append(rec)
        return _group_duplicates(conn, jobs)


# --------------------------------------------------------------------------- #
# Refresh log                                                                  #
# --------------------------------------------------------------------------- #

_LOG_FIELDS = (
    "started_at", "kind", "trigger", "channel_id", "channel_name", "site",
    "status", "found", "new_count", "analyzed", "analysis_failed", "removed",
    "duration_ms", "error",
)


def start_log(entry: dict[str, Any]) -> int:
    """Open an update event with status 'running' and return its id.

    The row is visible in the Log page while the work is in progress and is
    completed by :func:`finish_log`. Unknown keys are ignored.
    """
    row = {**entry, "status": "running", "started_at": entry.get("started_at") or _now()}
    values = [row.get(f) for f in _LOG_FIELDS]
    cols = ", ".join(_LOG_FIELDS)
    placeholders = ", ".join("?" for _ in _LOG_FIELDS)
    with _lock, _connect() as conn:
        cur = conn.execute(
            f"INSERT INTO refresh_log ({cols}, finished_at) VALUES ({placeholders}, ?)",
            (*values, _now()),
        )
        return int(cur.lastrowid)


def finish_log(log_id: int, fields: dict[str, Any]) -> None:
    """Complete an event opened by :func:`start_log` (status ok/error + counters)."""
    keys = [f for f in _LOG_FIELDS if f in fields]
    sets = ", ".join(f"{k} = ?" for k in keys)
    with _lock, _connect() as conn:
        conn.execute(
            f"UPDATE refresh_log SET {sets}, finished_at = ? WHERE id = ?",
            (*[fields[k] for k in keys], _now(), log_id),
        )


def add_log(entry: dict[str, Any]) -> None:
    """Append one already-finished update event (unknown keys are ignored)."""
    finish_log(start_log(entry), {"status": "ok", **entry})


def mark_interrupted_logs() -> None:
    """Events left 'running' by a restart can never finish: flag them."""
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE refresh_log SET status = 'error', "
            "error = 'Interrotto dal riavvio del servizio' WHERE status = 'running'"
        )


def list_logs(limit: int = 200) -> list[dict[str, Any]]:
    """Most recent update events first."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM refresh_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Analysis                                                                     #
# --------------------------------------------------------------------------- #


def get_analyzed_urls() -> set[str]:
    """Return the set of job_urls that already have a stored analysis."""
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT job_url FROM analysis").fetchall()
    return {row["job_url"] for row in rows}


def add_analysis_run(job_url: str, run: dict[str, Any]) -> None:
    """Append one analysis attempt to ``analysis_runs`` (success or failure).

    ``run`` keys: provider, model, prompt_version, cv_version_id, status,
    result (normalised dict, on success), raw_response, input_tokens,
    output_tokens, latency_ms, error.
    """
    result = run.get("result") or {}
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs
                (job_url, provider, model, prompt_version, cv_version_id, status,
                 relevance_score, tags, summary, reasons, raw_response,
                 input_tokens, output_tokens, latency_ms, error, created_at, context_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_url, run.get("provider"), run.get("model"), run.get("prompt_version"),
                run.get("cv_version_id"), run.get("status", "ok"),
                result.get("relevance_score"),
                json.dumps(result["tags"], ensure_ascii=False) if "tags" in result else None,
                result.get("summary"),
                json.dumps(result["reasons"], ensure_ascii=False) if "reasons" in result else None,
                run.get("raw_response"), run.get("input_tokens"), run.get("output_tokens"),
                run.get("latency_ms"), run.get("error"), _now(), run.get("context_key"),
            ),
        )


# A job whose analysis failed this many times is not retried automatically.
_MAX_ANALYSIS_FAILURES = 3


def configure_analysis(model: str, prompt_version: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('analysis_config', ?)",
                     (json.dumps([model, prompt_version]),))
        _update_analysis_context(conn)


def _update_analysis_context(conn: sqlite3.Connection) -> None:
    config = conn.execute("SELECT value FROM meta WHERE key = 'analysis_config'").fetchone()
    cv = conn.execute("SELECT text FROM cv WHERE id = 1").fetchone()
    key = hashlib.sha256(((config[0] if config else '') + '\n' + (cv[0] if cv else '')).encode()).hexdigest()
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('analysis_context', ?)", (key,))


def analysis_context() -> str:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = 'analysis_context'").fetchone()
        return row[0] if row else ''


_PENDING_SQL = """
    FROM jobs j
    WHERE COALESCE(j.site, '') != 'manual'
      AND NOT EXISTS (SELECT 1 FROM analysis a WHERE a.job_url = j.job_url
        AND (a.context_key = COALESCE((SELECT value FROM meta WHERE key = 'analysis_context'), '') OR a.context_key = 'legacy'))
      AND (SELECT COUNT(*) FROM analysis_runs r WHERE r.job_url = j.job_url
           AND r.status = 'error'
           AND r.context_key = COALESCE((SELECT value FROM meta WHERE key = 'analysis_context'), '')) < ?
"""


def jobs_pending_analysis(limit: int = 50, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    # Exclude attempts before LIMIT: failing jobs must not starve later batches.
    excluded = sorted(exclude or [])
    extra = (' AND j.job_url NOT IN (' + ','.join('?' for _ in excluded) + ')') if excluded else ''
    with _lock, _connect() as conn:
        rows = conn.execute(
            'SELECT j.job_url, j.title, j.company, j.location, j.is_remote, j.job_type, j.description '
            + _PENDING_SQL + extra + ' ORDER BY j.archived_at IS NOT NULL, j.first_seen_at DESC LIMIT ?',
            (_MAX_ANALYSIS_FAILURES, *excluded, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def count_pending_analysis() -> int:
    with _lock, _connect() as conn:
        return conn.execute('SELECT COUNT(*) ' + _PENDING_SQL, (_MAX_ANALYSIS_FAILURES,)).fetchone()[0]


def set_analysis(job_url: str, analysis: dict[str, Any], context_key: str | None = None) -> None:
    """Store (or replace) the analysis for a job."""
    if not job_url:
        return
    context_key = analysis_context() if context_key is None else context_key
    tags = json.dumps(analysis.get("tags", []), ensure_ascii=False)
    reasons = json.dumps(analysis.get("reasons", []), ensure_ascii=False)
    summary = analysis.get("summary", "")
    score = analysis.get("relevance_score")
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO analysis (job_url, tags, summary, relevance_score, reasons, analyzed_at, context_key, assessment)
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)
            ON CONFLICT(job_url) DO UPDATE SET
                context_key = excluded.context_key,
                assessment = excluded.assessment,
                tags            = excluded.tags,
                summary         = excluded.summary,
                relevance_score = excluded.relevance_score,
                reasons         = excluded.reasons,
                analyzed_at     = datetime('now')
            """,
            (job_url, tags, summary, score, reasons, context_key, json.dumps(analysis.get("assessment", {}), ensure_ascii=False)),
        )


def get_all_analysis() -> dict[str, dict[str, Any]]:
    """Return ``{job_url: {tags, summary, relevance_score, reasons}}`` for all analyzed jobs."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT job_url, tags, summary, relevance_score, reasons, assessment FROM analysis "
            "WHERE (context_key = COALESCE((SELECT value FROM meta WHERE key = 'analysis_context'), '') OR context_key = 'legacy')"
        ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result[row["job_url"]] = {
            "assessment": json.loads(row["assessment"] or "{}"),
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


def _cv_version_conn(conn: sqlite3.Connection, text: str, created_at: str | None = None) -> int:
    """Id of the ``cv_versions`` row for this exact text, creating it if new."""
    digest = hashlib.sha256(text.encode()).hexdigest()
    row = conn.execute("SELECT id FROM cv_versions WHERE sha256 = ?", (digest,)).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO cv_versions (sha256, text, created_at) VALUES (?, ?, ?)",
        (digest, text, created_at or _now()),
    )
    return int(cur.lastrowid)


def current_cv_version_id() -> int | None:
    """Version id of the CV currently used for analyses (None if no CV)."""
    with _lock, _connect() as conn:
        row = conn.execute("SELECT text FROM cv WHERE id = 1").fetchone()
        return _cv_version_conn(conn, row["text"]) if row and row["text"] else None


def set_cv_text(text: str) -> None:
    """Store the current CV text (single row) and record it as a version."""
    with _lock, _connect() as conn:
        _cv_version_conn(conn, text)
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
        _update_analysis_context(conn)


def get_cv_text() -> str:
    """Return the stored CV text, or an empty string if none."""
    with _lock, _connect() as conn:
        row = conn.execute("SELECT text FROM cv WHERE id = 1").fetchone()
    return row["text"] if row else ""


# ---------------------------------------------------------------------------
# Analytics aggregation
# ---------------------------------------------------------------------------

def _is_remote_true(value: Any) -> bool:
    """`jobs.is_remote` is stored as TEXT ('True'/'False'/'1'/None)."""
    return str(value).strip().lower() in ("true", "1", "yes")


def _to_float(value: Any) -> float | None:
    try:
        f = float(value)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_list(raw: Any) -> list[str]:
    """Parse a skills/tags cell that may be JSON or a comma/semicolon string."""
    if not raw:
        return []
    text = str(raw).strip()
    try:
        arr = json.loads(text)
        if isinstance(arr, list):
            return [str(x).strip() for x in arr if str(x).strip()]
    except (ValueError, TypeError):
        pass
    return [p.strip() for p in re.split(r"[,;]", text) if p.strip()]


# Tokens that show up in AI tags but are NOT skills (seniority, work mode, …).
_SKILL_STOPWORDS = {
    "senior", "junior", "mid", "middle", "lead", "principal", "staff",
    "remote", "on-site", "onsite", "on site", "no remote", "full remote",
    "hybrid", "ibrido", "smart working", "stage", "internship", "tirocinio",
    "full-time", "part-time", "full time", "part time", "freelance",
    "permanent", "contract", "neolaureato", "entry level", "entry-level",
}


def _top_counts(counter: dict[str, int], limit: int) -> list[dict[str, Any]]:
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"name": name, "count": n} for name, n in items[:limit]]


def analytics_summary() -> dict[str, Any]:
    """Aggregate the stored data into KPIs + market-intelligence breakdowns.

    Computed in Python over a single read of the (small) jobs table so the
    logic stays simple and robust to the TEXT-typed rich columns.
    """
    with _lock, _connect() as conn:
        jobs = [dict(r) for r in conn.execute("SELECT * FROM jobs").fetchall()]
        scores = [
            r["relevance_score"]
            for r in conn.execute(
                "SELECT relevance_score FROM analysis WHERE relevance_score IS NOT NULL "
                "AND (context_key = COALESCE((SELECT value FROM meta WHERE key='analysis_context'), '') OR context_key = 'legacy')"
            ).fetchall()
        ]
        tag_rows = [r["tags"] for r in conn.execute("SELECT tags FROM analysis WHERE context_key = COALESCE((SELECT value FROM meta WHERE key='analysis_context'), '') OR context_key = 'legacy'").fetchall()]
        likes = conn.execute(
            "SELECT COUNT(*) AS n FROM feedback WHERE verdict = 'like'"
        ).fetchone()["n"]
        dislikes = conn.execute(
            "SELECT COUNT(*) AS n FROM feedback WHERE verdict = 'dislike'"
        ).fetchone()["n"]
        channel_count = conn.execute("SELECT COUNT(*) AS n FROM channels").fetchone()["n"]
        new_7d = conn.execute(
            "SELECT COUNT(*) AS n FROM jobs WHERE seen_at >= datetime('now', '-7 days')"
        ).fetchone()["n"]
        one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
        database = {
            "since": one("SELECT MIN(first_seen_at) FROM jobs"),
            "jobs": one("SELECT COUNT(*) FROM jobs"),
            "in_feed": one(
                "SELECT COUNT(*) FROM jobs WHERE archived_at IS NULL "
                "AND job_url NOT IN (SELECT job_url FROM feedback)"
            ),
            "archived": one("SELECT COUNT(*) FROM jobs WHERE archived_at IS NOT NULL"),
            "analyzed": one("SELECT COUNT(*) FROM analysis"),
            "analysis_runs": one("SELECT COUNT(*) FROM analysis_runs"),
            "analysis_errors": one("SELECT COUNT(*) FROM analysis_runs WHERE status = 'error'"),
            "tokens": one(
                "SELECT COALESCE(SUM(input_tokens), 0) + COALESCE(SUM(output_tokens), 0) "
                "FROM analysis_runs"
            ),
            "sightings": one("SELECT COUNT(*) FROM job_sightings"),
            "versions": one("SELECT COUNT(*) FROM job_versions"),
            "feedback_events": one("SELECT COUNT(*) FROM feedback_events"),
            "cv_versions": one("SELECT COUNT(*) FROM cv_versions"),
        }

    total = len(jobs)
    remote = sum(1 for j in jobs if _is_remote_true(j.get("is_remote")))

    # Salary: midpoints of whatever min/max we have, plus coarse buckets (k/yr).
    mids: list[float] = []
    currency_counter: dict[str, int] = {}
    for j in jobs:
        lo, hi = _to_float(j.get("salary_min")), _to_float(j.get("salary_max"))
        vals = [v for v in (lo, hi) if v is not None]
        mid = sum(vals) / len(vals) if vals else 0
        # Drop non-annual outliers (hourly/monthly figures scraped as salary).
        if mid < 1000:
            continue
        mids.append(mid)
        cur = (j.get("salary_currency") or "").strip() or "?"
        currency_counter[cur] = currency_counter.get(cur, 0) + 1

    salary: dict[str, Any] = {"count": len(mids)}
    if mids:
        mids_sorted = sorted(mids)
        n = len(mids_sorted)
        salary["min"] = round(mids_sorted[0])
        salary["max"] = round(mids_sorted[-1])
        salary["median"] = round(mids_sorted[n // 2])
        salary["currency"] = max(currency_counter, key=lambda k: currency_counter[k])
        edges = [(0, 30_000), (30_000, 50_000), (50_000, 80_000),
                 (80_000, 120_000), (120_000, 10**12)]
        labels = ["<30k", "30–50k", "50–80k", "80–120k", "120k+"]
        buckets = []
        for (lo, hi), label in zip(edges, labels):
            buckets.append(
                {"range": label, "count": sum(1 for m in mids_sorted if lo <= m < hi)}
            )
        salary["buckets"] = buckets

    # Location words (cities/countries) are noise in the skills chart — collect
    # them so we can exclude e.g. "Verona" from "top skills".
    location_words: set[str] = set()
    for j in jobs:
        for part in re.split(r"[,/|]", (j.get("location") or "")):
            token = part.strip().lower()
            if token:
                location_words.add(token)

    def _is_skill(token: str) -> bool:
        low = token.strip().lower()
        return bool(low) and low not in _SKILL_STOPWORDS and low not in location_words

    # Skills from jobs.skills + AI tags; companies, industries, remote-by-site.
    skill_counter: dict[str, int] = {}
    company_counter: dict[str, int] = {}
    industry_counter: dict[str, int] = {}
    site_counter: dict[str, dict[str, int]] = {}
    for j in jobs:
        for s in _parse_list(j.get("skills")):
            if not _is_skill(s):
                continue
            key = s.title()
            skill_counter[key] = skill_counter.get(key, 0) + 1
        company = (j.get("company") or "").strip()
        if company:
            company_counter[company] = company_counter.get(company, 0) + 1
        industry = (j.get("company_industry") or "").strip()
        if industry:
            industry_counter[industry] = industry_counter.get(industry, 0) + 1
        site = (j.get("site") or "?").strip()
        bucket = site_counter.setdefault(site, {"remote": 0, "onsite": 0})
        bucket["remote" if _is_remote_true(j.get("is_remote")) else "onsite"] += 1
    for raw in tag_rows:
        for t in _parse_list(raw):
            if not _is_skill(t):
                continue
            key = t.title()
            skill_counter[key] = skill_counter.get(key, 0) + 1

    remote_by_site = [
        {"site": site, "remote": c["remote"], "onsite": c["onsite"]}
        for site, c in sorted(
            site_counter.items(), key=lambda kv: -(kv[1]["remote"] + kv[1]["onsite"])
        )
    ]

    return {
        "database": database,
        "kpis": {
            "total": total,
            "new_7d": new_7d,
            "remote_pct": round(remote / total * 100) if total else 0,
            "avg_score": round(sum(scores) / len(scores)) if scores else None,
            "analyzed": len(scores),
            "favorites": likes,
            "dismissed": dislikes,
            "channels": channel_count,
        },
        "salary": salary,
        "top_skills": _top_counts(skill_counter, 15),
        "top_companies": _top_counts(company_counter, 10),
        "top_industries": _top_counts(industry_counter, 8),
        "remote_by_site": remote_by_site,
    }


APPLICATION_STATUSES = {"to_apply", "applied", "contacted", "interview", "rejected", "offer", "withdrawn"}


def get_applications() -> dict[str, dict[str, Any]]:
    with _lock, _connect() as conn:
        return {r["job_url"]: dict(r) for r in conn.execute("SELECT * FROM applications")}


def _set_application_conn(conn: sqlite3.Connection, job_url: str, data: dict[str, Any]) -> None:
    if data['status'] not in APPLICATION_STATUSES:
        raise ValueError("Stato candidatura non valido")
    if not conn.execute("SELECT 1 FROM jobs WHERE job_url=?", (job_url,)).fetchone():
        raise KeyError(job_url)
    old = conn.execute("SELECT * FROM applications WHERE job_url=?", (job_url,)).fetchone()
    changes = {k: {'from': old[k] if old else None, 'to': v}
               for k, v in data.items() if not old or old[k] != v}
    if not changes:
        return
    columns = list(data)
    conn.execute(
        f"INSERT INTO applications(job_url,{','.join(columns)},updated_at) VALUES ({','.join('?' for _ in range(len(columns)+2))}) "
        f"ON CONFLICT(job_url) DO UPDATE SET {','.join(f'{k}=excluded.{k}' for k in columns)},updated_at=excluded.updated_at",
        (job_url, *data.values(), _now()),
    )
    conn.execute("INSERT INTO application_events(job_url,kind,content,occurred_on,created_at) VALUES (?,?,?,?,?)",
                 (job_url, 'updated' if old else 'created', json.dumps(changes, ensure_ascii=False), _now()[:10], _now()))
    conn.execute("UPDATE jobs SET archived_at=NULL, archive_reason=NULL WHERE job_url=?", (job_url,))


def set_application(job_url: str, status: str, applied_on: str | None = None,
                    notes: str = '', next_step: str = '', follow_up_on: str | None = None,
                    cv_label: str = '', contact: str = '') -> None:
    with _lock, _connect() as conn:
        _set_application_conn(conn, job_url, dict(status=status, applied_on=applied_on, notes=notes,
            next_step=next_step, follow_up_on=follow_up_on, cv_label=cv_label, contact=contact))


def create_manual_application(title: str, company: str, url: str | None, location: str,
                              **data: Any) -> str:
    """Create the job and tracker atomically; never overwrite an existing application."""
    job_url = url or f'manual:{uuid.uuid4()}'
    with _lock, _connect() as conn:
        if conn.execute("SELECT 1 FROM applications WHERE job_url=?", (job_url,)).fetchone():
            raise ValueError("Esiste già una candidatura per questo link: aprila dalla lista.")
        if not conn.execute("SELECT 1 FROM jobs WHERE job_url=?", (job_url,)).fetchone():
            _upsert_jobs_conn(conn, [dict(job_url=job_url, site='manual', title=title,
                                        company=company, location=location)])
        _set_application_conn(conn, job_url, data)
    return job_url


def application_events(job_url: str) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM application_events WHERE job_url=? ORDER BY occurred_on DESC, id DESC",
                            (job_url,)).fetchall()
    return [{**dict(row), 'content': json.loads(row['content'])} for row in rows]


def add_application_note(job_url: str, text: str, occurred_on: str) -> None:
    with _lock, _connect() as conn:
        if not conn.execute("SELECT 1 FROM applications WHERE job_url=?", (job_url,)).fetchone():
            raise KeyError(job_url)
        conn.execute("INSERT INTO application_events(job_url,kind,content,occurred_on,created_at) VALUES (?,?,?,?,?)",
                     (job_url, 'note', json.dumps({'text': text}, ensure_ascii=False), occurred_on, _now()))


def restore_job(job_url: str) -> bool:
    with _lock, _connect() as conn:
        urls = [job_url, *[row["job_url"] for row in _sibling_rows(conn, job_url)]]
        changed = False
        for url in urls:
            changed |= bool(conn.execute(
                "UPDATE jobs SET archived_at=NULL, archive_reason=NULL, feed_since=? "
                "WHERE job_url=? AND archived_at IS NOT NULL", (_now(), url),
            ).rowcount)
        return changed
