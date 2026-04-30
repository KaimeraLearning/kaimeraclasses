"""Timezone helpers — Kaimera Learning operates in IST (Asia/Kolkata).

Class times, demo slots, dates etc. are entered by users as IST wall-clock and
stored verbatim ("10:00", "2026-02-15"). All comparisons against "now" must be
done in IST too — comparing UTC `datetime.now()` against an IST wall-clock
gives a 5h30m skew that breaks no-show detection, today-window logic, etc.

Override via env: APP_TIMEZONE=Asia/Kolkata (default).
"""
import os
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None

_TZ_NAME = os.environ.get("APP_TIMEZONE", "Asia/Kolkata")


def _local_tz():
    """Return a tzinfo for the configured local zone, falling back to a fixed
    +05:30 offset if zoneinfo isn't available (rare)."""
    if ZoneInfo is not None:
        try:
            return ZoneInfo(_TZ_NAME)
        except Exception:
            pass
    return timezone(timedelta(hours=5, minutes=30))


def now_local() -> datetime:
    """Current time as a tz-aware datetime in the configured local zone (IST)."""
    return datetime.now(_local_tz())


def today_local_str() -> str:
    """`YYYY-MM-DD` for "today" in the local zone."""
    return now_local().strftime("%Y-%m-%d")


def parse_class_end(end_date: str, end_time: str) -> datetime:
    """Parse a stored class `end_date` + `end_time` into a tz-aware local
    datetime. The values were entered by users in IST wall-clock and stored
    verbatim, so we attach the local tz directly (no UTC conversion).

    Raises ValueError if either field is missing/malformed.
    """
    if not end_date:
        raise ValueError("end_date is required")
    et = (end_time or "23:59").strip()
    dt = datetime.fromisoformat(f"{end_date}T{et}:00")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_local_tz())
    return dt


def is_past_grace(end_date: str, end_time: str, grace_minutes: int = 30) -> bool:
    """True if `end_date + end_time + grace` has elapsed in local time.
    Returns False on parse errors (caller decides how to interpret)."""
    try:
        end_dt = parse_class_end(end_date, end_time)
    except Exception:
        return False
    return now_local() > end_dt + timedelta(minutes=grace_minutes)

