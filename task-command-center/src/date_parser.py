"""Small date parser for command-line inputs."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .errors import TaskCtlError


DATE_FORMATS = ["%Y-%m-%d", "%d.%m.%Y"]
DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
    "%d.%m.%Y %H:%M",
]


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise TaskCtlError(f"Cannot parse date '{value}'. Use YYYY-MM-DD.")


def parse_datetime(value: str, timezone: str) -> datetime:
    raw = value.strip()
    tz = ZoneInfo(timezone)

    lowered = raw.lower()
    for prefix in ("tomorrow ", "завтра "):
        if lowered.startswith(prefix):
            clock = raw[len(prefix) :].strip()
            parsed_time = _parse_time(clock)
            return datetime.combine(date.today() + timedelta(days=1), parsed_time, tz)

    for prefix in ("today ", "сегодня "):
        if lowered.startswith(prefix):
            clock = raw[len(prefix) :].strip()
            parsed_time = _parse_time(clock)
            return datetime.combine(date.today(), parsed_time, tz)

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=tz)
        except ValueError:
            pass

    raise TaskCtlError(
        f"Cannot parse datetime '{value}'. Use 'YYYY-MM-DD HH:MM' or 'tomorrow HH:MM'."
    )


def add_minutes(start: datetime, minutes: int) -> datetime:
    return start + timedelta(minutes=minutes)


def _parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise TaskCtlError(f"Cannot parse time '{value}'. Use HH:MM.") from exc
