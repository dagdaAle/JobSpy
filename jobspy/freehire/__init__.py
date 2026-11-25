"""
freehire (https://freehire.me): a public, keyless JSON catalogue of job postings
collected from company applicant-tracking systems (Workday, Greenhouse, Lever…),
aggregators and LinkedIn.

The API answers 200 even when it does not understand a filter: it lists the
unknown parameter in ``meta.ignored_params`` (or an unknown value in
``meta.ignored_values``) and returns the unfiltered catalogue or nothing. Both
are treated as errors here, never as results.

Besides the ``Freehire`` scraper used by :func:`jobspy.scrape_jobs`, this module
exposes the client and the mapping helpers so the webapp can search without a
channel, follow a company and check whether a posting closed at the source.
"""

from __future__ import annotations

import math
import re
import time
from datetime import date
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
import requests

from jobspy.common import description_text, with_retry
from jobspy.model import (
    CompensationInterval,
    DescriptionFormat,
    JobPost,
    Location,
    Scraper,
    ScraperInput,
)

BASE_URL = "https://freehire.me/api/v1"
USER_AGENT = "JobSpy-fork/1.0 (+https://github.com/dagdaAle/JobSpy)"
PAGE_SIZE = 100
_PAGE_PAUSE_S = 0.25
# A posting copied this many times across boards is treated as a mass posting.
MASS_POSTING_THRESHOLD = 5
_MAX_LOCATION_CHARS = 100

_COUNTRY_WORDS = {"italia": "it", "italy": "it"}
_REGION_WORDS = {"europa": "eu", "europe": "eu", "eu": "eu"}
_PERIODS = {
    "year": CompensationInterval.YEARLY,
    "month": CompensationInterval.MONTHLY,
    "week": CompensationInterval.WEEKLY,
    "day": CompensationInterval.DAILY,
    "hour": CompensationInterval.HOURLY,
}
_PRIORITY_LABEL = {"required": "obbligatorio", "preferred": "preferito"}
REQUIREMENTS_HEADING = "Requisiti (dalla fonte)"


class FreehireError(Exception):
    """freehire refused the request, failed, or ignored a filter."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class FreehireClient:
    """Thin client over the public API (no key, 300 requests per minute)."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or with_retry(requests.Session())
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json"}
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self.session.get(f"{BASE_URL}{path}", params=params, timeout=30)
        except requests.RequestException as exc:
            raise FreehireError(f"freehire: request failed - {exc}") from exc
        if response.status_code != 200:
            raise FreehireError(
                f"freehire: HTTP {response.status_code} on {path}",
                status=response.status_code,
            )
        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise FreehireError(f"freehire: invalid JSON on {path}") from exc
        meta = data.get("meta") or {}
        if meta.get("ignored_params") or meta.get("ignored_values"):
            ignored = meta.get("ignored_params") or meta.get("ignored_values")
            raise FreehireError(f"freehire ignored a filter: {ignored}")
        return data

    def search(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._get("/jobs/search", params)

    def job(self, slug: str) -> dict[str, Any]:
        data: dict[str, Any] = self._get(f"/jobs/{slug}")["data"]
        return data

    def companies(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = self._get(
            "/companies", {"q": query, "limit": limit}
        ).get("data", [])
        return data

    def company(self, slug: str) -> dict[str, Any]:
        data: dict[str, Any] = self._get(f"/companies/{slug}")["data"]
        return data


def location_filter(location: str | None) -> dict[str, str]:
    """Translate a channel location into freehire filters (no radius support)."""
    text = " ".join((location or "").split()).strip(" ,").lower()
    if not text:
        return {}
    if text in _COUNTRY_WORDS:
        return {"countries": _COUNTRY_WORDS[text]}
    if text in _REGION_WORDS:
        return {"regions": _REGION_WORDS[text]}
    # "Verona, Veneto, Italia" -> the city; freehire rejects unknown cities
    # through ignored_values, which the client turns into an error.
    return {"cities": text.split(",")[0].strip()}


def normalize_url(
    url: str | None, origin: str | None = None, external_id: str | None = None
) -> str | None:
    """The posting's own URL, matching what JobSpy's scrapers store."""
    if origin == "linkedin" and external_id and str(external_id).isdigit():
        return f"https://www.linkedin.com/jobs/view/{external_id}"
    if not url:
        return None
    parts = urlsplit(url)
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.startswith("utm_")
    ]
    path = parts.path.rstrip("/") or parts.path
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), ""))


