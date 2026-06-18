"""Application time helpers.

SQLite stores `CURRENT_TIMESTAMP` in UTC. API responses and date filters should
use the user's local study timezone so review windows and displayed times match
when the note was actually recorded.
"""
import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Shanghai")


def app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(APP_TIMEZONE)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Shanghai")


def now_local() -> datetime:
    return datetime.now(app_timezone())


def today_str() -> str:
    return now_local().strftime("%Y-%m-%d")


def yesterday_str() -> str:
    return (now_local() - timedelta(days=1)).strftime("%Y-%m-%d")


def to_local_display(value: str | None) -> str | None:
    if not value:
        return value
    dt = _parse_database_utc(value)
    return dt.astimezone(app_timezone()).strftime(DATETIME_FORMAT)


def local_date_bounds_utc(date_str: str) -> tuple[str, str]:
    day = date.fromisoformat(date_str)
    start_local = datetime.combine(day, time.min, tzinfo=app_timezone())
    end_local = start_local + timedelta(days=1)
    return _format_utc(start_local), _format_utc(end_local)


def _parse_database_utc(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        dt = datetime.strptime(value.split(".")[0], DATETIME_FORMAT)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(DATETIME_FORMAT)
