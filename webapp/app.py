"""
Local web app around the JobSpy library.

Endpoints:
* ``GET  /``            -> serves the single-page UI.
* ``POST /search``      -> runs a search (Italy preset or remote-only) and returns JSON.
* ``POST /feedback``    -> stores a like/dislike for a job.
* ``GET  /export``      -> downloads the last search result as CSV or XLSX.

It is intentionally single-process and stateless except for:
* the SQLite feedback DB (see ``storage.py``), and
* the last search result kept in memory so ``/export`` can reuse it.

This is meant for local, personal use (run via Docker); it does no auth.
"""

from __future__ import annotations

import datetime
import io
import math
import os
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jobspy.presets import (
    ITALY_EXTRA_SITES,
    ITALY_LOCAL_SITES,
    REMOTE_ONLY_SITES,
    search_italy,
    search_remote,
    search_site,
)

import analyzer
import storage

app = FastAPI(title="JobSpy Web", version="2.0.0")

# Columns we expose to the frontend (subset of JobSpy's DataFrame).
_DISPLAY_COLUMNS = [
    "site",
    "title",
    "company",
    "location",
    "is_remote",
    "job_type",
    "date_posted",
    "job_url",
]

# Columns needed for analysis (adds description on top of display columns).
_ANALYSIS_COLUMNS = _DISPLAY_COLUMNS + ["description"]

# Rich columns pulled straight from the JobSpy DataFrame (same name in DB).
_RICH_PASSTHROUGH = [
    "job_url_direct",
    "company_url",
    "company_industry",
    "company_logo",
    "banner_photo_url",
    "job_level",
    "job_function",
    "emails",
    "skills",
]
# DataFrame compensation columns -> DB salary columns.
_SALARY_MAP = {
    "min_amount": "salary_min",
    "max_amount": "salary_max",
    "currency": "salary_currency",
    "interval": "salary_interval",
}
# Full column set stored for a channel job (rich detail page + analysis).
_FULL_COLUMNS = _ANALYSIS_COLUMNS + _RICH_PASSTHROUGH + list(_SALARY_MAP.keys())

# Parallel DeepSeek calls while analyzing. Every job gets analyzed; this only
# bounds how many requests are in flight at once.
_ANALYSIS_WORKERS = int(os.environ.get("ANALYSIS_WORKERS", "5"))

# A job with no like/dislike leaves the feed this many days after it was first
# seen. It is archived, never deleted.
_FEED_DAYS = int(os.environ.get("FEED_DAYS", "7"))

# Default recency window (hours_old) for /maintenance/recency.
_RECENCY_DAYS = 14

# Hour of the day (local time, 0-23) at which channels refresh. Default 09:00.
_REFRESH_HOUR = int(os.environ.get("REFRESH_HOUR", "9"))
_REFRESH_MINUTE = int(os.environ.get("REFRESH_MINUTE", "0"))

# The most recent search result, reused by /export. Single-user local app.
_last_result: pd.DataFrame = pd.DataFrame()

# Serialize scraping so the scheduler and manual actions don't overlap.
_scrape_lock = threading.Lock()


class SearchRequest(BaseModel):
    mode: Literal["italy", "remote"] = "italy"
    search_term: str = Field(..., min_length=1)
    location: str = ""
    distance_km: int = Field(25, ge=1, le=500)
    results_wanted: int = Field(25, ge=1, le=500)
    hours_old: int | None = Field(None, ge=1)
    sites: list[str] | None = None
    include_linkedin: bool = True


class FeedbackRequest(BaseModel):
    job_url: str = Field(..., min_length=1)
    verdict: Literal["like", "dislike"] | None = None
    title: str = ""
    company: str = ""
    site: str = ""


# All sites that can back a channel.
_ALL_SITES = ITALY_LOCAL_SITES + ITALY_EXTRA_SITES + REMOTE_ONLY_SITES


class ChannelRequest(BaseModel):
    site: str = Field(..., min_length=1)
    search_term: str = Field(..., min_length=1)
    name: str = ""
    location: str = ""
    distance_km: int = Field(25, ge=1, le=500)
    results_wanted: int = Field(25, ge=1, le=500)
    hours_old: int | None = Field(None, ge=1)
    is_remote: bool = False


