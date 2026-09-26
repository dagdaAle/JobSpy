from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime

from jobspy.model import (
    Compensation,
    CompensationInterval,
    JobPost,
    JobResponse,
    Location,
    Scraper,
    ScraperInput,
    Site,
)
from jobspy.util import create_logger, create_session

log = create_logger("Subito")

# Province (lowercase, as typed by the user) -> Subito region slug. Subito's
# search URL needs both: /annunci-{region}/vendita/offerte-lavoro/{province}/.
# Unknown places fall back to a nationwide search.
_PROVINCE_REGION = {
    # Veneto
    "verona": "veneto", "vicenza": "veneto", "padova": "veneto", "venezia": "veneto",
    "treviso": "veneto", "rovigo": "veneto", "belluno": "veneto",
    # Lombardia
    "milano": "lombardia", "brescia": "lombardia", "mantova": "lombardia",
    "bergamo": "lombardia", "cremona": "lombardia",
    # Trentino-Alto Adige
    "trento": "trentino-alto-adige", "bolzano": "trentino-alto-adige",
    # Emilia-Romagna
    "bologna": "emilia-romagna", "modena": "emilia-romagna", "ferrara": "emilia-romagna",
}

_CONTRACT = {
    "tind": "Tempo indeterminato",
    "tdet": "Tempo determinato",
}

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class Subito(Scraper):
    """
    Scraper for Subito Lavoro (https://www.subito.it, "Offerte di lavoro").

    Reads the search result pages' ``__NEXT_DATA__`` JSON (30 ads per page).
    ``location`` is the province ("Verona", "Verona, Veneto, Italia" also
    works: only the first part is used). Subito's WAF blocks plain HTTP
    clients by TLS fingerprint, so a browser-like TLS session is used.
    """

    base_url = "https://www.subito.it"

    def __init__(
        self,
        proxies: list[str] | str | None = None,
        ca_cert: str | None = None,
        user_agent: str | None = None,
    ):
        super().__init__(Site.SUBITO, proxies=proxies, ca_cert=ca_cert)
        self.user_agent = user_agent
        self.scraper_input = None

    def _search_url(self, location: str | None) -> str:
        province = _slug((location or "").split(",")[0])
        region = _PROVINCE_REGION.get(province)
        if region:
            return f"{self.base_url}/annunci-{region}/vendita/offerte-lavoro/{province}/"
        return f"{self.base_url}/annunci-italia/vendita/offerte-lavoro/"

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        session = create_session(proxies=self.proxies, ca_cert=self.ca_cert, is_tls=True)
        headers = {
            "User-Agent": self.user_agent
            or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/140.0 Safari/537.36",
            "Accept-Language": "it-IT,it;q=0.9",
        }
        url = self._search_url(scraper_input.location)
        wanted = scraper_input.results_wanted or 15
        jobs: list[JobPost] = []
        seen: set[str] = set()
        page = 1
        while len(jobs) < wanted and page <= 10:
            params = {"q": scraper_input.search_term or ""}
            if page > 1:
                params["o"] = page
            try:
                response = session.get(url, params=params, headers=headers,
                                       timeout_seconds=scraper_input.request_timeout)
                if response.status_code != 200:
                    log.error(f"Subito: HTTP {response.status_code} on page {page}")
                    break
                ads = self._extract_ads(response.text)
            except Exception as e:
                log.error(f"Subito: request failed - {e}")
                break
            if not ads:
                break
            for ad in ads:
                if not self._matches(ad, scraper_input.search_term):
                    continue
                post = self._parse(ad)
                if post and post.job_url not in seen:
                    seen.add(post.job_url)
                    jobs.append(post)
                    if len(jobs) >= wanted:
                        break
            page += 1
        return JobResponse(jobs=jobs)

    @staticmethod
    def _extract_ads(html: str) -> list[dict]:
        match = _NEXT_DATA_RE.search(html)
        if not match:
            return []
        try:
            items = json.loads(match.group(1))["props"]["pageProps"]["initialState"]["items"]
        except (KeyError, TypeError, ValueError):
            return []
        ads = items.get("originalList") or []
        return [a.get("item", a) for a in ads if isinstance(a, dict)]

    @staticmethod
    def _matches(ad: dict, search_term: str | None) -> bool:
        """Subito's own search is loose ("programmatore" also returns
        "PROGRAMMA GOL" sales jobs): keep an ad only if every word of the
        query appears in its title or text."""
        words = [w for w in (search_term or "").lower().split() if len(w) >= 3]
        text = f"{ad.get('subject', '')} {ad.get('body', '')}".lower()
        return all(w in text for w in words)

    @staticmethod
    def _feature(ad: dict, key: str) -> dict | None:
        values = ((ad.get("features") or {}).get(key) or {}).get("values") or []
        return values[0] if values else None

    def _parse(self, ad: dict) -> JobPost | None:
        title = (ad.get("subject") or "").strip()
        url = (ad.get("urls") or {}).get("default")
        if not title or not url:
            return None

        geo = ad.get("geo") or {}
        town = (geo.get("town") or {}).get("value")
        province = (geo.get("city") or {}).get("shortName")
        region = (geo.get("region") or {}).get("value")

        salary = None
        price = self._feature(ad, "/price")
        if price:
            try:
                amount = float(price.get("key"))
                salary = Compensation(
                    min_amount=amount, max_amount=amount, currency="EUR",
                    interval=CompensationInterval.YEARLY if amount >= 5000 else CompensationInterval.MONTHLY,
                )
            except (TypeError, ValueError):
                pass

        contract = self._feature(ad, "/contract_type")
        level = self._feature(ad, "/work_level")
        sector = self._feature(ad, "/job_category")
        hours = self._feature(ad, "/work_hour")
        advertiser = ad.get("advertiser") or {}

        extra = [
            f"{label}: {v['value']}"
            for label, v in (("Contratto", contract), ("Orario", hours), ("Livello", level))
            if v
        ]
        description = (ad.get("body") or "").strip()
        if extra:
            description = f"{description}\n\n" + "\n".join(extra)

        date_posted = None
        try:
            date_posted = datetime.strptime(ad.get("date", ""), "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            pass

        return JobPost(
            id=f"subito-{url.rsplit('-', 1)[-1].split('.')[0]}",
            title=title,
            company_name=advertiser.get("name") or None,
            job_url=url,
            location=Location(city=town, state=province or region, country="IT"),
            description=description or None,
            compensation=salary,
            date_posted=date_posted,
            is_remote=False,
            job_level=level["value"] if level else None,
            company_industry=sector["value"] if sector else None,
            listing_type=_CONTRACT.get(contract["key"], contract["value"]) if contract else None,
        )
