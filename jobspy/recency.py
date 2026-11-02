"""Date-only source filtering. Unknown dates remain visible, never invented."""
from datetime import date, datetime, timedelta, timezone


def within_recency(posted: date | None, hours_old: int | None) -> bool:
    if hours_old is None or posted is None:
        return True
    # JobPost exposes dates, not timestamps: retain the entire cutoff day.
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_old)).date()
    return posted >= cutoff
