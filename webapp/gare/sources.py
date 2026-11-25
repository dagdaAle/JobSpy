"""
TED (Tenders Electronic Daily), the EU public procurement journal: public,
keyless v3 search API. Only above-threshold tenders are published there.
"""

from __future__ import annotations

import datetime
import json
import re
import time
from typing import Any

import requests
from area_common import SourceError, http_session

SOURCES = ("ted",)
SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
NOTICE_URL = "https://ted.europa.eu/it/notice/-/detail/{number}"
PAGE_SIZE = 100
_MAX_PAGES = 5
_PAGE_PAUSE_S = 1.0
_LANGS = ("ita", "eng")
CALL_TYPES = ("cn-standard", "cn-social", "cn-desg")
FIELDS = [
    "notice-title", "title-proc", "description-proc", "buyer-name", "publication-date",
    "deadline-receipt-tender-date-lot", "deadline-receipt-request-date-lot", "estimated-value-lot", "estimated-value-cur-lot",
    "place-of-performance-city-lot", "classification-cpv", "notice-type",
]


def build_query(channel: dict[str, Any], today: datetime.date | None = None) -> str:
    """TED expert query for a channel: country, CPV codes (any, children included), text, recency."""
    parts = [f"buyer-country={channel.get('country') or 'ITA'}"]
    cpv = [c for c in re.split(r"[,\s]+", channel.get("cpv") or "") if c]
    if cpv:
        parts.append("(" + " OR ".join(f"classification-cpv={c}" for c in cpv) + ")")
    text = (channel.get("query") or "").replace('"', " ").strip()
    if text:
        parts.append(f'FT~"{text}"')
    since = (today or datetime.date.today()) - datetime.timedelta(days=channel.get("days") or 14)
    parts.append(f"PD>={since:%Y%m%d}")
    # ACTIVE alone also returns award notices (can-*): only calls for tenders are still open.
    parts.append(f"notice-type IN ({' '.join(CALL_TYPES)})")
    return " AND ".join(parts) + " SORT BY publication-date DESC"


def _text(value: Any) -> str | None:
    """A multilingual field: Italian first, then English, then any language."""
    if isinstance(value, dict):
        for lang in (*_LANGS, *value):
            if value.get(lang):
                v = value[lang]
                return " ".join(v) if isinstance(v, list) else str(v)
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or None
    return str(value) if value else None


def _date(value: str | None) -> str | None:
    return value[:10] if value and re.match(r"\d{4}-\d{2}-\d{2}", value) else None


def ted_item(notice: dict[str, Any]) -> dict[str, Any] | None:
    number = notice.get("publication-number")
    title = _text(notice.get("title-proc")) or _text(notice.get("notice-title"))
    if not number or not title:
        return None
    amounts = [float(a) for a in notice.get("estimated-value-lot") or [] if re.fullmatch(r"[\d.]+", str(a))]
    # Restricted procedures have a deadline to ask to take part instead of one for tenders.
    raw_deadlines = notice.get("deadline-receipt-tender-date-lot") or notice.get("deadline-receipt-request-date-lot")
    deadlines = sorted(d for d in (_date(x) for x in raw_deadlines or []) if d)
    places = list(dict.fromkeys(notice.get("place-of-performance-city-lot") or []))
    cpvs = list(dict.fromkeys(notice.get("classification-cpv") or []))
    currency = list(dict.fromkeys(notice.get("estimated-value-cur-lot") or []))
    return {
        "key": f"ted-{number}",
        "source": "ted",
        "title": title,
        "body": _text(notice.get("description-proc")),
        "buyer": _text(notice.get("buyer-name")),
        "kind": notice.get("notice-type"),
        "place": ", ".join(places) or None,
        # Multi-lot tenders: the nearest deadline and the sum of the lots.
        "deadline": deadlines[0] if deadlines else None,
        "published_at": _date(notice.get("publication-date")),
        "url": NOTICE_URL.format(number=number),
        "amount": sum(amounts) if amounts else None,
        "currency": currency[0] if len(currency) == 1 else None,
        "cpv": ",".join(cpvs) or None,
        "raw_json": json.dumps(notice, ensure_ascii=False)[:20000],
    }


def fetch_ted(channel: dict[str, Any], session: requests.Session | None = None) -> list[dict[str, Any]]:
    session = session or http_session()
    wanted = channel.get("results_wanted") or 50
    query = build_query(channel)
    items: list[dict[str, Any]] = []
    for page in range(1, _MAX_PAGES + 1):
        try:
            response = session.post(SEARCH_URL, json={
                "query": query, "fields": FIELDS, "limit": min(PAGE_SIZE, wanted),
                "page": page, "scope": "ACTIVE",
            }, timeout=60)
        except requests.RequestException as exc:
            raise SourceError(f"TED: request failed - {exc}") from exc
        if response.status_code != 200:
            raise SourceError(f"TED: HTTP {response.status_code} - {response.text[:200]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise SourceError("TED: invalid JSON") from exc
        if data.get("timedOut"):
            raise SourceError("TED: search timed out")
        notices = data.get("notices") or []
        items.extend(i for i in (ted_item(n) for n in notices) if i)
        if len(items) >= wanted or len(notices) < min(PAGE_SIZE, wanted):
            break
        time.sleep(_PAGE_PAUSE_S)
    return items[:wanted]


def within_budget(item: dict[str, Any], channel: dict[str, Any]) -> bool:
    """A tender above the channel's maximum amount is dropped; one without an amount stays."""
    limit = channel.get("max_amount")
    return not limit or item.get("amount") is None or item["amount"] <= limit


FETCHERS = {"ted": fetch_ted}
