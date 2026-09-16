from __future__ import annotations

from datetime import date

from app.domain.entities import Briefing, BriefingListItem, Source, Story, StorySummary, Topic
from app.domain.exceptions import AppError
from app.domain.interfaces import CatalogRepository, EditorialRepository, HealthRepository


class PublicReads:
    def __init__(
        self,
        editorial: EditorialRepository,
        catalog: CatalogRepository,
        health: HealthRepository,
    ) -> None:
        self.editorial = editorial
        self.catalog = catalog
        self.health = health

    async def meta(self) -> dict[str, str | None]:
        current = await self.editorial.get_current_date()
        return {
            "currentDate": current.isoformat() if current else None,
            "timezone": "Asia/Shanghai",
        }

    async def today(self) -> Briefing:
        current = await self.editorial.get_current_date()
        if current is None:
            raise AppError(404, "NOT_FOUND", "No briefing for this date.")
        return await self.briefing(current)

    async def briefing(self, day: date) -> Briefing:
        found = await self.editorial.get_published_briefing(day)
        if found is None:
            raise AppError(404, "NOT_FOUND", "No briefing for this date.")
        return found

    async def list_briefings(self, start: date, end: date) -> list[BriefingListItem]:
        return await self.editorial.list_published_briefings(start, end)

    async def story(self, slug: str) -> Story:
        found = await self.editorial.get_published_story(slug)
        if found is None:
            raise AppError(404, "NOT_FOUND", "Unknown cluster.")
        return found

    async def topics(self) -> list[Topic]:
        return await self.catalog.list_active_topics()

    async def topic(self, slug: str) -> Topic:
        found = await self.catalog.get_active_topic_with_stories(slug)
        if found is None:
            raise AppError(404, "NOT_FOUND", "Unknown topic.")
        return found

    async def sources(self) -> list[Source]:
        return await self.catalog.list_sources()

    async def search(self, query: str) -> list[StorySummary]:
        return await self.editorial.search_published_stories(query)

    async def ready(self) -> None:
        ok = await self.health.ping()
        if not ok:
            raise AppError(503, "INTERNAL_ERROR", "Database unavailable.")
