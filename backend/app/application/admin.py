from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.application.timefmt import combine_hhmm, weekday_for
from app.domain.entities import (
    AdminUser,
    Briefing,
    Citation,
    Pulse,
    PulseTopic,
    Source,
    Story,
    Text,
    TimelineItem,
    TopicRef,
)
from app.domain.exceptions import AppError
from app.domain.interfaces import AdminCatalogRepository, AdminEditorialRepository, IdentityRepository

CTRL_RE = re.compile(r"[\x00-\x1F\x7F]")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

TOPIC_POST = {"slug", "name", "blurb", "sortOrder"}
TOPIC_PATCH = {"name", "blurb", "sortOrder", "isActive", "slug"}
SOURCE_POST = {
    "id",
    "name",
    "status",
    "detail",
    "lastFetch",
    "todayCount",
    "consecutiveFailures",
    "isQuarantined",
    "homepageUrl",
    "feedUrl",
}
SOURCE_PATCH = SOURCE_POST - {"id"} | {"id"}
BRIEFING_POST = {"date", "title", "weekday", "moreHeading", "lede", "pulse", "updatedAt"}
BRIEFING_PATCH = {"title", "weekday", "moreHeading", "lede", "pulse", "updatedAt", "date"}
STORY_POST = {
    "slug",
    "date",
    "topicSlug",
    "section",
    "rank",
    "title",
    "dek",
    "synthesis",
    "timeline",
    "sources",
}
STORY_PATCH = STORY_POST | {"slug"}


def _unknown(payload: dict[str, Any], allowed: set[str]) -> None:
    if not isinstance(payload, dict):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    if set(payload) - allowed:
        raise AppError(422, "VALIDATION_ERROR", "Unknown field.")