@app.on_event("startup")
def _startup() -> None:
    storage.init_db()
    storage.mark_interrupted_logs()
    # Re-read the mounted CV at every start: a changed PDF becomes a new CV
    # version (older analyses stay linked to the CV they were made with).
    try:
        cv_text = analyzer.extract_pdf_text()
        if cv_text:
            storage.set_cv_text(cv_text)
    except Exception:
        # CV is optional; never block startup on parsing issues.
        traceback.print_exc()

    # Apply the feed rule right away, then analyze whatever is still missing.
    _archive_stale(trigger="startup")
    _kick_analysis(trigger="startup")

    # Start the background scheduler that refreshes channels daily at a fixed hour.
    thread = threading.Thread(target=_scheduler_loop, daemon=True)
    thread.start()
    print(
        "[scheduler] started (daily at %02d:%02d local)"
        % (_REFRESH_HOUR, _REFRESH_MINUTE),
        flush=True,
    )


def _clean_records(
    df: pd.DataFrame, columns: list[str] | None = None
) -> list[dict[str, Any]]:
    """Turn a JobSpy DataFrame into JSON-safe records for the frontend."""
    if df is None or df.empty:
        return []

    subset = df.reindex(columns=columns or _DISPLAY_COLUMNS).copy()
    # date_posted may be datetime/date/NaT -> stringify safely.
    if "date_posted" in subset:
        subset["date_posted"] = subset["date_posted"].astype(str)

    records: list[dict[str, Any]] = []
    for row in subset.to_dict(orient="records"):
        clean: dict[str, Any] = {}
        for key, value in row.items():
            # Replace NaN/NaT/None with None so JSON stays valid.
            if value is None or (isinstance(value, float) and math.isnan(value)):
                clean[key] = None
            elif str(value) in ("NaT", "nan", "None"):
                clean[key] = None
            else:
                clean[key] = value
        # Rename compensation columns to the DB salary_* names.
        for src, dst in _SALARY_MAP.items():
            if src in clean:
                clean[dst] = clean.pop(src)
        records.append(clean)
    return records


