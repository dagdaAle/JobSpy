"""
Infrastructure shared by the non-job areas (Concorsi PA, Gare P.IVA).

Knows nothing about either area: each one builds an :class:`AreaStore` with its
own table prefix, its own sources and its own extraction prompt. Lavoro (the
job feed) does not use this module, and the areas never import each other.
"""

from __future__ import annotations

import datetime
import json
import threading
import time
from typing import Any, Callable, Literal

import analyzer
import requests
import storage
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "Mozilla/5.0 (compatible; JobSpy/1.0)"
MAX_EXTRACTION_FAILURES = 3
DECISIONS = ("adatto", "da_valutare", "non_adatto")

CHANNEL_FIELDS = (
    "name", "source", "query", "location", "cpv", "country", "days", "max_amount", "results_wanted",
)
ITEM_FIELDS = (
    "source", "title", "body", "buyer", "kind", "place", "deadline", "published_at", "url",
    "amount", "currency", "cpv", "raw_json",
)


class SourceError(RuntimeError):
    """A source answered with an error or with something that is not a result."""


def http_session() -> requests.Session:
    """Session with retries on network errors and 5xx, and a plain user agent."""
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=1, status_forcelist=(500, 502, 503, 504), allowed_methods=None,
    ))
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def today() -> str:
    return datetime.date.today().isoformat()


