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

# Cap analyses per search to bound API cost/latency (overridable via env).
_MAX_ANALYSIS = int(os.environ.get("MAX_ANALYSIS_PER_SEARCH", "30"))

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
_ALL_SITES = ITALY_LOCAL_SITES + REMOTE_ONLY_SITES


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
    # Extract CV text from the mounted PDF once, if we don't have it yet.
    try:
        if not storage.get_cv_text():
            cv_text = analyzer.extract_pdf_text()
            if cv_text:
                storage.set_cv_text(cv_text)
    except Exception:
        # CV is optional; never block startup on parsing issues.
        pass

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


def _analyze_new_jobs(records: list[dict[str, Any]]) -> None:
    """
    Analyze jobs that don't yet have a stored analysis, via DeepSeek.

    Runs in a small thread pool (network-bound). Skips silently if the
    analyzer isn't configured (no API key). Individual failures are ignored
    so a bad job doesn't sink the whole search.
    """
    if not analyzer.is_configured():
        return

    cv_text = storage.get_cv_text()
    already = storage.get_analyzed_urls()
    pending = [
        r for r in records if r.get("job_url") and r["job_url"] not in already
    ][:_MAX_ANALYSIS]
    if not pending:
        return

    def _work(rec: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        try:
            result = analyzer.analyze_job(rec, cv_text)
            return rec["job_url"], result
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_work, r) for r in pending]
        for fut in as_completed(futures):
            out = fut.result()
            if out is not None:
                url, result = out
                storage.set_analysis(url, result)


def _refresh_channel(channel: dict[str, Any]) -> int:
    """Scrape a channel's site+query, persist jobs, analyze the new ones.

    Returns the number of jobs new to this channel. Scraping is serialized via
    ``_scrape_lock`` so the scheduler and manual triggers don't overlap.
    """
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

    records = _clean_records(df, _FULL_COLUMNS)
    new_count = storage.upsert_channel_jobs(channel["id"], records)

    # Only analyze jobs that are new for this channel (bounds cost).
    new_urls = {
        r["job_url"]
        for r in records
        if r.get("job_url")
    }
    # _analyze_new_jobs already skips already-analyzed urls, so pass all records
    # belonging to this channel; the analyzer cache prevents re-paying.
    _analyze_new_jobs(records)
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
    """Refresh every channel once, logging per-channel results."""
    channels = storage.list_channels()
    for channel in channels:
        try:
            new_count = _refresh_channel(channel)
            print(
                "[scheduler] channel %s (%s): %d new"
                % (channel["id"], channel["site"], new_count),
                flush=True,
            )
        except Exception:
            print("[scheduler] channel %s failed:" % channel.get("id"), flush=True)
            traceback.print_exc()


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
    analysis_records = _clean_records(_last_result, _FULL_COLUMNS)
    storage.upsert_jobs(analysis_records)
    _analyze_new_jobs(analysis_records)

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
        source = pd.DataFrame(storage.get_all_jobs())
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


@app.get("/jobs")
def list_jobs() -> dict[str, Any]:
    """
    Return all previously stored jobs (with feedback + analysis) without
    scraping. Used to repopulate the UI on page load / refresh so we don't
    re-run the scrape and AI analysis every time.
    """
    jobs = storage.get_all_jobs()
    return {
        "count": len(jobs),
        "jobs": jobs,
        "feedback": storage.get_all_feedback(),
        "analysis": storage.get_all_analysis(),
        "analyzer_configured": analyzer.is_configured(),
    }


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
        new_count = _refresh_channel(channel) if channel else 0
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
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Errore durante lo scraping: {exc}") from exc
    return {"ok": True, "id": channel_id, "new_count": new_count}


@app.get("/channels/{channel_id}/jobs")
def channel_jobs(channel_id: int) -> dict[str, Any]:
    if storage.get_channel(channel_id) is None:
        raise HTTPException(status_code=404, detail="Canale non trovato.")
    jobs = storage.get_channel_jobs(channel_id)
    return {
        "count": len(jobs),
        "jobs": jobs,
        "feedback": storage.get_all_feedback(),
        "analysis": storage.get_all_analysis(),
        "analyzer_configured": analyzer.is_configured(),
    }


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
    """Report whether AI analysis is available and if a CV is loaded."""
    cv_text = storage.get_cv_text()
    return {
        "analyzer_configured": analyzer.is_configured(),
        "cv_loaded": bool(cv_text),
        "cv_chars": len(cv_text),
        "max_analysis_per_search": _MAX_ANALYSIS,
    }


@app.get("/analytics")
def analytics() -> dict[str, Any]:
    """Aggregated KPIs + market-intelligence breakdowns over the stored data."""
    return storage.analytics_summary()


# Serve the SPA. Mounted last so API routes take precedence.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