def is_suspect(raw: dict[str, Any]) -> bool:
    reality = raw.get("reality") or {}
    return bool(reality.get("fake_freshness")) or (
        (reality.get("mass_posting_count") or 0) >= MASS_POSTING_THRESHOLD
    )


def _requirements(raw: dict[str, Any]) -> list[dict[str, str]]:
    items = (raw.get("enrichment") or {}).get("requirements") or []
    return [
        {
            "text": str(r.get("text")).strip(),
            "priority": r.get("priority") or "required",
        }
        for r in items
        if isinstance(r, dict) and r.get("text")
    ]


def _description(raw: dict[str, Any], fmt: DescriptionFormat) -> str | None:
    text = description_text(raw.get("description"), fmt) or ""
    reqs = _requirements(raw)
    if reqs:
        lines = [
            f"- [{_PRIORITY_LABEL.get(r['priority'], r['priority'])}] {r['text']}"
            for r in reqs
        ]
        text = f"{text.rstrip()}\n\n## {REQUIREMENTS_HEADING}\n" + "\n".join(lines)
    return text.strip() or None


def _location(raw: dict[str, Any]) -> Location | None:
    text = re.sub(r"^[\s,]+|[\s,]+$", "", raw.get("location") or "")
    if not text:
        return None
    if len(text) > _MAX_LOCATION_CHARS:
        text = text[: _MAX_LOCATION_CHARS - 1].rstrip(", ") + "…"
    return Location(city=text)


def to_post(
    raw: dict[str, Any], fmt: DescriptionFormat = DescriptionFormat.MARKDOWN
) -> JobPost | None:
    """Map one freehire posting to a JobPost (None when unusable)."""
    origin = raw.get("source")
    job_url = normalize_url(raw.get("url"), origin, raw.get("external_id"))
    title = raw.get("title")
    if not job_url or not title:
        return None
    enrichment = raw.get("enrichment") or {}
    stamp = (raw.get("posted_at") or raw.get("created_at") or "")[:10]
    posted = date.fromisoformat(stamp) if stamp else None
    return JobPost(
        id=f"freehire-{raw.get('public_slug')}",
        title=title,
        company=raw.get("company"),
        location=_location(raw),
        job_url=job_url,
        description=_description(raw, fmt),
        date_posted=posted,
        is_remote=raw.get("work_mode") == "remote",
        min_amount=enrichment.get("salary_min"),
        max_amount=enrichment.get("salary_max"),
        currency=enrichment.get("salary_currency"),
        interval=_PERIODS.get(enrichment.get("salary_period") or ""),
        skills=[str(s) for s in raw.get("skills") or []] or None,
    )


def to_source_row(raw: dict[str, Any], job_url: str) -> dict[str, Any]:
    """The freehire-only data kept in ``job_sources`` (never overwritten by other scrapers)."""
    enrichment = raw.get("enrichment") or {}
    return {
        "job_url": job_url,
        "source": "freehire",
        "slug": raw.get("public_slug"),
        "origin": raw.get("source"),
        "salary_min": enrichment.get("salary_min"),
        "salary_max": enrichment.get("salary_max"),
        "salary_currency": enrichment.get("salary_currency"),
        "salary_interval": (
            _PERIODS.get(enrichment.get("salary_period") or "")
            or CompensationInterval.YEARLY
        ).value
        if enrichment.get("salary_min") or enrichment.get("salary_max")
        else None,
        "skills": [str(s) for s in raw.get("skills") or []],
        "requirements": _requirements(raw),
        "category": enrichment.get("category"),
        "posting_language": enrichment.get("posting_language"),
        "suspect": is_suspect(raw),
        "reality": raw.get("reality") or {},
        "closed_at": raw.get("closed_at"),
    }


