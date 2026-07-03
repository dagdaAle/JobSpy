from __future__ import annotations

from datetime import datetime

from jobspy.model import (
    Scraper,
    ScraperInput,
    Site,
    JobPost,
    JobResponse,
    Location,
    DescriptionFormat,
)
from jobspy.util import (
    create_logger,
    create_session,
    markdown_converter,
    plain_converter,
)

log = create_logger("WorkingNomads")


class WorkingNomads(Scraper):
    """
    Scraper for Working Nomads (https://www.workingnomads.com) using their
    public exposed-jobs JSON endpoint.

    Working Nomads is remote-only. There is no server-side search, so
    ``search_term`` is matched client-side against the title and tags. The
    ``location`` field often carries a time-zone hint (e.g. "Time zone: CET"),
    which is preserved so European / Italy-based candidates can filter.
    """

    base_url = "https://www.workingnomads.com/api/exposed_jobs/"

    def __init__(
        self,
        proxies: list[str] | str | None = None,
        ca_cert: str | None = None,
        user_agent: str | None = None,
    ):
        super().__init__(Site.WORKINGNOMADS, proxies=proxies, ca_cert=ca_cert)
        self.session = None
        self.scraper_input = None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        self.session = create_session(
            proxies=self.proxies, ca_cert=self.ca_cert, is_tls=False, has_retry=True
        )
        headers = {
            "User-Agent": self.user_agent
            or "Mozilla/5.0 (compatible; JobSpy/1.0)",
            "Accept": "application/json",
        }

        log.info("Fetching Working Nomads feed")
        try:
            response = self.session.get(
                self.base_url,
                headers=headers,
                timeout=scraper_input.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            log.error(f"WorkingNomads: request failed - {e}")
            return JobResponse(jobs=[])

        raw_jobs = data if isinstance(data, list) else []
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
                log.error(f"WorkingNomads: error parsing job - {e}")
                continue

        return JobResponse(jobs=job_list)

    @staticmethod
    def _matches_search(raw: dict, search: str) -> bool:
        haystack = " ".join(
            [
                str(raw.get("title", "")),
                str(raw.get("company_name", "")),
                str(raw.get("tags", "")),
                str(raw.get("category_name", "")),
            ]
        ).lower()
        return search in haystack

    def _parse_job(self, raw: dict) -> JobPost | None:
        job_url = raw.get("url")
        title = raw.get("title")
        if not job_url or not title:
            return None

        job_id = f"workingnomads-{abs(hash(job_url))}"

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
            company_name=raw.get("company_name"),
            location=location_obj,
            job_url=job_url,
            description=description,
            date_posted=self._parse_date(raw.get("pub_date")),
            is_remote=True,
            company_industry=raw.get("category_name"),
            skills=self._parse_tags(raw.get("tags")),
        )

    @staticmethod
    def _parse_tags(tags) -> list[str] | None:
        if not tags:
            return None
        if isinstance(tags, list):
            return [str(t).strip() for t in tags if str(t).strip()] or None
        if isinstance(tags, str):
            parts = [t.strip() for t in tags.split(",") if t.strip()]
            return parts or None
        return None

    @staticmethod
    def _parse_date(date_str: str | None):
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            return None
