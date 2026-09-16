from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.domain.entities import Text

SHANGHAI = ZoneInfo("Asia/Shanghai")


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def shanghai_date(value: datetime) -> date:
    return value.astimezone(SHANGHAI).date()


def combine_hhmm(day: date, hhmm: str) -> datetime:
    hour, minute = hhmm.split(":")
    return datetime(day.year, day.month, day.day, int(hour), int(minute), tzinfo=SHANGHAI)


def format_hhmm(value: datetime | None, *, dash_if_none: bool = False) -> str:
    if value is None:
        return "—" if dash_if_none else ""
    return value.astimezone(SHANGHAI).strftime("%H:%M")


WEEKDAY_ZH = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
WEEKDAY_EN = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def weekday_for(day: date) -> Text:
    idx = day.weekday()
    return Text(WEEKDAY_ZH[idx], WEEKDAY_EN[idx])
