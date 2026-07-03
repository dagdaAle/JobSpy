from __future__ import annotations

import ast
from datetime import datetime

from jobspy.model import (
    Scraper,
    ScraperInput,
    Site,
    JobPost,
    JobResponse,
    Location,
    JobType,
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

log = create_logger("Remotive")


class Remotive(Scraper):
    """
    Scraper for Remotive (https://remotive.com) using their public JSON API.

    Remotive is a remote-only job board. The API returns all jobs matching an
    optional ``search`` term; there is no location radius (every job is remote),
    so parameters like ``distance`` and ``location`` are ignored. The
    ``candidate_required_location`` field is preserved in the job location so
    users can filter to Europe / Italy-friendly time zones themselves.
    """

    base_url = "https://remotive.com/api/remote-jobs"

    def __init__(
        self,
        proxies: list[str] | str | None = None,
        ca_cert: str | None = None,
        user_agent: str | None = None,
    ):
        super().__init__(Site.REMOTIVE, proxies=proxies, ca_cert=ca_cert)
        self.session = None
        self.scraper_input = None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        self.session = create_session(
            proxies=self.proxies, ca_cert=self.ca_cert, is_tls=False, has_retry=True
        )
        headers = {
            "User-Agent": self.user_agent
            or "Mozilla/5.0 (compatible; JobSpy/1.0; +https://github.com/speedyapply/JobSpy)",
            "Accept": "application/json",
        }

        params = {}
        if scraper_input.search_term:
            params["search"] = scraper_input.search_term

        log.info(f"Fetching Remotive jobs (search={scraper_input.search_term!r})")
        try:
            response = self.session.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=scraper_input.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            log.error(f"Remotive: request failed - {e}")
            return JobResponse(jobs=[])

        raw_jobs = data.get("jobs", [])
        results_wanted = scraper_input.results_wanted or 15

        job_list: list[JobPost] = []
        for raw in raw_jobs[:results_wanted]:
            try:
                job_post = self._parse_job(raw)
                if job_post:
                    job_list.append(job_post)
            except Exception as e:
                log.error(f"Remotive: error parsing job - {e}")
                continue

        return JobResponse(jobs=job_list)

    def _parse_job(self, raw: dict) -> JobPost | None:
        job_url = raw.get("url")
        title = raw.get("title")
        if not job_url or not title:
            return None

        job_id = f"remotive-{raw.get('id')}"

        # Description formatting to respect the requested format
        description = raw.get("description")
        if description:
            fmt = self.scraper_input.description_format
            if fmt == DescriptionFormat.MARKDOWN:
                description = markdown_converter(description)
            elif fmt == DescriptionFormat.PLAIN:
                description = plain_converter(description)

        # candidate_required_location -> free-text location, kept as country string
        candidate_location = raw.get("candidate_required_location") or "Worldwide"
        location_obj = Location(city=None, state=None, country=candidate_location)

        return JobPost(
            id=job_id,
            title=title,
            company_name=raw.get("company_name"),
            company_logo=raw.get("company_logo_url") or raw.get("company_logo"),
            location=location_obj,
            job_url=job_url,
            description=description,
            job_type=self._parse_job_type(raw.get("job_type")),
            compensation=self._parse_salary(raw.get("salary")),
            date_posted=self._parse_date(raw.get("publication_date")),
            is_remote=True,
            company_industry=raw.get("category"),
            skills=self._parse_tags(raw.get("tags")),
        )

    @staticmethod
    def _parse_job_type(job_type_str: str | None) -> list[JobType] | None:
        if not job_type_str:
            return None
        mapping = {
            "full_time": JobType.FULL_TIME,
            "part_time": JobType.PART_TIME,
            "contract": JobType.CONTRACT,
            "freelance": JobType.CONTRACT,
            "internship": JobType.INTERNSHIP,
        }
        jt = mapping.get(job_type_str.lower())
        return [jt] if jt else None

    @staticmethod
    def _parse_salary(salary_str: str | None) -> Compensation | None:
        if not salary_str:
            return None
        # Remotive salaries are free-form text (e.g. "$12K", "€40k - €60k").
        # Store as yearly interval without over-parsing the ambiguous string.
        return Compensation(
            interval=CompensationInterval.YEARLY,
            min_amount=None,
            max_amount=None,
            currency=None,
        )

    @staticmethod
    def _parse_date(date_str: str | None):
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_tags(tags) -> list[str] | None:
        if not tags:
            return None
        if isinstance(tags, list):
            return [str(t) for t in tags] or None
        # API sometimes returns tags as a string repr of a list
        if isinstance(tags, str):
            try:
                parsed = ast.literal_eval(tags)
                if isinstance(parsed, list):
                    return [str(t) for t in parsed] or None
            except (ValueError, SyntaxError):
                return [tags]
        return None
