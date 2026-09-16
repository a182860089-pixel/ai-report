from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from app.application.timefmt import SHANGHAI

_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def parse_schedule(raw: str) -> tuple[str, ...]:
    parts = [item.strip() for item in (raw or "").split(",") if item.strip()]
    if not parts or len(parts) > 8:
        raise ValueError("PIPELINE_SCHEDULE must contain 1-8 HH:MM times")
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        if _HHMM.fullmatch(part) is None:
            raise ValueError("PIPELINE_SCHEDULE times must be HH:MM")
        if part in seen:
            raise ValueError("PIPELINE_SCHEDULE times must be unique")
        seen.add(part)
        out.append(part)
    return tuple(sorted(out))


def next_run_at(now: datetime, times: tuple[str, ...], tz=SHANGHAI) -> datetime:
    if not times:
        raise ValueError("schedule times required")
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(tz)
    for stamp in times:
        hour, minute = stamp.split(":")
        candidate = local.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        if candidate > local:
            return candidate.astimezone(timezone.utc)
    hour, minute = times[0].split(":")
    tomorrow = local.date() + timedelta(days=1)
    candidate = datetime(tomorrow.year, tomorrow.month, tomorrow.day, int(hour), int(minute), tzinfo=tz)
    return candidate.astimezone(timezone.utc)


def matching_slot(now: datetime, times: tuple[str, ...], tz=SHANGHAI) -> str | None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(tz)
    stamp = f"{local.hour:02d}:{local.minute:02d}"
    return stamp if stamp in times else None
