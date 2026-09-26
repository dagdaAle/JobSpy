from __future__ import annotations

from datetime import datetime

from jobspy.model import (
    Compensation,
    CompensationInterval,
    DescriptionFormat,
    JobPost,
    JobResponse,
    Location,
    Scraper,
    ScraperInput,
    Site,
)
from jobspy.util import create_logger, create_session, markdown_converter, plain_converter

log = create_logger("inPA")

# Province -> region, as inPA writes it in a notice's "sedi". Used to keep
# region-wide notices (sedi == ["Veneto"]) when searching for a province.
_PROVINCE_REGION = {
    "verona": "veneto", "vicenza": "veneto", "padova": "veneto", "venezia": "veneto",
    "treviso": "veneto", "rovigo": "veneto", "belluno": "veneto",
    "milano": "lombardia", "brescia": "lombardia", "mantova": "lombardia",
    "bergamo": "lombardia", "cremona": "lombardia",
    "trento": "trentino-alto adige", "bolzano": "trentino-alto adige",
    "bologna": "emilia romagna", "modena": "emilia romagna", "ferrara": "emilia romagna",
}

# Notices valid everywhere (ministries, national agencies).
_NATIONAL = {"italia", "tutto il territorio nazionale", "nazionale"}


class InPA(Scraper):
    """
    Scraper for inPA (https://www.inpa.gov.it), the Italian public
    administration's official recruiting portal: public competitions
    (concorsi), notices and mobility.

    Uses the portal's public search API (no login). Only notices still open
    for applications are returned. The API has no reliable place filter, so
    ``location`` is applied client-side on the notice's "sedi": a notice is
    kept when it names the province, is region-wide for that province's
    region, or is national.
    """

    api_url = "https://portale.inpa.gov.it/concorsi-smart/api/concorso-public-area/search-better"
    detail_url = "https://www.inpa.gov.it/bandi-e-avvisi/dettaglio-bando-avviso/?concorso_id={id}"

    def __init__(
        self,
        proxies: list[str] | str | None = None,
        ca_cert: str | None = None,
        user_agent: str | None = None,
    ):
        super().__init__(Site.INPA, proxies=proxies, ca_cert=ca_cert)
        self.user_agent = user_agent
        self.scraper_input = None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        session = create_session(
            proxies=self.proxies, ca_cert=self.ca_cert, is_tls=False, has_retry=True
        )
        headers = {
            "User-Agent": self.user_agent or "Mozilla/5.0 (compatible; JobSpy/1.0)",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {"text": scraper_input.search_term or "", "status": ["OPEN"]}
        wanted = scraper_input.results_wanted or 15
        jobs: list[JobPost] = []
        page = 0
        while len(jobs) < wanted and page < 20:
            try:
                response = session.post(
                    self.api_url,
                    params={"page": page, "size": 50},
                    json=body,
                    headers=headers,
                    timeout=scraper_input.request_timeout,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                log.error(f"inPA: request failed - {e}")
                break
            notices = data.get("content") or []
            for notice in notices:
                if not self._in_area(notice, scraper_input.location):
                    continue
                post = self._parse(notice)
                if post:
                    jobs.append(post)
                    if len(jobs) >= wanted:
                        break
            if data.get("last", True) or not notices:
                break
            page += 1
        return JobResponse(jobs=jobs)

    @staticmethod
    def _in_area(notice: dict, location: str | None) -> bool:
        place = (location or "").split(",")[0].strip().lower()
        if not place or place in _NATIONAL:
            return True
        sedi = [str(s).strip().lower() for s in notice.get("sedi") or []]
        if not sedi:
            # No place given: can't tell where it is, so don't show it.
            return False
        if any(s in _NATIONAL for s in sedi):
            return True
        if place in sedi:
            return True
        region = _PROVINCE_REGION.get(place, place)
        # Region-wide notice: names the region and no specific province.
        return sedi == [region]

    def _parse(self, notice: dict) -> JobPost | None:
        title = (notice.get("titolo") or "").strip()
        if not title or not notice.get("id"):
            return None
        figure = (notice.get("figuraRicercata") or "").strip()
        if figure and figure.lower() not in title.lower():
            title = f"{title} – {figure}"

        description = notice.get("descrizione") or notice.get("descrizioneBreve") or ""
        fmt = self.scraper_input.description_format
        if description and fmt == DescriptionFormat.MARKDOWN:
            description = markdown_converter(description)
        elif description and fmt == DescriptionFormat.PLAIN:
            description = plain_converter(description)

        deadline = self._date(notice.get("dataScadenza"))
        facts = [
            f"Scadenza domande: {deadline.strftime('%d/%m/%Y')}" if deadline else None,
            f"Posti: {notice['numPosti']}" if notice.get("numPosti") else None,
            f"Procedura: {', '.join(notice.get('categorie') or [])}" if notice.get("categorie") else None,
            f"Sedi: {', '.join(notice.get('sedi') or [])}" if notice.get("sedi") else None,
        ]
        header = "\n".join(f for f in facts if f)
        description = f"{header}\n\n{description}".strip() if header else description

        sedi = notice.get("sedi") or []
        salary = None
        lo, hi = notice.get("salaryMin"), notice.get("salaryMax")
        if lo or hi:
            salary = Compensation(
                min_amount=lo or hi, max_amount=hi or lo, currency="EUR",
                interval=CompensationInterval.YEARLY,
            )

        enti = notice.get("entiRiferimento") or []
        return JobPost(
            id=f"inpa-{notice['id']}",
            title=title,
            company_name=enti[0] if enti else None,
            job_url=self.detail_url.format(id=notice["id"]),
            job_url_direct=notice.get("linkReindirizzamento") or None,
            location=Location(
                city=sedi[-1] if len(sedi) > 1 else None,
                state=sedi[0] if sedi else None,
                country="IT",
            ),
            description=description or None,
            compensation=salary,
            date_posted=self._date(notice.get("dataPubblicazione")),
            is_remote=False,
            company_industry="Pubblica Amministrazione",
            job_function=", ".join(notice.get("settori") or []) or None,
            listing_type=notice.get("tipoProcedura"),
        )

    @staticmethod
    def _date(value: str | None):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
