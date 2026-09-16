from __future__ import annotations

from datetime import datetime

import pytest

from app.application.schedule import matching_slot, next_run_at, parse_schedule
from app.application.timefmt import SHANGHAI

TIMES = ("06:30", "12:30", "18:30")


def test_parse_schedule_sorts_and_rejects_junk():
    assert parse_schedule("18:30, 06:30,12:30") == TIMES
    with pytest.raises(ValueError):
        parse_schedule("")
    with pytest.raises(ValueError):
        parse_schedule("06:30,06:30")
    with pytest.raises(ValueError):
        parse_schedule("24:00")
    with pytest.raises(ValueError):
        parse_schedule("6:30")
    with pytest.raises(ValueError):
        parse_schedule(",".join(f"{hour:02d}:00" for hour in range(9)))


def test_next_run_same_day_wraps_and_skips_exact_minute():
    morning = datetime(2026, 9, 16, 7, 0, tzinfo=SHANGHAI)
    nxt = next_run_at(morning, TIMES).astimezone(SHANGHAI)
    assert nxt.strftime("%Y-%m-%d %H:%M") == "2026-09-16 12:30"

    exact = datetime(2026, 9, 16, 6, 30, 0, tzinfo=SHANGHAI)
    nxt = next_run_at(exact, TIMES).astimezone(SHANGHAI)
    assert nxt.strftime("%Y-%m-%d %H:%M") == "2026-09-16 12:30"

    late = datetime(2026, 9, 16, 18, 30, 1, tzinfo=SHANGHAI)
    nxt = next_run_at(late, TIMES).astimezone(SHANGHAI)
    assert nxt.strftime("%Y-%m-%d %H:%M") == "2026-09-17 06:30"


def test_matching_slot_uses_shanghai_clock():
    assert matching_slot(datetime(2026, 9, 16, 6, 30, 45, tzinfo=SHANGHAI), TIMES) == "06:30"
    assert matching_slot(datetime(2026, 9, 16, 6, 31, tzinfo=SHANGHAI), TIMES) is None