def _raw_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Every column JobSpy returned, row by row (same order as _clean_records)."""
    if df is None or df.empty:
        return []
    return _clean_records(df, list(df.columns))


def _with_raw(df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    """Records for storage, each carrying its full JobSpy row under ``_raw``."""
    records = _clean_records(df, columns)
    for rec, raw in zip(records, _raw_records(df)):
        rec["_raw"] = raw
    return records


# --------------------------------------------------------------------------- #
# AI analysis                                                                  #
# --------------------------------------------------------------------------- #
# Every job in the DB gets analyzed. A single background worker drains the
# backlog (jobs without an analysis); refreshes just "kick" it. Each attempt,
# failed ones included, is stored in analysis_runs.

_analysis_state = threading.Lock()
_analysis_running = False
_analysis_requested = False


def _analyze_one(rec: dict[str, Any], cv_text: str, cv_version_id: int | None) -> bool:
    """Analyze one job, store the attempt, return True on success."""
    base = {
        "provider": analyzer.PROVIDER,
        "model": analyzer.MODEL,
        "prompt_version": analyzer.PROMPT_VERSION,
        "cv_version_id": cv_version_id,
    }
    try:
        out = analyzer.analyze_job(rec, cv_text)
    except Exception as exc:
        storage.add_analysis_run(
            rec["job_url"], {**base, "status": "error", "error": f"{type(exc).__name__}: {exc}"[:1000]}
        )
        return False
    storage.add_analysis_run(
        rec["job_url"],
        {
            **base,
            "status": "ok",
            "result": out["result"],
            "raw_response": out["raw"],
            "input_tokens": out["input_tokens"],
            "output_tokens": out["output_tokens"],
            "latency_ms": out["latency_ms"],
        },
    )
    storage.set_analysis(rec["job_url"], out["result"])
    return True


def _analyze_backlog(trigger: str) -> None:
    """Analyze every job still missing an analysis, logging one event per run."""
    if not analyzer.is_configured():
        return
    pending_total = storage.count_pending_analysis()
    if not pending_total:
        return
    log_id = storage.start_log({"kind": "analysis", "trigger": trigger, "found": pending_total})
    t0 = time.monotonic()
    ok = failed = 0
    try:
        cv_text = storage.get_cv_text()
        cv_version_id = storage.current_cv_version_id()
        seen: set[str] = set()
        while True:
            batch = [r for r in storage.jobs_pending_analysis(50) if r["job_url"] not in seen]
            if not batch:
                break
            seen.update(r["job_url"] for r in batch)
            with ThreadPoolExecutor(max_workers=_ANALYSIS_WORKERS) as pool:
                for success in pool.map(lambda r: _analyze_one(r, cv_text, cv_version_id), batch):
                    ok += success
                    failed += not success
    except Exception as exc:
        storage.finish_log(log_id, {
            "status": "error", "error": str(exc)[:500], "analyzed": ok,
            "analysis_failed": failed, "duration_ms": int((time.monotonic() - t0) * 1000),
        })
        raise
    storage.finish_log(log_id, {
        "status": "ok" if ok or not failed else "error",
        "error": None if ok or not failed else "Tutte le analisi sono fallite: vedi analysis_runs",
        "analyzed": ok, "analysis_failed": failed,
        "duration_ms": int((time.monotonic() - t0) * 1000),
    })


def _analysis_worker(trigger: str) -> None:
    global _analysis_running, _analysis_requested
    while True:
        with _analysis_state:
            if not _analysis_requested:
                _analysis_running = False
                return
            _analysis_requested = False
        try:
            _analyze_backlog(trigger)
        except Exception:
            traceback.print_exc()


def _kick_analysis(trigger: str = "manual") -> None:
    """Make sure the backlog gets analyzed soon, without blocking the caller."""
    global _analysis_running, _analysis_requested
    with _analysis_state:
        _analysis_requested = True
        if _analysis_running:
            return
        _analysis_running = True
    threading.Thread(target=_analysis_worker, args=(trigger,), daemon=True).start()


def _refresh_channel(channel: dict[str, Any], trigger: str = "manual") -> int:
    """Scrape a channel's site+query and persist every job and sighting.

    Returns the number of jobs new to this channel. Scraping is serialized via
    ``_scrape_lock`` so the scheduler and manual triggers don't overlap. The
    run is logged; AI analysis of the new jobs happens in the background.
    """
    log_id = storage.start_log({
        "kind": "refresh",
        "trigger": trigger,
        "channel_id": channel["id"],
        "channel_name": channel.get("name") or channel["search_term"],
        "site": channel["site"],
    })
    t0 = time.monotonic()
    try:
        with _scrape_lock:
            df = search_site(
                channel["site"],
                channel["search_term"],
                location=channel.get("location") or "",
                distance_km=channel.get("distance_km") or 25,
                results_wanted=channel.get("results_wanted") or 25,
                hours_old=channel.get("hours_old"),
                is_remote=bool(channel.get("is_remote")),
            )
        records = _with_raw(df, _FULL_COLUMNS)
        new_count = storage.upsert_channel_jobs(channel["id"], records, run_id=log_id)
    except Exception as exc:
        storage.finish_log(log_id, {
            "status": "error", "error": str(exc)[:500],
            "duration_ms": int((time.monotonic() - t0) * 1000),
        })
        raise
    storage.finish_log(log_id, {
        "status": "ok", "found": len(records), "new_count": new_count,
        "duration_ms": int((time.monotonic() - t0) * 1000),
    })
    return new_count


def _seconds_until_next_run() -> float:
    """Seconds from now until the next _REFRESH_HOUR:_REFRESH_MINUTE (local time)."""
    now = datetime.datetime.now()
    target = now.replace(
        hour=_REFRESH_HOUR, minute=_REFRESH_MINUTE, second=0, microsecond=0
    )
    if target <= now:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


def _refresh_all_channels() -> None:
    """Refresh every channel, analyze everything new, then clean the feed."""
    for channel in storage.list_channels():
        try:
            new_count = _refresh_channel(channel, trigger="scheduler")
            print(
                "[scheduler] channel %s (%s): %d new"
                % (channel["id"], channel["site"], new_count),
                flush=True,
            )
        except Exception:
            print("[scheduler] channel %s failed:" % channel.get("id"), flush=True)
            traceback.print_exc()
    _kick_analysis(trigger="scheduler")
    _archive_stale(trigger="scheduler")
    try:
        print("[scheduler] backup: %s" % storage.backup_db("daily"), flush=True)
    except Exception:
        traceback.print_exc()


def _archive_stale(days: int = _FEED_DAYS, trigger: str = "manual") -> int:
    """Archive jobs left without a verdict for ``days`` and log it."""
    t0 = time.monotonic()
    log_id = storage.start_log({"kind": "archive", "trigger": trigger})
    try:
        archived = storage.archive_stale_jobs(days)
    except Exception as exc:
        storage.finish_log(log_id, {"status": "error", "error": str(exc)[:500]})
        traceback.print_exc()
        return 0
    storage.finish_log(log_id, {
        "status": "ok", "removed": archived,
        "duration_ms": int((time.monotonic() - t0) * 1000),
    })
    print("[scheduler] archived %d jobs without a verdict after %d days" % (archived, days), flush=True)
    return archived


def _scheduler_loop() -> None:
    """Sleep until the next daily run time, refresh all channels, repeat."""
    while True:
        delay = _seconds_until_next_run()
        print(
            "[scheduler] next run in %.0f min (at %02d:%02d local)"
            % (delay / 60, _REFRESH_HOUR, _REFRESH_MINUTE),
            flush=True,
        )
        time.sleep(delay)
        try:
            _refresh_all_channels()
        except Exception:
            traceback.print_exc()


@app.post("/search")
def run_search(req: SearchRequest) -> dict[str, Any]:
    global _last_result

    try:
        if req.mode == "remote":
            df = search_remote(
                req.search_term,
                results_wanted=req.results_wanted,
                sites=req.sites,
            )
        else:
            if not req.location.strip():
                raise HTTPException(
                    status_code=422,
                    detail="Per la ricerca in Italia serve una localita (es. 'Verona, Veneto').",
                )
            df = search_italy(
                req.search_term,
                req.location,
                distance_km=req.distance_km,
                results_wanted=req.results_wanted,
                hours_old=req.hours_old,
                include_linkedin=req.include_linkedin,
                sites=req.sites,
            )
    except HTTPException:
        raise
    except Exception as exc:  # scraping failures, network, etc.
        raise HTTPException(status_code=502, detail=f"Errore durante lo scraping: {exc}") from exc

    _last_result = df if df is not None else pd.DataFrame()

    # Persist raw jobs (with description + rich columns) and analyze new ones.
    storage.upsert_jobs(_with_raw(_last_result, _FULL_COLUMNS))
    _kick_analysis()

    return {
        "count": int(len(_last_result)),
        "jobs": _clean_records(_last_result),
        "feedback": storage.get_all_feedback(),
        "analysis": storage.get_all_analysis(),
        "analyzer_configured": analyzer.is_configured(),
    }


@app.post("/feedback")
def set_feedback(req: FeedbackRequest) -> dict[str, Any]:
    storage.set_feedback(
        req.job_url,
        req.verdict,
        title=req.title,
        company=req.company,
        site=req.site,
    )
    return {"ok": True, "job_url": req.job_url, "verdict": req.verdict}


@app.get("/export")
def export(format: Literal["csv", "xlsx"] = "csv") -> StreamingResponse:
    # Prefer the last in-memory search; otherwise fall back to all stored jobs
    # so export still works after a page refresh / container restart.
    if _last_result is not None and not _last_result.empty:
        source = _last_result
    else:
        source = pd.DataFrame(storage.get_all_jobs(include_archived=True))
    if source is None or source.empty:
        raise HTTPException(status_code=404, detail="Nessun risultato da esportare: fai prima una ricerca.")

    df = source.reindex(columns=_DISPLAY_COLUMNS).copy()
    # Attach the stored verdict as a column so the export reflects likes/dislikes.
    feedback = storage.get_all_feedback()
    df["feedback"] = df["job_url"].map(feedback).fillna("")

    # Enrich with DeepSeek analysis (tags / summary / relevance score).
    analysis = storage.get_all_analysis()
    df["relevance_score"] = df["job_url"].map(
        lambda u: analysis.get(u, {}).get("relevance_score")
    )
    df["tags"] = df["job_url"].map(
        lambda u: ", ".join(analysis.get(u, {}).get("tags", []))
    )
    df["summary"] = df["job_url"].map(
        lambda u: analysis.get(u, {}).get("summary", "")
    )

    if format == "csv":
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        data = buffer.getvalue().encode("utf-8")
        media = "text/csv"
        filename = "jobs.csv"
    else:
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="jobs")
        data = bio.getvalue()
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "jobs.xlsx"

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _jobs_envelope(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Jobs plus the feedback/analysis of those jobs only (not the whole DB,
    which made per-channel responses huge for MCP clients)."""
    urls: set[str] = set()
    for j in jobs:
        urls.add(j["job_url"])
        urls.update(j.get("duplicate_urls") or [])
    feedback = storage.get_all_feedback()
    analysis = storage.get_all_analysis()
    return {
        "count": len(jobs),
        "jobs": jobs,
        "feedback": {u: v for u, v in feedback.items() if u in urls},
        "analysis": {u: v for u, v in analysis.items() if u in urls},
        "analyzer_configured": analyzer.is_configured(),
    }