def llm_json(system: str, user: str, max_tokens: int = 900) -> dict[str, Any]:
    """One JSON-mode call on the configured DeepSeek model.

    Raises :class:`analyzer.AnalyzerNotConfigured` when no key is set.
    """
    response = analyzer._client().chat.completions.create(
        model=analyzer.MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=max_tokens,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return data if isinstance(data, dict) else {}


class AreaStore:
    """Tables ``<prefix>_*`` for one area, in the shared SQLite DB (ADR 003)."""

    def __init__(self, prefix: str) -> None:
        if not prefix.isidentifier():
            raise ValueError(f"bad prefix {prefix!r}")
        self.p = prefix

    # ------------------------------------------------------------------ schema
    def init_tables(self) -> None:
        p = self.p
        with storage._lock, storage._connect() as conn:
            conn.executescript(f"""
                CREATE TABLE IF NOT EXISTS {p}_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL, source TEXT, query TEXT, location TEXT, cpv TEXT,
                    country TEXT, days INTEGER, max_amount REAL, results_wanted INTEGER DEFAULT 50,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    last_refresh_at TEXT, last_refresh_status TEXT
                );
                CREATE TABLE IF NOT EXISTS {p}_items (
                    key TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT NOT NULL, body TEXT,
                    buyer TEXT, kind TEXT, place TEXT, deadline TEXT, published_at TEXT, url TEXT,
                    amount REAL, currency TEXT, cpv TEXT, raw_json TEXT,
                    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
                    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
                    archived_at TEXT
                );
                CREATE TABLE IF NOT EXISTS {p}_channel_items (
                    channel_id INTEGER NOT NULL, key TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY (channel_id, key)
                );
                CREATE TABLE IF NOT EXISTS {p}_verdicts (
                    key TEXT PRIMARY KEY, verdict TEXT NOT NULL CHECK (verdict IN ('like', 'dislike')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS {p}_extractions (
                    key TEXT PRIMARY KEY, prompt_version TEXT NOT NULL, facts_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS {p}_extraction_errors (
                    key TEXT NOT NULL, prompt_version TEXT NOT NULL, error TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)

    # ---------------------------------------------------------------- channels
    def list_channels(self) -> list[dict[str, Any]]:
        with storage._lock, storage._connect() as conn:
            rows = conn.execute(f"SELECT * FROM {self.p}_channels ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get_channel(self, channel_id: int) -> dict[str, Any] | None:
        with storage._lock, storage._connect() as conn:
            row = conn.execute(f"SELECT * FROM {self.p}_channels WHERE id = ?", (channel_id,)).fetchone()
        return dict(row) if row else None

    def create_channel(self, fields: dict[str, Any]) -> dict[str, Any]:
        cols = [f for f in CHANNEL_FIELDS if fields.get(f) is not None]
        with storage._lock, storage._connect() as conn:
            cur = conn.execute(
                f"INSERT INTO {self.p}_channels ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                [fields[c] for c in cols],
            )
            channel_id = cur.lastrowid
        channel = self.get_channel(int(channel_id or 0))
        assert channel is not None
        return channel

    def delete_channel(self, channel_id: int) -> None:
        """Remove the channel and its links; items and verdicts stay."""
        with storage._lock, storage._connect() as conn:
            conn.execute(f"DELETE FROM {self.p}_channel_items WHERE channel_id = ?", (channel_id,))
            conn.execute(f"DELETE FROM {self.p}_channels WHERE id = ?", (channel_id,))

    def mark_refresh(self, channel_id: int, status: str) -> None:
        with storage._lock, storage._connect() as conn:
            conn.execute(
                f"UPDATE {self.p}_channels SET last_refresh_at = datetime('now'), last_refresh_status = ? "
                "WHERE id = ?", (status, channel_id),
            )

    # ------------------------------------------------------------------- items
    def upsert_items(self, channel_id: int, items: list[dict[str, Any]]) -> int:
        """Store items and link them to the channel. Returns how many are new to the channel."""
        p = self.p
        new = 0
        with storage._lock, storage._connect() as conn:
            for item in items:
                values = [item.get(f) for f in ITEM_FIELDS]
                conn.execute(
                    f"INSERT INTO {p}_items (key, {', '.join(ITEM_FIELDS)}) "
                    f"VALUES (?, {', '.join('?' for _ in ITEM_FIELDS)}) "
                    f"ON CONFLICT(key) DO UPDATE SET "
                    + ", ".join(f"{f} = excluded.{f}" for f in ITEM_FIELDS)
                    + ", last_seen_at = datetime('now')",
                    (item["key"], *values),
                )
                cur = conn.execute(
                    f"INSERT OR IGNORE INTO {p}_channel_items (channel_id, key) VALUES (?, ?)",
                    (channel_id, item["key"]),
                )
                new += cur.rowcount
        return new

    def list_items(self, view: str = "feed", channel_id: int | None = None) -> list[dict[str, Any]]:
        """Items for a view: feed (open, no verdict), saved, dismissed, archived (closed or expired)."""
        p = self.p
        open_sql = f"i.archived_at IS NULL AND (i.deadline IS NULL OR i.deadline >= '{today()}')"
        where = {
            "feed": f"{open_sql} AND v.verdict IS NULL",
            "saved": "v.verdict = 'like'",
            "dismissed": "v.verdict = 'dislike'",
            "archived": f"NOT ({open_sql}) AND v.verdict IS NULL",
        }.get(view)
        if where is None:
            raise ValueError(f"unknown view {view!r}")
        params: list[Any] = []
        if channel_id is not None:
            where += f" AND i.key IN (SELECT key FROM {p}_channel_items WHERE channel_id = ?)"
            params.append(channel_id)
        with storage._lock, storage._connect() as conn:
            rows = conn.execute(
                f"""SELECT i.*, v.verdict, e.facts_json,
                       (SELECT group_concat(channel_id) FROM {p}_channel_items c WHERE c.key = i.key) AS channel_csv
                    FROM {p}_items i
                    LEFT JOIN {p}_verdicts v ON v.key = i.key
                    LEFT JOIN {p}_extractions e ON e.key = i.key
                    WHERE {where}
                    ORDER BY (i.deadline IS NULL), i.deadline, i.first_seen_at DESC""",
                params,
            ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            item.pop("raw_json", None)
            facts = item.pop("facts_json")
            item["facts"] = json.loads(facts) if facts else None
            csv = item.pop("channel_csv")
            item["channel_ids"] = [int(x) for x in csv.split(",")] if csv else []
            out.append(item)
        return out

    def set_verdict(self, key: str, verdict: str | None) -> None:
        with storage._lock, storage._connect() as conn:
            if verdict is None:
                conn.execute(f"DELETE FROM {self.p}_verdicts WHERE key = ?", (key,))
            else:
                conn.execute(
                    f"INSERT INTO {self.p}_verdicts (key, verdict) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET verdict = excluded.verdict, updated_at = datetime('now')",
                    (key, verdict),
                )

    def has_item(self, key: str) -> bool:
        with storage._lock, storage._connect() as conn:
            return conn.execute(f"SELECT 1 FROM {self.p}_items WHERE key = ?", (key,)).fetchone() is not None

    # ------------------------------------------------------------- extraction
    def pending_extraction(self, prompt_version: str, limit: int = 50) -> list[dict[str, Any]]:
        """Open items without facts for this prompt version, skipping disliked and failing ones."""
        p = self.p
        with storage._lock, storage._connect() as conn:
            rows = conn.execute(
                f"""SELECT i.* FROM {p}_items i
                    WHERE i.archived_at IS NULL AND (i.deadline IS NULL OR i.deadline >= ?)
                      AND i.key NOT IN (SELECT key FROM {p}_verdicts WHERE verdict = 'dislike')
                      AND i.key NOT IN (SELECT key FROM {p}_extractions WHERE prompt_version = ?)
                      AND (SELECT COUNT(*) FROM {p}_extraction_errors x
                           WHERE x.key = i.key AND x.prompt_version = ?) < ?
                    ORDER BY i.first_seen_at DESC LIMIT ?""",
                (today(), prompt_version, prompt_version, MAX_EXTRACTION_FAILURES, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def save_extraction(self, key: str, prompt_version: str, facts: dict[str, Any]) -> None:
        with storage._lock, storage._connect() as conn:
            conn.execute(
                f"INSERT INTO {self.p}_extractions (key, prompt_version, facts_json) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET prompt_version = excluded.prompt_version, "
                "facts_json = excluded.facts_json, created_at = datetime('now')",
                (key, prompt_version, json.dumps(facts, ensure_ascii=False)),
            )

    def save_extraction_error(self, key: str, prompt_version: str, error: str) -> None:
        with storage._lock, storage._connect() as conn:
            conn.execute(
                f"INSERT INTO {self.p}_extraction_errors (key, prompt_version, error) VALUES (?, ?, ?)",
                (key, prompt_version, error[:500]),
            )

    # ---------------------------------------------------------------- profile
    def get_profile(self, default: dict[str, Any]) -> dict[str, Any]:
        with storage._lock, storage._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (f"{self.p}_profile",)).fetchone()
        return {**default, **json.loads(row[0])} if row else dict(default)

    def set_profile(self, profile: dict[str, Any]) -> None:
        with storage._lock, storage._connect() as conn:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (f"{self.p}_profile", json.dumps(profile, ensure_ascii=False)),
            )


def refresh_channel(
    store: AreaStore,
    channel: dict[str, Any],
    fetch: Callable[[dict[str, Any]], list[dict[str, Any]]],
    trigger: str,
) -> int:
    """Run ``fetch`` for a channel, store what it returns, log the run. Raises on failure."""
    site = f"{store.p}:{channel.get('source') or 'ted'}"
    log_id = storage.start_log({
        "kind": "refresh", "trigger": trigger, "channel_id": None,
        "channel_name": f"[{store.p.upper()}] {channel['name']}", "site": site,
    })
    t0 = time.monotonic()
    try:
        items = fetch(channel)
        new_count = store.upsert_items(channel["id"], items)
    except Exception as exc:
        store.mark_refresh(channel["id"], "error")
        storage.finish_log(log_id, {
            "status": "error", "error": str(exc)[:500], "duration_ms": int((time.monotonic() - t0) * 1000),
        })
        raise
    store.mark_refresh(channel["id"], "ok")
    storage.finish_log(log_id, {
        "status": "ok", "found": len(items), "new_count": new_count,
        "duration_ms": int((time.monotonic() - t0) * 1000),
    })
    return new_count


def extract_pending(
    store: AreaStore,
    prompt_version: str,
    extract: Callable[[dict[str, Any]], dict[str, Any]],
    trigger: str,
) -> int:
    """Extract facts for every pending item of an area; logs one 'analysis' event. Returns how many."""
    if not analyzer.is_configured():
        return 0
    pending = store.pending_extraction(prompt_version)
    if not pending:
        return 0
    t0 = time.monotonic()
    done = failed = 0
    for item in pending:
        try:
            store.save_extraction(item["key"], prompt_version, extract(item))
            done += 1
        except Exception as exc:
            store.save_extraction_error(item["key"], prompt_version, str(exc))
            failed += 1
    storage.add_log({
        "kind": "analysis", "trigger": trigger, "site": store.p, "found": len(pending),
        "analyzed": done, "analysis_failed": failed, "duration_ms": int((time.monotonic() - t0) * 1000),
    })
    return done


class Area:
    """Everything an area plugs into the generic router and the scheduler."""

    def __init__(
        self,
        prefix: str,
        fetchers: dict[str, Callable[[dict[str, Any]], list[dict[str, Any]]]],
        prompt_version: str,
        extract: Callable[[dict[str, Any]], dict[str, Any]],
        decide: Callable[[dict[str, Any] | None, dict[str, Any]], tuple[str | None, list[str]]],
        default_profile: dict[str, Any],
        vocabulary: tuple[str, ...],
        post_filter: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None,
    ) -> None:
        self.store = AreaStore(prefix)
        self.fetchers = fetchers
        self.prompt_version = prompt_version
        self.extract = extract
        self.decide = decide
        self.default_profile = default_profile
        self.vocabulary = vocabulary
        self.post_filter = post_filter
        self._analysis_lock = threading.Lock()

    def fetch(self, channel: dict[str, Any]) -> list[dict[str, Any]]:
        fetcher = self.fetchers.get(channel.get("source") or next(iter(self.fetchers)))
        if fetcher is None:
            raise SourceError(f"unknown source {channel.get('source')!r}")
        items = fetcher(channel)
        if self.post_filter:
            items = [i for i in items if self.post_filter(i, channel)]
        return items

    def refresh(self, channel: dict[str, Any], trigger: str) -> int:
        return refresh_channel(self.store, channel, self.fetch, trigger)

    def refresh_all(self, trigger: str = "scheduler") -> None:
        """One refresh per channel; a failing channel is logged and skipped (ADR 004)."""
        for channel in self.store.list_channels():
            try:
                self.refresh(channel, trigger)
            except Exception as exc:
                print(f"[scheduler] {self.store.p} channel {channel['id']} failed: {exc}", flush=True)

    def analyze_pending(self, trigger: str = "scheduler") -> int:
        """Extract facts for pending items; a run already in progress makes this a no-op."""
        if not self._analysis_lock.acquire(blocking=False):
            return 0
        try:
            return extract_pending(self.store, self.prompt_version, self.extract, trigger)
        finally:
            self._analysis_lock.release()

    def kick_analysis(self, trigger: str = "manual") -> None:
        threading.Thread(target=self.analyze_pending, args=(trigger,), daemon=True).start()

    def items(self, view: str, channel_id: int | None) -> list[dict[str, Any]]:
        profile = self.store.get_profile(self.default_profile)
        out = []
        for item in self.store.list_items(view, channel_id):
            item["decision"], item["reasons"] = self.decide(item["facts"], profile)
            out.append(item)
        return out


class ChannelIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source: str | None = None
    query: str | None = Field(None, max_length=200)
    location: str | None = Field(None, max_length=120)
    cpv: str | None = Field(None, max_length=200, pattern=r"^[\d,\s]*$")
    country: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    days: int | None = Field(None, ge=1, le=90)
    max_amount: float | None = Field(None, gt=0)
    results_wanted: int = Field(50, ge=1, le=200)

class VerdictIn(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    verdict: Literal["like", "dislike"] | None = None


def area_router(area: Area) -> APIRouter:
    """The ``/<prefix>`` API of an area (contract in specs/002-pa-gare-areas/plan.md)."""
    router = APIRouter(prefix=f"/{area.store.p}", tags=[area.store.p])
    sources = tuple(area.fetchers)

    def channel_or_404(channel_id: int) -> dict[str, Any]:
        channel = area.store.get_channel(channel_id)
        if channel is None:
            raise HTTPException(status_code=404, detail="Canale non trovato.")
        return channel

    @router.get("/meta")
    def meta() -> dict[str, Any]:
        return {"sources": list(sources), "vocabulary": list(area.vocabulary)}

    @router.get("/channels")
    def channels() -> dict[str, Any]:
        return {"channels": area.store.list_channels()}

    @router.post("/channels")
    def create_channel(req: ChannelIn) -> dict[str, Any]:
        fields = req.model_dump()
        if fields["source"] is None:
            fields["source"] = sources[0]
        if fields["source"] not in sources:
            raise HTTPException(status_code=422, detail=f"Fonte sconosciuta: {fields['source']}")
        channel = area.store.create_channel(fields)
        try:
            new_count = area.refresh(channel, "create")
        except Exception as exc:
            return {"channel": area.store.get_channel(channel["id"]), "new_count": 0, "error": str(exc)[:300]}
        area.kick_analysis("create")
        return {"channel": area.store.get_channel(channel["id"]), "new_count": new_count}

    @router.delete("/channels/{channel_id}")
    def delete_channel(channel_id: int) -> dict[str, Any]:
        channel_or_404(channel_id)
        area.store.delete_channel(channel_id)
        return {"ok": True}

    @router.post("/channels/{channel_id}/refresh")
    def refresh(channel_id: int) -> dict[str, Any]:
        try:
            new_count = area.refresh(channel_or_404(channel_id), "manual")
        except SourceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)[:300]) from exc
        area.kick_analysis("manual")
        return {"new_count": new_count}

    @router.get("/items")
    def items(
        view: Literal["feed", "saved", "dismissed", "archived"] = "feed",
        channel_id: int | None = Query(None),
    ) -> dict[str, Any]:
        return {"items": area.items(view, channel_id)}

    @router.post("/verdict")
    def verdict(req: VerdictIn) -> dict[str, Any]:
        if not area.store.has_item(req.key):
            raise HTTPException(status_code=404, detail="Voce non trovata.")
        area.store.set_verdict(req.key, req.verdict)
        return {"ok": True}

    @router.get("/profile")
    def get_profile() -> dict[str, Any]:
        return area.store.get_profile(area.default_profile)

    @router.put("/profile")
    def put_profile(profile: dict[str, Any]) -> dict[str, Any]:
        # Only the keys the area knows, so a typo cannot pile up in meta.
        clean = {k: profile[k] for k in area.default_profile if k in profile}
        area.store.set_profile(clean)
        return area.store.get_profile(area.default_profile)

    return router