def search_params(
    search_term: str | None = None,
    location: str | None = None,
    is_remote: bool = False,
    hours_old: int | None = None,
    company_slug: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if company_slug:
        params["company_slug"] = company_slug
    elif search_term:
        params["q"] = search_term
    params.update(location_filter(location))
    if is_remote:
        params["work_mode"] = "remote"
    if hours_old:
        params["posted_within_days"] = max(1, math.ceil(hours_old / 24))
    return params


def location_match(location: str | None) -> re.Pattern[str] | None:
    """freehire's city filter is fuzzy (Verona also brings Verona, WI and Rieti):
    a pattern the posting location must match, None when no city is given."""
    parts = [p.strip() for p in " ".join((location or "").split()).lower().split(",")]
    if not parts[0] or set(location_filter(location)) != {"cities"}:
        return None
    city = rf"(?<!\w){re.escape(parts[0])}(?!\w)"
    if not any(p in _COUNTRY_WORDS for p in parts[1:]):
        return re.compile(city, re.I)
    # shortcut: only Italy is known as a country, add more to _COUNTRY_WORDS when needed
    return re.compile(rf"{city}.*(?<!\w)(italy|italia|it)(?!\w)|^\s*{city}\s*$", re.I)


def fetch_postings(
    client: FreehireClient,
    params: dict[str, Any],
    results_wanted: int,
    location: str | None = None,
) -> list[dict[str, Any]]:
    """Open postings matching ``params`` (and ``location``, see
    :func:`location_match`), paging until ``results_wanted``."""
    match = location_match(location)
    found: list[dict[str, Any]] = []
    offset = 0
    while len(found) < results_wanted:
        limit = min(PAGE_SIZE, results_wanted - len(found))
        page = client.search({**params, "limit": limit, "offset": offset})
        items = page.get("data") or []
        found.extend(
            item
            for item in items
            if not item.get("closed_at")
            and (match is None or match.search(item.get("location") or ""))
        )
        total = (page.get("meta") or {}).get("total") or 0
        offset += len(items)
        if len(items) < limit or offset >= total:
            break
        time.sleep(_PAGE_PAUSE_S)
    return found[:results_wanted]


def check_city(client: FreehireClient, params: dict[str, Any]) -> None:
    """freehire answers 0 results, not an error, for a city it does not know:
    after an empty search, ask whether the city has any posting at all."""
    city = params.get("cities")
    if city and not (client.search({"cities": city, "limit": 1}).get("meta") or {}).get(
        "total"
    ):
        raise FreehireError(
            f"freehire does not know the city '{city}' (use Italia, Europa or a known city)"
        )


def _rows(
    postings: list[dict[str, Any]], fmt: DescriptionFormat
) -> tuple[list[JobPost], list[dict[str, Any]]]:
    posts, sources = [], []
    for raw in postings:
        post = to_post(raw, fmt)
        if post is None:
            continue
        posts.append(post)
        sources.append(to_source_row(raw, post.job_url))
    return posts, sources


class Freehire(Scraper):
    """Keyword search on freehire for :func:`jobspy.scrape_jobs`."""

    def __init__(self, client: FreehireClient | None = None) -> None:
        super().__init__()
        self.client = client
        self.source_rows: list[dict[str, Any]] = []

    def scrape(self, scraper_input: ScraperInput) -> list[JobPost]:
        client = self.client or FreehireClient()
        params = search_params(
            scraper_input.search_term,
            scraper_input.location,
            scraper_input.is_remote,
            scraper_input.hours_old,
        )
        try:
            postings = fetch_postings(
                client,
                params,
                scraper_input.results_wanted or 15,
                scraper_input.location,
            )
            if not postings:
                check_city(client, params)
        except FreehireError as exc:
            self.fail(str(exc))
            return []
        posts, self.source_rows = _rows(postings, scraper_input.description_format)
        return posts


def scrape_freehire(
    search_term: str = "",
    *,
    location: str = "",
    is_remote: bool = False,
    hours_old: int | None = None,
    results_wanted: int = 25,
    company_slug: str = "",
    client: FreehireClient | None = None,
) -> pd.DataFrame:
    """Same DataFrame shape as :func:`jobspy.scrape_jobs`, plus
    ``attrs["source_rows"]`` with the freehire-only data of each row.

    Rows freehire took from LinkedIn get ``site="linkedin"``: they share the
    LinkedIn scraper's URL, so the stored job does not flip site on every refresh.
    """
    client = client or FreehireClient()
    errors: dict[str, str] = {}
    sources: list[dict[str, Any]] = []
    posts: list[JobPost] = []
    try:
        params = search_params(
            search_term, location, is_remote, hours_old, company_slug
        )
        postings = fetch_postings(client, params, results_wanted, location)
        if company_slug and not postings:
            client.company(company_slug)  # 404 -> FreehireError: the company is gone
        if not postings:
            check_city(client, params)
        posts, sources = _rows(postings, DescriptionFormat.MARKDOWN)
    except FreehireError as exc:
        errors["freehire"] = str(exc)
    origin = {row["job_url"]: row["origin"] for row in sources}
    rows = [
        p.model_copy(
            update={
                "site": "linkedin"
                if origin.get(p.job_url) == "linkedin"
                else "freehire"
            }
        )
        for p in posts
    ]
    df = pd.DataFrame(
        [p.model_dump() for p in rows], columns=list(JobPost.model_fields)
    )
    df.attrs = {"errors": errors, "warnings": {}, "source_rows": sources}
    return df