@app.get("/jobs")
def list_jobs() -> dict[str, Any]:
    """
    Return all previously stored jobs (with feedback + analysis) without
    scraping. Used to repopulate the UI on page load / refresh so we don't
    re-run the scrape and AI analysis every time.
    """
    return _jobs_envelope(storage.get_all_jobs())


@app.get("/channels")
def get_channels() -> dict[str, Any]:
    """List all channels with their per-channel job counts."""
    return {"channels": storage.list_channels(), "sites": _ALL_SITES}


@app.post("/channels")
def create_channel(req: ChannelRequest) -> dict[str, Any]:
    """Create a channel and do an immediate first refresh."""
    site = req.site.strip().lower()
    if site not in _ALL_SITES:
        raise HTTPException(status_code=422, detail=f"Sito non supportato: {site}")

    channel_id = storage.create_channel(
        site=site,
        search_term=req.search_term,
        name=req.name,
        location=req.location,
        distance_km=req.distance_km,
        results_wanted=req.results_wanted,
        hours_old=req.hours_old,
        is_remote=req.is_remote,
    )
    channel = storage.get_channel(channel_id)
    try:
        new_count = _refresh_channel(channel, trigger="create") if channel else 0
        _kick_analysis(trigger="create")
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Canale creato ma scraping fallito: {exc}"
        ) from exc

    return {
        "channel": storage.get_channel(channel_id),
        "new_count": new_count,
    }


