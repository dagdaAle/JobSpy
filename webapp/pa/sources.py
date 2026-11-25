"""
Sources of the Concorsi PA area: inPA and the Gazzetta Ufficiale 4th special series.

Both return area items (dicts with the ``area_common.ITEM_FIELDS`` keys plus
``key``), not ``JobPost``: these notices have an issuing body and a deadline,
not a company and a salary.
"""

from __future__ import annotations

import datetime
import html
import re
import time
from typing import Any

import requests
from area_common import SourceError, http_session
from bs4 import BeautifulSoup

from jobspy.inpa import InPA

SOURCES = ("inpa", "gazzetta")

INPA_API = InPA.api_url
INPA_DETAIL = InPA.detail_url
GU_BASE = "https://www.gazzettaufficiale.it"
GU_INDEX = GU_BASE + "/30giorni/concorsi"
_PAGE_PAUSE_S = 1.0  # ADR 004: be gentle with public sites
_MAX_INPA_PAGES = 20

_MONTHS = {
    m: i for i, m in enumerate(
        ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
         "settembre", "ottobre", "novembre", "dicembre"), start=1)
}
_SCAD = re.compile(r"scad\.\s*(\d{1,2})\s+([a-zà]+)\s+(\d{4})", re.I)
_CODE = re.compile(r"\((\d{2}[A-Z]\d{5})\)\s*$")
_ISSUE = re.compile(r"/gazzetta/concorsi/caricaDettaglio\?dataPubblicazioneGazzetta=(\d{4}-\d{2}-\d{2})"
                    r"&numeroGazzetta=(\d+)")


def _iso_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _words(text: str) -> str:
    return " ".join(html.unescape(text or "").split())


def _matches(query: str, *texts: str) -> bool:
    """Every word of the query appears in the texts (case-insensitive, prefix match: 'informatic')."""
    terms = [t for t in (query or "").lower().split() if t not in ("*", "tutti", "tutto")]
    hay = " ".join(texts).lower()
    return all(re.search(rf"(?<!\w){re.escape(t)}", hay) for t in terms)


# ---------------------------------------------------------------------- inPA
def inpa_item(notice: dict[str, Any]) -> dict[str, Any] | None:
    title = _words(notice.get("titolo") or "")
    if not title or not notice.get("id"):
        return None
    figure = _words(notice.get("figuraRicercata") or "")
    if figure and figure.lower() not in title.lower():
        title = f"{title} – {figure}"
    enti = notice.get("entiRiferimento") or []
    sedi = notice.get("sedi") or []
    body = BeautifulSoup(notice.get("descrizione") or notice.get("descrizioneBreve") or "", "html.parser")
    return {
        "key": f"inpa-{notice['id']}",
        "source": "inpa",
        "title": title,
        "body": (f"Posti: {notice['numPosti']}\n" if notice.get("numPosti") else "")
        + body.get_text(" ", strip=True)[:8000] or None,
        "buyer": enti[0] if enti else None,
        "kind": notice.get("tipoProcedura") or ", ".join(notice.get("categorie") or []) or None,
        "place": ", ".join(sedi) or None,
        "deadline": _iso_date(notice.get("dataScadenza")),
        "published_at": _iso_date(notice.get("dataPubblicazione")),
        "url": INPA_DETAIL.format(id=notice["id"]),
        "amount": None, "currency": None, "cpv": None, "raw_json": None,
    }


