"""Persistent Ford API request guard; pure logic for unit testing."""
from __future__ import annotations
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import isfinite


def retry_after_seconds(header: str | None, *, now: datetime | None = None) -> int:
    """RFC-compliant Retry-After delta seconds or HTTP date, bounded to 7d."""
    if not header:
        return 0
    header = header.strip()
    if header.isdigit():
        return min(int(header), 604800)
    try:
        dt = parsedate_to_datetime(header)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        seconds = (dt - (now or datetime.now(timezone.utc))).total_seconds()
        return min(604800, max(0, int(seconds + 0.999))) if isfinite(seconds) else 0
    except (ValueError, TypeError, OverflowError, IndexError):
        return 0


class RequestBudget:
    """Account-scoped scheduled GET limiter persisted across HA restarts."""

    def __init__(self, *, next_allowed: float = 0, suspended: bool = False) -> None:
        self.next_allowed = max(0, float(next_allowed))
        self.suspended = bool(suspended)

    def allowed(self, now: float) -> bool:
        return not self.suspended and now >= self.next_allowed

    def mark_started(self, now: float, interval_minutes: int) -> None:
        # Reserve the full budget BEFORE sending a request. Even a crash or
        # timeout cannot produce rapid successive requests on restart.
        self.next_allowed = max(self.next_allowed, now + max(15, interval_minutes) * 60)

    def throttle(self, now: float, retry_after: int = 0) -> None:
        self.next_allowed = max(self.next_allowed, now + max(3600, retry_after))

    def temporary_failure(self, now: float) -> None:
        self.next_allowed = max(self.next_allowed, now + 1800)

    def forbid(self) -> None:
        self.suspended = True