def _clean_str(value: Any, *, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    if CTRL_RE.search(value):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    text = value.strip() if min_len > 0 else value
    if not (min_len <= len(text) <= max_len):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return text


def _bool(value: Any) -> bool:
    if not isinstance(value, bool):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return value


def _int(value: Any, *, min_v: int, max_v: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    if value < min_v or value > max_v:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return value


def _text(value: Any, *, max_len: int) -> Text:
    if not isinstance(value, dict):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    if set(value) - {"zh", "en"}:
        raise AppError(422, "VALIDATION_ERROR", "Unknown field.")
    if "zh" not in value or "en" not in value:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return Text(zh=_clean_str(value["zh"], min_len=1, max_len=max_len), en=_clean_str(value["en"], min_len=1, max_len=max_len))


def _slug(value: Any, *, max_len: int) -> str:
    if not isinstance(value, str) or not value or len(value) > max_len or not SLUG_RE.fullmatch(value):
        raise AppError(422, "VALIDATION_ERROR", "Invalid slug.")
    return value


def _date(value: Any) -> date:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        raise AppError(422, "VALIDATION_ERROR", "Invalid date. Use YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise AppError(422, "VALIDATION_ERROR", "Invalid date. Use YYYY-MM-DD.") from exc


def _hhmm(value: Any) -> str:
    if not isinstance(value, str) or not HHMM_RE.fullmatch(value):
        raise AppError(422, "VALIDATION_ERROR", "Invalid time.")
    return value


def _https_url(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AppError(422, "VALIDATION_ERROR", "Invalid URL.")
    if value == "":
        return None
    if CTRL_RE.search(value) or " " in value or len(value) > 500 or not value.startswith("https://"):
        raise AppError(422, "VALIDATION_ERROR", "Invalid URL.")
    if len(value) < 9:
        raise AppError(422, "VALIDATION_ERROR", "Invalid URL.")
    return value


def _last_fetch(value: Any) -> datetime | None | object:
    if value is None or value == "\u2014":
        return None
    return combine_hhmm(date(2026, 9, 14), _hhmm(value))


MISSING = object()


def parse_topic_create(payload: dict[str, Any]) -> dict[str, Any]:
    _unknown(payload, TOPIC_POST)
    for key in ("slug", "name", "blurb"):
        if key not in payload:
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return {
        "slug": _slug(payload["slug"], max_len=64),
        "name": _text(payload["name"], max_len=80),
        "blurb": _text(payload["blurb"], max_len=240),
        "sort_order": _int(payload["sortOrder"], min_v=0) if "sortOrder" in payload else 0,
    }


def parse_topic_patch(payload: dict[str, Any], current_slug: str) -> dict[str, Any]:
    _unknown(payload, TOPIC_PATCH)
    if "slug" in payload:
        incoming = payload["slug"]
        if not isinstance(incoming, str) or incoming != current_slug:
            raise AppError(422, "VALIDATION_ERROR", "Slug cannot be changed.")
    out: dict[str, Any] = {}
    if "name" in payload:
        out["name"] = _text(payload["name"], max_len=80)
    if "blurb" in payload:
        out["blurb"] = _text(payload["blurb"], max_len=240)
    if "sortOrder" in payload:
        out["sort_order"] = _int(payload["sortOrder"], min_v=0)
    if "isActive" in payload:
        out["is_active"] = _bool(payload["isActive"])
    return out


def parse_source_create(payload: dict[str, Any]) -> Source:
    _unknown(payload, SOURCE_POST)
    for key in ("id", "name", "status", "detail"):
        if key not in payload:
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    status = payload["status"]
    if status not in {"ok", "late", "bad"}:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    last_fetch = None
    if "lastFetch" in payload:
        last_fetch = _last_fetch(payload["lastFetch"])
    return Source(
        code=_slug(payload["id"], max_len=64),
        name=_clean_str(payload["name"], min_len=1, max_len=120),
        status=status,
        last_fetch_at=last_fetch,
        today_count=_int(payload["todayCount"], min_v=0) if "todayCount" in payload else 0,
        detail=_text(payload["detail"], max_len=240),
        consecutive_failures=_int(payload["consecutiveFailures"], min_v=0) if "consecutiveFailures" in payload else 0,
        is_quarantined=_bool(payload["isQuarantined"]) if "isQuarantined" in payload else False,
        homepage_url=_https_url(payload.get("homepageUrl")) if "homepageUrl" in payload else None,
        feed_url=_https_url(payload.get("feedUrl")) if "feedUrl" in payload else None,
    )


def parse_source_patch(payload: dict[str, Any], current: Source) -> Source:
    _unknown(payload, SOURCE_PATCH)
    if "id" in payload and payload["id"] != current.code:
        raise AppError(422, "VALIDATION_ERROR", "Code cannot be changed.")
    status = payload["status"] if "status" in payload else current.status
    if status not in {"ok", "late", "bad"}:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    last_fetch = current.last_fetch_at
    if "lastFetch" in payload:
        last_fetch = _last_fetch(payload["lastFetch"])
    return Source(
        code=current.code,
        name=_clean_str(payload["name"], min_len=1, max_len=120) if "name" in payload else current.name,
        status=status,
        last_fetch_at=last_fetch,
        today_count=_int(payload["todayCount"], min_v=0) if "todayCount" in payload else current.today_count,
        detail=_text(payload["detail"], max_len=240) if "detail" in payload else current.detail,
        consecutive_failures=(
            _int(payload["consecutiveFailures"], min_v=0)
            if "consecutiveFailures" in payload
            else current.consecutive_failures
        ),
        is_quarantined=_bool(payload["isQuarantined"]) if "isQuarantined" in payload else current.is_quarantined,
        homepage_url=_https_url(payload["homepageUrl"]) if "homepageUrl" in payload else current.homepage_url,
        feed_url=_https_url(payload["feedUrl"]) if "feedUrl" in payload else current.feed_url,
    )


def _pulse(value: Any) -> Pulse:
    if not isinstance(value, dict):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    allowed = {"clusters", "articles", "zhEn", "healthy", "totalSources", "topics"}
    if set(value) - allowed:
        raise AppError(422, "VALIDATION_ERROR", "Unknown field.")
    for key in ("clusters", "articles", "zhEn", "healthy", "totalSources", "topics"):
        if key not in value:
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    clusters = _int(value["clusters"], min_v=0)
    articles = _int(value["articles"], min_v=0)
    healthy = _int(value["healthy"], min_v=0)
    total_sources = _int(value["totalSources"], min_v=0)
    if healthy > total_sources:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    topics_raw = value["topics"]
    if not isinstance(topics_raw, list) or len(topics_raw) > 20:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    topics: list[PulseTopic] = []
    for item in topics_raw:
        if not isinstance(item, dict) or set(item) - {"name", "count"}:
            raise AppError(422, "VALIDATION_ERROR", "Unknown field." if isinstance(item, dict) and set(item) - {"name", "count"} else "Invalid payload.")
        if "name" not in item or "count" not in item:
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        topics.append(PulseTopic(name=_text(item["name"], max_len=80), count=_int(item["count"], min_v=0)))
    return Pulse(
        clusters=clusters,
        articles=articles,
        zh_en=_clean_str(value["zhEn"], min_len=1, max_len=32),
        healthy=healthy,
        total_sources=total_sources,
        topics=tuple(topics),
    )


def _lede(value: Any) -> tuple[Text, ...]:
    if not isinstance(value, list) or len(value) > 20:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return tuple(_text(item, max_len=400) for item in value)


def parse_briefing_create(payload: dict[str, Any]) -> dict[str, Any]:
    _unknown(payload, BRIEFING_POST)
    for key in ("date", "title", "moreHeading", "lede", "pulse", "updatedAt"):
        if key not in payload:
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    day = _date(payload["date"])
    weekday = _text(payload["weekday"], max_len=16) if "weekday" in payload else weekday_for(day)
    return {
        "date": day,
        "weekday": weekday,
        "title": _text(payload["title"], max_len=200),
        "more_heading": _text(payload["moreHeading"], max_len=80),
        "lede": _lede(payload["lede"]),
        "pulse": _pulse(payload["pulse"]),
        "published_at": combine_hhmm(day, _hhmm(payload["updatedAt"])),
    }


def parse_briefing_patch(payload: dict[str, Any], current: Briefing) -> dict[str, Any]:
    _unknown(payload, BRIEFING_PATCH)
    if "date" in payload:
        incoming = payload["date"]
        if not isinstance(incoming, str) or incoming != current.date.isoformat():
            raise AppError(422, "VALIDATION_ERROR", "Date cannot be changed.")
    out: dict[str, Any] = {}
    if "weekday" in payload:
        out["weekday"] = _text(payload["weekday"], max_len=16)
    if "title" in payload:
        out["title"] = _text(payload["title"], max_len=200)
    if "moreHeading" in payload:
        out["more_heading"] = _text(payload["moreHeading"], max_len=80)
    if "lede" in payload:
        out["lede"] = _lede(payload["lede"])
    if "pulse" in payload:
        out["pulse"] = _pulse(payload["pulse"])
    if "updatedAt" in payload:
        out["published_at"] = combine_hhmm(current.date, _hhmm(payload["updatedAt"]))
    return out


def _citations(value: Any, day: date) -> tuple[Citation, ...]:
    if not isinstance(value, list) or len(value) > 40:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    out: list[Citation] = []
    for item in value:
        if not isinstance(item, dict):
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        allowed = {"name", "lang", "kind", "time", "sourceCode"}
        if set(item) - allowed:
            raise AppError(422, "VALIDATION_ERROR", "Unknown field.")
        for key in ("name", "lang", "kind", "time"):
            if key not in item:
                raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        lang = item["lang"]
        if lang not in {"zh", "en"}:
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        source_code = None
        if "sourceCode" in item and item["sourceCode"] is not None:
            source_code = _slug(item["sourceCode"], max_len=64)
        out.append(
            Citation(
                name=_clean_str(item["name"], min_len=1, max_len=120),
                lang=lang,
                kind=_text(item["kind"], max_len=32),
                cited_at=combine_hhmm(day, _hhmm(item["time"])),
                source_code=source_code,
            )
        )
    return tuple(out)


def _timeline(value: Any, day: date) -> tuple[TimelineItem, ...]:
    if not isinstance(value, list) or len(value) > 40:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    out: list[TimelineItem] = []
    for item in value:
        if not isinstance(item, dict):
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        if set(item) - {"time", "text"}:
            raise AppError(422, "VALIDATION_ERROR", "Unknown field.")
        if "time" not in item or "text" not in item:
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        out.append(TimelineItem(occurred_at=combine_hhmm(day, _hhmm(item["time"])), text=_text(item["text"], max_len=400)))
    return tuple(out)


def _synthesis(value: Any) -> tuple[Text, ...]:
    if not isinstance(value, list) or len(value) > 40:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return tuple(_text(item, max_len=2000) for item in value)


def parse_story_write(payload: dict[str, Any], *, creating: bool, current_slug: str | None = None) -> dict[str, Any]:
    allowed = STORY_POST if creating else STORY_PATCH
    _unknown(payload, allowed)
    if creating:
        for key in ("slug", "date", "topicSlug", "section", "title", "dek", "synthesis", "timeline", "sources"):
            if key not in payload:
                raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        slug = _slug(payload["slug"], max_len=80)
    else:
        if "slug" in payload:
            if not isinstance(payload["slug"], str) or payload["slug"] != current_slug:
                raise AppError(422, "VALIDATION_ERROR", "Slug cannot be changed.")
        slug = current_slug or ""
        for key in ("date", "topicSlug", "section", "title", "dek", "synthesis", "timeline", "sources"):
            if key not in payload:
                raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    section = payload["section"]
    if section not in {"must", "more"}:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    rank = None
    if section == "must":
        if "rank" not in payload:
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        rank = _int(payload["rank"], min_v=1, max_v=10_000)
    day = _date(payload["date"])
    return {
        "slug": slug,
        "date": day,
        "topic_slug": _slug(payload["topicSlug"], max_len=64),
        "section": section,
        "rank": rank,
        "title": _text(payload["title"], max_len=200),
        "dek": _text(payload["dek"], max_len=400),
        "synthesis": _synthesis(payload["synthesis"]),
        "timeline": _timeline(payload["timeline"], day),
        "sources": _citations(payload["sources"], day),
    }


class AdminUseCases:
    def __init__(
        self,
        catalog: AdminCatalogRepository,
        editorial: AdminEditorialRepository,
        identity: IdentityRepository,
    ) -> None:
        self.catalog = catalog
        self.editorial = editorial
        self.identity = identity

    async def _audit(self, admin: AdminUser, action: str, resource: str, ip: str | None, ua: str | None, metadata: dict[str, Any]) -> None:
        await self.identity.insert_audit(admin.id, action, resource, ip, ua, metadata)

    async def list_topics(self):
        return await self.catalog.list_topics()

    async def get_topic(self, slug: str):
        found = await self.catalog.get_topic(slug)
        if found is None:
            raise AppError(404, "NOT_FOUND", "Unknown topic.")
        return found

    async def create_topic(self, payload: dict[str, Any], admin: AdminUser, ip: str | None, ua: str | None):
        data = parse_topic_create(payload)
        if await self.catalog.get_topic(data["slug"]) is not None:
            raise AppError(409, "CONFLICT", "Topic slug already exists.")
        topic = await self.catalog.create_topic(data["slug"], data["name"], data["blurb"], data["sort_order"])
        await self._audit(admin, "topic.create", f"topics/{topic.slug}", ip, ua, {"slug": topic.slug})
        return topic

    async def update_topic(self, slug: str, payload: dict[str, Any], admin: AdminUser, ip: str | None, ua: str | None):
        current = await self.get_topic(slug)
        data = parse_topic_patch(payload, current.slug)
        topic = await self.catalog.update_topic(
            slug,
            data.get("name"),
            data.get("blurb"),
            data.get("sort_order"),
            data.get("is_active"),
        )
        await self._audit(admin, "topic.update", f"topics/{slug}", ip, ua, {"fields": sorted(data)})
        return topic

    async def delete_topic(self, slug: str, admin: AdminUser, ip: str | None, ua: str | None):
        await self.get_topic(slug)
        await self.catalog.delete_topic(slug)
        await self._audit(admin, "topic.delete", f"topics/{slug}", ip, ua, {"slug": slug})

    async def list_sources(self):
        return await self.catalog.list_sources()

    async def get_source(self, code: str):
        found = await self.catalog.get_source(code)
        if found is None:
            raise AppError(404, "NOT_FOUND", "Unknown source.")
        return found

    async def create_source(self, payload: dict[str, Any], admin: AdminUser, ip: str | None, ua: str | None):
        source = parse_source_create(payload)
        if await self.catalog.get_source(source.code) is not None:
            raise AppError(409, "CONFLICT", "Source code already exists.")
        created = await self.catalog.create_source(source)
        await self._audit(admin, "source.create", f"sources/{created.code}", ip, ua, {"code": created.code})
        return created

    async def update_source(self, code: str, payload: dict[str, Any], admin: AdminUser, ip: str | None, ua: str | None):
        current = await self.get_source(code)
        updated = parse_source_patch(payload, current)
        saved = await self.catalog.update_source(code, updated)
        await self._audit(admin, "source.update", f"sources/{code}", ip, ua, {"code": code})
        return saved

    async def delete_source(self, code: str, admin: AdminUser, ip: str | None, ua: str | None):
        await self.get_source(code)
        await self.catalog.delete_source(code)
        await self._audit(admin, "source.delete", f"sources/{code}", ip, ua, {"code": code})

    async def list_briefings(self, start: date, end: date):
        return await self.editorial.list_briefings(start, end)

    async def get_briefing(self, day: date):
        found = await self.editorial.get_briefing(day)
        if found is None:
            raise AppError(404, "NOT_FOUND", "No briefing for this date.")
        return found

    async def create_briefing(self, payload: dict[str, Any], admin: AdminUser, ip: str | None, ua: str | None):
        data = parse_briefing_create(payload)
        if await self.editorial.get_briefing(data["date"]) is not None:
            raise AppError(409, "CONFLICT", "Briefing date already exists.")
        created = await self.editorial.create_briefing(
            data["date"],
            data["weekday"],
            data["title"],
            data["more_heading"],
            data["lede"],
            data["pulse"],
            data["published_at"],
        )
        await self._audit(admin, "briefing.create", f"briefings/{created.date.isoformat()}", ip, ua, {"date": created.date.isoformat()})
        return created

    async def update_briefing(self, day: date, payload: dict[str, Any], admin: AdminUser, ip: str | None, ua: str | None):
        current = await self.get_briefing(day)
        data = parse_briefing_patch(payload, current)
        updated = await self.editorial.update_briefing(
            day,
            data.get("weekday"),
            data.get("title"),
            data.get("more_heading"),
            data.get("lede"),
            data.get("pulse"),
            data.get("published_at"),
        )
        await self._audit(admin, "briefing.update", f"briefings/{day.isoformat()}", ip, ua, {"date": day.isoformat()})
        return updated

    async def publish(self, day: date, admin: AdminUser, ip: str | None, ua: str | None):
        await self.get_briefing(day)
        updated = await self.editorial.set_briefing_status(day, "published")
        await self._audit(admin, "briefing.publish", f"briefings/{day.isoformat()}", ip, ua, {"date": day.isoformat()})
        return updated

    async def unpublish(self, day: date, admin: AdminUser, ip: str | None, ua: str | None):
        await self.get_briefing(day)
        updated = await self.editorial.set_briefing_status(day, "draft")
        await self._audit(admin, "briefing.unpublish", f"briefings/{day.isoformat()}", ip, ua, {"date": day.isoformat()})
        return updated

    async def delete_briefing(self, day: date, admin: AdminUser, ip: str | None, ua: str | None):
        current = await self.get_briefing(day)
        if current.status == "published":
            raise AppError(409, "CONFLICT", "Cannot delete a published briefing.")
        await self.editorial.delete_briefing(day)
        await self._audit(admin, "briefing.delete", f"briefings/{day.isoformat()}", ip, ua, {"date": day.isoformat()})

    async def list_stories(self, day: date | None, topic_slug: str | None):
        if topic_slug is not None and await self.catalog.get_topic(topic_slug) is None:
            return []
        return await self.editorial.list_stories(day, topic_slug)

    async def get_story(self, slug: str):
        found = await self.editorial.get_story(slug)
        if found is None:
            raise AppError(404, "NOT_FOUND", "Unknown cluster.")
        return found

    async def _story_from_parsed(self, data: dict[str, Any]) -> Story:
        briefing = await self.editorial.get_briefing(data["date"])
        if briefing is None:
            raise AppError(422, "VALIDATION_ERROR", "Unknown briefing.")
        topic = await self.catalog.get_topic(data["topic_slug"])
        if topic is None:
            raise AppError(422, "VALIDATION_ERROR", "Unknown topic.")
        for citation in data["sources"]:
            if citation.source_code is not None and await self.catalog.get_source(citation.source_code) is None:
                raise AppError(422, "VALIDATION_ERROR", "Unknown source.")
        return Story(
            slug=data["slug"],
            date=data["date"],
            topic_slug=topic.slug,
            rank=data["rank"],
            section=data["section"],
            title=data["title"],
            dek=data["dek"],
            topic=TopicRef(slug=topic.slug, name=topic.name),
            synthesis=data["synthesis"],
            timeline=data["timeline"],
            sources=data["sources"],
        )

    async def create_story(self, payload: dict[str, Any], admin: AdminUser, ip: str | None, ua: str | None):
        data = parse_story_write(payload, creating=True)
        if await self.editorial.get_story(data["slug"]) is not None:
            raise AppError(409, "CONFLICT", "Story slug already exists.")
        story = await self._story_from_parsed(data)
        created = await self.editorial.create_story(story)
        await self._audit(admin, "story.create", f"stories/{created.slug}", ip, ua, {"slug": created.slug})
        return created

    async def update_story(self, slug: str, payload: dict[str, Any], admin: AdminUser, ip: str | None, ua: str | None):
        await self.get_story(slug)
        data = parse_story_write(payload, creating=False, current_slug=slug)
        story = await self._story_from_parsed(data)
        updated = await self.editorial.update_story(slug, story)
        await self._audit(admin, "story.update", f"stories/{slug}", ip, ua, {"slug": slug})
        return updated

    async def delete_story(self, slug: str, admin: AdminUser, ip: str | None, ua: str | None):
        await self.get_story(slug)
        await self.editorial.delete_story(slug)
        await self._audit(admin, "story.delete", f"stories/{slug}", ip, ua, {"slug": slug})

    async def list_audits(self, limit: int):
        return await self.identity.list_audits(limit)