def fetch_inpa(channel: dict[str, Any], session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Open inPA notices matching the channel's query, filtered by place like the Lavoro inPA source."""
    session = session or http_session()
    term = (channel.get("query") or "").strip()
    body = {"text": "" if term.lower() in ("*", "tutti", "tutto") else term, "status": ["OPEN"]}
    wanted = channel.get("results_wanted") or 50
    items: list[dict[str, Any]] = []
    for page in range(_MAX_INPA_PAGES):
        try:
            response = session.post(
                INPA_API, params={"page": page, "size": 50}, json=body,
                headers={"Accept": "application/json"}, timeout=30,
            )
        except requests.RequestException as exc:
            raise SourceError(f"inPA: request failed - {exc}") from exc
        if response.status_code != 200:
            raise SourceError(f"inPA: HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise SourceError("inPA: invalid JSON") from exc
        notices = data.get("content") or []
        for notice in notices:
            if not InPA._in_area(notice, channel.get("location")):
                continue
            item = inpa_item(notice)
            if item:
                items.append(item)
        if len(items) >= wanted or data.get("last", True) or not notices:
            break
        time.sleep(_PAGE_PAUSE_S)
    return items[:wanted]


# ------------------------------------------------------------------ Gazzetta
def _gu_date(text: str) -> str | None:
    m = _SCAD.search(text)
    if not m or m.group(2).lower() not in _MONTHS:
        return None
    try:
        return datetime.date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
    except ValueError:
        return None


def gu_issues(index_html: str) -> list[tuple[str, str]]:
    """(publication date, issue number) of the issues in the 30-day index, newest first."""
    seen: dict[tuple[str, str], None] = {}
    for m in _ISSUE.finditer(index_html):
        seen[(m.group(1), m.group(2))] = None
    if not seen:
        raise SourceError("Gazzetta: no issue found in the 30-day index (page changed?)")
    return sorted(seen, reverse=True)


def gu_acts(issue_html: str, published_at: str) -> list[dict[str, Any]]:
    """One item per act of an issue, with the issuing body and section it is listed under."""
    soup = BeautifulSoup(issue_html, "html.parser")
    section = body = ""
    items: list[dict[str, Any]] = []
    for el in soup.select("span.rubrica, span.emettitore, span.risultato"):
        classes = el.get("class") or []
        if "rubrica" in classes:
            section = _words(el.get_text())
            continue
        if "emettitore" in classes:
            body = _words(el.get_text())
            continue
        links = el.find_all("a", href=True)
        if len(links) < 2:
            continue
        head = _words(links[0].get_text(" "))
        for span in links[1].select("span"):
            span.decompose()
        text = _words(links[1].get_text(" "))
        code = _CODE.search(text)
        if not code:
            continue
        title = _CODE.sub("", text).strip()
        items.append({
            "key": f"gu-{code.group(1)}",
            "source": "gazzetta",
            "title": title,
            "body": None,
            "buyer": body.title() if body.isupper() else body or None,
            "kind": _SCAD.sub("", head).strip(" ()").capitalize() or None,
            "place": section.title() or None,
            "deadline": _gu_date(head),
            "published_at": published_at,
            "url": GU_BASE + links[1]["href"],
            "amount": None, "currency": None, "cpv": None, "raw_json": None,
        })
    return items


def _gu_get(session: requests.Session, url: str) -> str:
    try:
        response = session.get(url, timeout=30)
    except requests.RequestException as exc:
        raise SourceError(f"Gazzetta: request failed - {exc}") from exc
    # The site answers 200 with a "Pagina non trovata" page for wrong URLs.
    if response.status_code != 200 or "Pagina non trovata" in response.text[:3000]:
        raise SourceError(f"Gazzetta: HTTP {response.status_code} on {url}")
    return response.text


def fetch_gazzetta(channel: dict[str, Any], session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Acts of the last 30 days whose title or issuing body matches the channel's query and place."""
    session = session or http_session()
    wanted = channel.get("results_wanted") or 50
    query = channel.get("query") or ""
    place = (channel.get("location") or "").split(",")[0].strip()
    items: list[dict[str, Any]] = []
    for date, number in gu_issues(_gu_get(session, GU_INDEX)):
        time.sleep(_PAGE_PAUSE_S)
        page = _gu_get(session, f"{GU_BASE}/gazzetta/concorsi/caricaDettaglio/home"
                                f"?dataPubblicazioneGazzetta={date}&numeroGazzetta={number}")
        for item in gu_acts(page, date):
            text = (item["title"], item["buyer"] or "")
            # shortcut: the place is matched on title and body name only (GU has no structured
            # place); central administrations count everywhere. Upgrade if local bodies are missed.
            central = "centrali" in (item["place"] or "").lower()
            if _matches(query, *text) and (not place or central or _matches(place, *text)):
                items.append(item)
        if len(items) >= wanted:
            break
    return items[:wanted]


FETCHERS = {"inpa": fetch_inpa, "gazzetta": fetch_gazzetta}