@app.delete("/channels/{channel_id}")
def remove_channel(channel_id: int) -> dict[str, Any]:
    if storage.get_channel(channel_id) is None:
        raise HTTPException(status_code=404, detail="Canale non trovato.")
    storage.delete_channel(channel_id)
    return {"ok": True, "id": channel_id}


@app.post("/channels/{channel_id}/refresh")
def refresh_channel(channel_id: int) -> dict[str, Any]:
    channel = storage.get_channel(channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Canale non trovato.")
    try:
        new_count = _refresh_channel(channel)
        _kick_analysis()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Errore durante lo scraping: {exc}") from exc
    return {"ok": True, "id": channel_id, "new_count": new_count}


@app.get("/channels/{channel_id}/jobs")
def channel_jobs(channel_id: int) -> dict[str, Any]:
    if storage.get_channel(channel_id) is None:
        raise HTTPException(status_code=404, detail="Canale non trovato.")
    return _jobs_envelope(storage.get_channel_jobs(channel_id))


@app.get("/job")
def get_job(url: str) -> dict[str, Any]:
    """Return a single job with ALL stored fields + analysis + feedback (detail page)."""
    job = storage.get_job(url)
    if job is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato.")
    analysis = storage.get_all_analysis().get(url)
    feedback = storage.get_all_feedback().get(url)
    return {"job": job, "analysis": analysis, "feedback": feedback}


@app.get("/status")
def status() -> dict[str, Any]:
    """Report AI analysis state (key, CV, backlog) and the feed rule."""
    cv_text = storage.get_cv_text()
    return {
        "analyzer_configured": analyzer.is_configured(),
        "cv_loaded": bool(cv_text),
        "cv_chars": len(cv_text),
        "analysis_pending": storage.count_pending_analysis(),
        "analysis_running": _analysis_running,
        "feed_days": _FEED_DAYS,
    }


@app.get("/analytics")
def analytics() -> dict[str, Any]:
    """Aggregated KPIs + market-intelligence breakdowns over the stored data."""
    return storage.analytics_summary()


@app.post("/maintenance/recency")
def set_recency(hours: int = _RECENCY_DAYS * 24) -> dict[str, Any]:
    """Set the recency window (hours_old) on every channel."""
    changed = storage.set_hours_old_all(hours)
    return {"ok": True, "channels_updated": changed, "hours_old": hours}


@app.post("/maintenance/archive")
def archive(days: int = _FEED_DAYS) -> dict[str, Any]:
    """Archive jobs left without a verdict for N days (nothing is deleted)."""
    archived = _archive_stale(days)
    return {"ok": True, "archived": archived, "days": days}


@app.post("/maintenance/analyze")
def analyze_backlog() -> dict[str, Any]:
    """Start analyzing every job that has no AI analysis yet (background)."""
    _kick_analysis()
    return {"ok": True, "pending": storage.count_pending_analysis()}


@app.get("/logs")
def logs(limit: int = 200) -> dict[str, Any]:
    """Recent update events (channel refreshes, purges), newest first."""
    return {"logs": storage.list_logs(max(1, min(limit, 1000)))}


# Serve the SPA. Mounted last so API routes take precedence.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
