from __future__ import annotations

from datetime import date

from app.adapters.memory.repositories import MemoryWorld


def test_fixture_counts():
    world = MemoryWorld()
    assert len(world.topic_rows) == 10
    assert len(world.sources) == 12
    assert len(world.briefings) == 14
    assert len(world.story_records) == 53
    today = date(2026, 9, 14)
    briefing = world.briefings[today]
    assert len(briefing.must_read) == 8
    assert briefing.must_read[4].slug == "llama-41-8b"
    assert briefing.pulse.total_sources == 26
    assert briefing.pulse.clusters == 14