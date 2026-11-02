"""Helpers shared by the fork-only sources."""

from __future__ import annotations

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jobspy.model import DescriptionFormat
from jobspy.util import RequestsRotating, description_fields


def with_retry(session: RequestsRotating) -> RequestsRotating:
    """Retry network errors and 5xx up to 3 times with backoff, POST included."""
    adapter = HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=None,
        )
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def description_text(html: str | None, fmt: DescriptionFormat) -> str | None:
    """The description in the requested format (None when empty)."""
    text = description_fields(html, fmt)["description"]
    return text if isinstance(text, str) else None
