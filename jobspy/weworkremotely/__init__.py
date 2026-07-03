from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

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

log = create_logger("WeWorkRemotely")


class WeWorkRemotely(Scraper):
    """
    Scraper for We Work Remotely (https://weworkremotely.com) using their public
    per-category RSS feeds.

    WWR is remote-only. There is no server-side search, so ``search_term`` is
    matched client-side against the job title. Multiple category feeds are
    aggregated. Feed titles are formatted ``"Company: Position"``.
    """

    base_url = "https://weworkremotely.com/categories"

    # Broad tech coverage; extendable.
    category_feeds = [
        "remote-programming-jobs",
        "remote-full-stack-programming-jobs",
        "remote-back-end-programming-jobs",
        "remote-front-end-programming-jobs",
        "remote-devops-sysadmin-jobs",
        "remote-design-jobs",
        "remote-product-jobs",
    ]

    def __init__(
        self,
        proxies: list[str] | str | None = None,
        ca_cert: str | None = None,
        user_agent: str | None = None,
    ):
        super().__init__(Site.WEWORKREMOTELY, proxies=proxies, ca_cert=ca_cert)
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
            "Accept": "application/rss+xml, application/xml, text/xml",
        }

        search = (scraper_input.search_term or "").strip().lower()
        results_wanted = scraper_input.results_wanted or 15

        seen_urls: set[str] = set()
        job_list: list[JobPost] = []

        for feed_slug in self.category_feeds:
            if len(job_list) >= results_wanted:
                break
            url = f"{self.base_url}/{feed_slug}.rss"
            log.info(f"Fetching WWR feed {feed_slug}")
            try:
                response = self.session.get(
                    url, headers=headers, timeout=scraper_input.request_timeout
                )
                response.raise_for_status()
                root = ET.fromstring(response.content)
            except Exception as e:
                log.error(f"WeWorkRemotely: failed feed {feed_slug} - {e}")
                continue

            for item in root.findall(".//item"):
                if len(job_list) >= results_wanted:
                    break
                try:
                    job_post = self._parse_item(item, feed_slug, search, seen_urls)
                    if job_post:
                        job_list.append(job_post)
                except Exception as e:
                    log.error(f"WeWorkRemotely: error parsing item - {e}")
                    continue

        return JobResponse(jobs=job_list)

    def _parse_item(
        self, item, feed_slug: str, search: str, seen_urls: set[str]
    ) -> JobPost | None:
        link = self._text(item, "link")
        raw_title = self._text(item, "title")
        if not link or not raw_title:
            return None
        if link in seen_urls:
            return None

        # Title format: "Company: Position"
        if ":" in raw_title:
            company_name, _, position = raw_title.partition(":")
            company_name = company_name.strip()
            position = position.strip()
        else:
            company_name, position = None, raw_title.strip()

        if search and search not in position.lower():
            return None

        seen_urls.add(link)

        description = self._text(item, "description")
        if description:
            fmt = self.scraper_input.description_format
            if fmt == DescriptionFormat.MARKDOWN:
                description = markdown_converter(description)
            elif fmt == DescriptionFormat.PLAIN:
                description = plain_converter(description)

        region = self._text(item, "region") or "Anywhere in the World"
        category = self._text(item, "category")
        location_obj = Location(city=None, state=None, country=region)

        job_id = f"weworkremotely-{abs(hash(link))}"

        return JobPost(
            id=job_id,
            title=position,
            company_name=company_name,
            location=location_obj,
            job_url=link,
            description=description,
            date_posted=self._parse_date(self._text(item, "pubDate")),
            is_remote=True,
            company_industry=category,
        )

    @staticmethod
    def _text(item, tag: str) -> str | None:
        el = item.find(tag)
        if el is not None and el.text:
            return el.text.strip()
        return None

    @staticmethod
    def _parse_date(date_str: str | None):
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str).date()
        except (ValueError, TypeError):
            return None
