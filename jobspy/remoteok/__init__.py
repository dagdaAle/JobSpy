from __future__ import annotations

from datetime import datetime

from jobspy.model import (
    Scraper,
    ScraperInput,
    Site,
    JobPost,
    JobResponse,
    Location,
    Compensation,
    CompensationInterval,
    DescriptionFormat,
)
from jobspy.util import (
    create_logger,
    create_session,
    markdown_converter,
    plain_converter,
)

log = create_logger("RemoteOK")


class RemoteOK(Scraper):
    """
    Scraper for RemoteOK (https://remoteok.com) using their public JSON feed.

    RemoteOK is remote-only. The ``/api`` endpoint returns the full feed; the
    first element is a legal/metadata object and is skipped. There is no
    server-side search, so ``search_term`` is matched client-side against the
    position title and tags.
    """

    base_url = "https://remoteok.com/api"

    def __init__(
        self,
        proxies: list[str] | str | None = None,
        ca_cert: str | None = None,
        user_agent: str | None = None,
    ):
        super().__init__(Site.REMOTEOK, proxies=proxies, ca_cert=ca_cert)
        self.session = None
        self.scraper_input = None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        self.session = create_session(
            proxies=self.proxies, ca_cert=self.ca_cert, is_tls=False, has_retry=True
        )
        headers = {
            "User-Agent": self.user_agent
            or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        log.info("Fetching RemoteOK feed")
        try:
            response = self.session.get(
                self.base_url,
                headers=headers,
                timeout=scraper_input.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            log.error(f"RemoteOK: request failed - {e}")
            return JobResponse(jobs=[])

        # First element is legal/metadata; skip it.
        raw_jobs = data[1:] if data and isinstance(data, list) else []

        search = (scraper_input.search_term or "").strip().lower()
        results_wanted = scraper_input.results_wanted or 15

        job_list: list[JobPost] = []
        for raw in raw_jobs:
            if len(job_list) >= results_wanted:
                break
            if search and not self._matches_search(raw, search):
                continue
            try:
                job_post = self._parse_job(raw)
                if job_post:
                    job_list.append(job_post)
            except Exception as e:
                log.error(f"RemoteOK: error parsing job - {e}")
                continue

        return JobResponse(jobs=job_list)

    @staticmethod
    def _matches_search(raw: dict, search: str) -> bool:
        haystack = " ".join(
            [
                str(raw.get("position", "")),
                str(raw.get("company", "")),
                " ".join(raw.get("tags", []) or []),
            ]
        ).lower()
        return search in haystack

    def _parse_job(self, raw: dict) -> JobPost | None:
        job_url = raw.get("url") or raw.get("apply_url")
        title = raw.get("position")
        if not job_url or not title:
            return None

        job_id = f"remoteok-{raw.get('id')}"

        description = raw.get("description")
        if description:
            fmt = self.scraper_input.description_format
            if fmt == DescriptionFormat.MARKDOWN:
                description = markdown_converter(description)
            elif fmt == DescriptionFormat.PLAIN:
                description = plain_converter(description)

        raw_location = raw.get("location") or "Remote"
        location_obj = Location(city=None, state=None, country=raw_location)

        return JobPost(
            id=job_id,
            title=title,
            company_name=raw.get("company"),
            company_logo=raw.get("company_logo") or raw.get("logo") or None,
            location=location_obj,
            job_url=job_url,
            description=description,
            compensation=self._parse_salary(raw),
            date_posted=self._parse_date(raw.get("date")),
            is_remote=True,
            skills=raw.get("tags") or None,
        )

    @staticmethod
    def _parse_salary(raw: dict) -> Compensation | None:
        try:
            smin = int(raw.get("salary_min") or 0)
            smax = int(raw.get("salary_max") or 0)
        except (ValueError, TypeError):
            return None
        if smin <= 0 and smax <= 0:
            return None
        return Compensation(
            interval=CompensationInterval.YEARLY,
            min_amount=smin or None,
            max_amount=smax or None,
            currency="USD",
        )

    @staticmethod
    def _parse_date(date_str: str | None):
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            return None
