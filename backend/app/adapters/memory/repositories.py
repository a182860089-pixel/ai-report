from __future__ import annotations

import json
from datetime import date, datetime, timezone
from ipaddress import ip_address
from pathlib import Path
from typing import Any
import asyncio

from app.application.timefmt import SHANGHAI, combine_hhmm
from app.domain.entities import (
    AdminUser,
    Article,
    AuditEntry,
    ClusterJob,
    Briefing,
    BriefingListItem,
    Citation,
    FetchRun,
    ParsedArticle,
    Pulse,
    PulseTopic,
    RefreshRecord,
    Source,
    Story,
    StorySummary,
    Text,
    TimelineItem,
    Topic,
    TopicRef,
)
from app.domain.exceptions import AppError
from app.domain.interfaces import (
    AdminCatalogRepository,
    AdminEditorialRepository,
    CatalogRepository,
    EditorialRepository,
    HealthRepository,
    IdentityRepository,
    PipelineRepository,
)

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
SEED_DAY = date(2026, 9, 14)


def _text(value: dict[str, str]) -> Text:
    return Text(zh=value["zh"], en=value["en"])


def _safe_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        ip_address(ip)
        return ip
    except ValueError:
        return None


def _clip(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


def _summary_of(story: Story) -> StorySummary:
    return StorySummary(
        slug=story.slug,
        date=story.date,
        topic_slug=story.topic_slug,
        rank=story.rank,
        section=story.section,
        title=story.title,
        dek=story.dek,
        topic=story.topic,
        source_count=len(story.sources),
        source_names=tuple(src.name for src in story.sources[:3]),
    )


def _haystack(story: Story, topic_name: Text) -> str:
    return " ".join(
        [
            story.slug,
            story.title.zh,
            story.title.en,
            story.dek.zh,
            story.dek.en,
            *[item.zh for item in story.synthesis],
            *[item.en for item in story.synthesis],
            *[item.name for item in story.sources],
            topic_name.zh,
            topic_name.en,
        ]
    ).lower()


def _story_sort_key(rec: dict[str, Any]) -> tuple:
    summary: StorySummary = rec["summary"]
    return (
        -summary.date.toordinal(),
        0 if summary.section == "must" else 1,
        summary.rank if summary.rank is not None else 10**9,
        rec["id"],
    )


class MemoryWorld:
    def __init__(self, fixtures_dir: Path | None = None) -> None:
        root = fixtures_dir or FIXTURES
        topics_raw = json.loads((root / "topics.json").read_text(encoding="utf-8"))
        sources_raw = json.loads((root / "sources.json").read_text(encoding="utf-8"))
        briefings_raw = json.loads((root / "briefings.json").read_text(encoding="utf-8"))
        stories_raw = json.loads((root / "stories.json").read_text(encoding="utf-8"))

        self.topic_rows: list[dict[str, Any]] = []
        self.topic_by_slug: dict[str, dict[str, Any]] = {}
        for index, row in enumerate(topics_raw, start=1):
            item = {
                "id": index,
                "slug": row["slug"],
                "name": _text(row["name"]),
                "blurb": _text(row["blurb"]),
                "sort_order": index - 1,
                "is_active": True,
            }
            self.topic_rows.append(item)
            self.topic_by_slug[item["slug"]] = item

        self.sources: list[Source] = []
        self.source_by_code: dict[str, Source] = {}
        for row in sources_raw:
            last_fetch = None
            if row.get("lastFetch") and row["lastFetch"] != "\u2014":
                last_fetch = combine_hhmm(SEED_DAY, row["lastFetch"])
            is_lab = row["id"] == "lab-rss"
            source = Source(
                code=row["id"],
                name=row["name"],
                status=row["status"],
                last_fetch_at=None if is_lab else last_fetch,
                today_count=int(row["todayCount"]),
                detail=_text(row["detail"]),
                consecutive_failures=2 if is_lab else 0,
                is_quarantined=is_lab,
                homepage_url=row.get("homepageUrl"),
                feed_url=row.get("feedUrl"),
            )
            self.sources.append(source)
            self.source_by_code[source.code] = source
        name_to_code = {item.name: item.code for item in self.sources}

        self.story_records: list[dict[str, Any]] = []
        self.summary_by_slug: dict[str, StorySummary] = {}
        self.story_by_slug: dict[str, Story] = {}
        self.status_by_date: dict[date, str] = {}
        self.briefings: dict[date, Briefing] = {}
        self.list_items: dict[date, BriefingListItem] = {}

        stories_by_date: dict[date, list[dict[str, Any]]] = {}
        for index, row in enumerate(stories_raw, start=1):
            day = date.fromisoformat(row["date"])
            topic = self.topic_by_slug[row["topicSlug"]]
            topic_ref = TopicRef(slug=topic["slug"], name=topic["name"])
            citations = tuple(
                Citation(
                    name=src["name"],
                    lang=src["lang"],
                    kind=_text(src["kind"]),
                    cited_at=combine_hhmm(day, src["time"]),
                    source_code=name_to_code.get(src["name"]),
                )
                for src in row["sources"]
            )
            synthesis = tuple(_text(item) for item in row["synthesis"])
            timeline = tuple(
                TimelineItem(occurred_at=combine_hhmm(day, item["time"]), text=_text(item["text"]))
                for item in row["timeline"]
            )
            rank = row.get("rank")
            section = row["section"]
            if section == "more" or rank in (0, None):
                rank = None
            story = Story(
                slug=row["slug"],
                date=day,
                topic_slug=topic["slug"],
                rank=rank,
                section=section,
                title=_text(row["title"]),
                dek=_text(row["dek"]),
                topic=topic_ref,
                synthesis=synthesis,
                timeline=timeline,
                sources=citations,
            )
            summary = _summary_of(story)
            record = {
                "id": index,
                "summary": summary,
                "story": story,
                "haystack": _haystack(story, topic["name"]),
            }
            self.story_records.append(record)
            self.summary_by_slug[story.slug] = summary
            self.story_by_slug[story.slug] = story
            stories_by_date.setdefault(day, []).append(record)

        for row in briefings_raw:
            day = date.fromisoformat(row["date"])
            published_at = combine_hhmm(day, row["updatedAt"])
            pulse_raw = row["pulse"]
            pulse = Pulse(
                clusters=int(pulse_raw["clusters"]),
                articles=int(pulse_raw["articles"]),
                zh_en=pulse_raw["zhEn"],
                healthy=int(pulse_raw["healthy"]),
                total_sources=int(pulse_raw["totalSources"]),
                topics=tuple(
                    PulseTopic(name=_text(item["name"]), count=int(item["count"]))
                    for item in pulse_raw["topics"]
                ),
            )
            briefing = Briefing(
                date=day,
                weekday=_text(row["weekday"]),
                published_at=published_at,
                title=_text(row["title"]),
                lede=tuple(_text(item) for item in row["lede"]),
                more_heading=_text(row["moreHeading"]),
                pulse=pulse,
                must_read=(),
                more=(),
                status="published",
            )
            self.briefings[day] = briefing
            self.status_by_date[day] = "published"
            self.list_items[day] = BriefingListItem(
                date=day,
                weekday=briefing.weekday,
                title=briefing.title,
                published_at=published_at,
                must_read_count=0,
                clusters=pulse.clusters,
                status="published",
            )

        self.next_story_id = len(self.story_records) + 1
        self.next_topic_id = len(self.topic_rows) + 1
        self.fetch_runs: list[FetchRun] = []
        self.raw_payloads: dict[int, dict[str, str | None]] = {}
        self.articles: list[dict[str, Any]] = []
        self.cluster_jobs: list[ClusterJob] = []
        self.next_fetch_run_id = 1
        self.next_article_id = 1
        self.next_cluster_job_id = 1
        self._lock: asyncio.Lock | None = None
        for day in list(self.briefings):
            self.rebuild_day(day)

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def published_records(self) -> list[dict[str, Any]]:
        return [
            rec
            for rec in self.story_records
            if self.status_by_date.get(rec["summary"].date) == "published"
        ]

    def rebuild_day(self, day: date) -> None:
        briefing = self.briefings.get(day)
        if briefing is None:
            return
        day_recs = [rec for rec in self.story_records if rec["summary"].date == day]
        must = sorted(
            [rec for rec in day_recs if rec["summary"].section == "must"],
            key=lambda rec: rec["summary"].rank or 0,
        )
        more = sorted(
            [rec for rec in day_recs if rec["summary"].section == "more"],
            key=lambda rec: rec["id"],
        )
        status = self.status_by_date.get(day, briefing.status)
        updated = Briefing(
            date=briefing.date,
            weekday=briefing.weekday,
            published_at=briefing.published_at,
            title=briefing.title,
            lede=briefing.lede,
            more_heading=briefing.more_heading,
            pulse=briefing.pulse,
            must_read=tuple(rec["summary"] for rec in must),
            more=tuple(rec["summary"] for rec in more),
            status=status,
        )
        self.briefings[day] = updated
        self.list_items[day] = BriefingListItem(
            date=updated.date,
            weekday=updated.weekday,
            title=updated.title,
            published_at=updated.published_at,
            must_read_count=len(must),
            clusters=updated.pulse.clusters,
            status=status,
        )

    def refresh_topic_refs(self, slug: str) -> None:
        topic = self.topic_by_slug[slug]
        topic_ref = TopicRef(slug=topic["slug"], name=topic["name"])
        affected: set[date] = set()
        for rec in self.story_records:
            if rec["summary"].topic_slug != slug:
                continue
            story: Story = rec["story"]
            updated = Story(
                slug=story.slug,
                date=story.date,
                topic_slug=slug,
                rank=story.rank,
                section=story.section,
                title=story.title,
                dek=story.dek,
                topic=topic_ref,
                synthesis=story.synthesis,
                timeline=story.timeline,
                sources=story.sources,
            )
            summary = _summary_of(updated)
            rec["story"] = updated
            rec["summary"] = summary
            rec["haystack"] = _haystack(updated, topic["name"])
            self.story_by_slug[updated.slug] = updated
            self.summary_by_slug[updated.slug] = summary
            affected.add(updated.date)
        for day in affected:
            self.rebuild_day(day)

    def put_story(self, story: Story, record_id: int | None = None) -> dict[str, Any]:
        topic = self.topic_by_slug[story.topic_slug]
        summary = _summary_of(story)
        rec = {
            "id": record_id or self.next_story_id,
            "summary": summary,
            "story": story,
            "haystack": _haystack(story, topic["name"]),
        }
        if record_id is None:
            self.next_story_id += 1
        self.story_records.append(rec)
        self.summary_by_slug[story.slug] = summary
        self.story_by_slug[story.slug] = story
        return rec

    def drop_story(self, slug: str) -> dict[str, Any] | None:
        rec = next((item for item in self.story_records if item["story"].slug == slug), None)
        if rec is None:
            return None
        self.story_records.remove(rec)
        self.summary_by_slug.pop(slug, None)
        self.story_by_slug.pop(slug, None)
        return rec

    def add_draft_briefing(self, day: date) -> None:
        published_at = combine_hhmm(day, "07:00")
        title = Text(zh="draft", en="draft")
        weekday = Text(zh="x", en="x")
        pulse = Pulse(1, 1, "1 : 1", 1, 1, ())
        self.status_by_date[day] = "draft"
        self.briefings[day] = Briefing(
            day, weekday, published_at, title, (), Text("m", "m"), pulse, (), (), status="draft"
        )
        self.list_items[day] = BriefingListItem(day, weekday, title, published_at, 0, 1, status="draft")
        topic = self.topic_rows[0]
        topic_ref = TopicRef(slug=topic["slug"], name=topic["name"])
        story = Story(
            slug=f"draft-{day.isoformat()}",
            date=day,
            topic_slug=topic["slug"],
            rank=1,
            section="must",
            title=title,
            dek=title,
            topic=topic_ref,
            synthesis=(),
            timeline=(),
            sources=(),
        )
        self.put_story(story)
        self.rebuild_day(day)


class MemoryEditorialRepository(EditorialRepository):
    def __init__(self, world: MemoryWorld) -> None:
        self.world = world

    async def get_current_date(self) -> date | None:
        published = [day for day, status in self.world.status_by_date.items() if status == "published"]
        return max(published) if published else None

    async def get_published_briefing(self, day: date) -> Briefing | None:
        if self.world.status_by_date.get(day) != "published":
            return None
        return self.world.briefings.get(day)

    async def list_published_briefings(self, start: date, end: date) -> list[BriefingListItem]:
        return [
            self.world.list_items[day]
            for day in sorted(self.world.list_items)
            if start <= day <= end and self.world.status_by_date.get(day) == "published"
        ]

    async def get_published_story(self, slug: str) -> Story | None:
        rec = next((item for item in self.world.story_records if item["story"].slug == slug), None)
        if rec is None:
            return None
        if self.world.status_by_date.get(rec["summary"].date) != "published":
            return None
        return rec["story"]

    async def search_published_stories(self, query: str) -> list[StorySummary]:
        needle = query.lower()
        hits = [rec for rec in self.world.published_records() if needle in rec["haystack"]]
        hits.sort(key=_story_sort_key)
        return [rec["summary"] for rec in hits]


class MemoryCatalogRepository(CatalogRepository):
    def __init__(self, world: MemoryWorld) -> None:
        self.world = world

    def _count(self, slug: str) -> int:
        return sum(1 for rec in self.world.published_records() if rec["summary"].topic_slug == slug)

    async def list_active_topics(self) -> list[Topic]:
        rows = sorted(
            [row for row in self.world.topic_rows if row["is_active"]],
            key=lambda row: (row["sort_order"], row["id"]),
        )
        return [
            Topic(
                slug=row["slug"],
                name=row["name"],
                blurb=row["blurb"],
                cluster_count=self._count(row["slug"]),
                sort_order=row["sort_order"],
                is_active=row["is_active"],
            )
            for row in rows
        ]

    async def get_active_topic_with_stories(self, slug: str) -> Topic | None:
        row = self.world.topic_by_slug.get(slug)
        if row is None or not row["is_active"]:
            return None
        recs = [item for item in self.world.published_records() if item["summary"].topic_slug == slug]
        recs.sort(key=_story_sort_key)
        return Topic(
            slug=row["slug"],
            name=row["name"],
            blurb=row["blurb"],
            cluster_count=len(recs),
            stories=tuple(item["summary"] for item in recs),
            sort_order=row["sort_order"],
            is_active=row["is_active"],
        )

    async def list_sources(self) -> list[Source]:
        return list(self.world.sources)


class MemoryIdentityRepository(IdentityRepository):
    def __init__(self) -> None:
        self.admins: dict[int, AdminUser] = {}
        self.email_index: dict[str, int] = {}
        self.refresh: dict[str, RefreshRecord] = {}
        self.audits: list[dict[str, Any]] = []
        self._admin_id = 1
        self._refresh_id = 1
        self._audit_id = 1

    def add_admin(self, email: str, password_hash: str, is_active: bool = True) -> AdminUser:
        admin = AdminUser(id=self._admin_id, email=email.lower(), password_hash=password_hash, is_active=is_active)
        self.admins[admin.id] = admin
        self.email_index[admin.email] = admin.id
        self._admin_id += 1
        return admin

    def set_active(self, admin_id: int, is_active: bool) -> None:
        admin = self.admins[admin_id]
        self.admins[admin_id] = AdminUser(admin.id, admin.email, admin.password_hash, is_active)

    async def get_admin_by_email(self, email: str) -> AdminUser | None:
        admin_id = self.email_index.get(email.lower())
        return None if admin_id is None else self.admins[admin_id]

    async def get_admin_by_id(self, admin_id: int) -> AdminUser | None:
        return self.admins.get(admin_id)

    async def update_last_login(self, admin_id: int, at: datetime) -> None:
        return None

    async def insert_refresh(
        self,
        admin_user_id: int,
        token_hash: str,
        expires_at: datetime,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        record = RefreshRecord(
            id=self._refresh_id,
            admin_user_id=admin_user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )
        self._refresh_id += 1
        self.refresh[token_hash] = record
        _ = (_safe_ip(ip), _clip(user_agent, 300))

    async def get_refresh_by_hash(self, token_hash: str) -> RefreshRecord | None:
        return self.refresh.get(token_hash)

    async def revoke_refresh(self, token_hash: str, at: datetime) -> None:
        record = self.refresh.get(token_hash)
        if record is None:
            return
        self.refresh[token_hash] = RefreshRecord(
            record.id, record.admin_user_id, record.token_hash, record.expires_at, at
        )

    async def revoke_all_refresh(self, admin_user_id: int, at: datetime) -> None:
        for token_hash, record in list(self.refresh.items()):
            if record.admin_user_id == admin_user_id and record.revoked_at is None:
                self.refresh[token_hash] = RefreshRecord(
                    record.id, record.admin_user_id, record.token_hash, record.expires_at, at
                )

    async def insert_audit(
        self,
        actor_id: int | None,
        action: str,
        resource: str,
        ip: str | None,
        user_agent: str | None,
        metadata: dict[str, Any],
    ) -> None:
        email = None
        if actor_id is not None:
            admin = self.admins.get(actor_id)
            email = admin.email if admin is not None else None
        self.audits.append(
            {
                "id": self._audit_id,
                "actor_id": actor_id,
                "actor_email": email,
                "action": action,
                "resource": resource,
                "ip": _safe_ip(ip),
                "user_agent": _clip(user_agent, 300),
                "metadata": metadata,
                "created_at": datetime.now(timezone.utc),
            }
        )
        self._audit_id += 1

    async def list_audits(self, limit: int) -> list[AuditEntry]:
        rows = sorted(self.audits, key=lambda item: item["id"], reverse=True)[:limit]
        return [
            AuditEntry(
                action=row["action"],
                resource=row["resource"],
                created_at=row["created_at"],
                metadata=row["metadata"],
                actor_email=row["actor_email"],
            )
            for row in rows
        ]


class MemoryHealthRepository(HealthRepository):
    async def ping(self) -> bool:
        return True


class MemoryAdminCatalogRepository(AdminCatalogRepository):
    def __init__(self, world: MemoryWorld) -> None:
        self.world = world

    def _topic(self, row: dict[str, Any], *, with_stories: bool) -> Topic:
        recs = [item for item in self.world.story_records if item["summary"].topic_slug == row["slug"]]
        recs.sort(key=_story_sort_key)
        return Topic(
            slug=row["slug"],
            name=row["name"],
            blurb=row["blurb"],
            cluster_count=len(recs),
            stories=tuple(item["summary"] for item in recs) if with_stories else (),
            sort_order=row["sort_order"],
            is_active=row["is_active"],
        )

    async def list_topics(self) -> list[Topic]:
        rows = sorted(self.world.topic_rows, key=lambda row: (row["sort_order"], row["id"]))
        return [self._topic(row, with_stories=False) for row in rows]

    async def get_topic(self, slug: str) -> Topic | None:
        row = self.world.topic_by_slug.get(slug)
        if row is None:
            return None
        return self._topic(row, with_stories=True)

    async def create_topic(self, slug: str, name: Text, blurb: Text, sort_order: int) -> Topic:
        item = {
            "id": self.world.next_topic_id,
            "slug": slug,
            "name": name,
            "blurb": blurb,
            "sort_order": sort_order,
            "is_active": True,
        }
        self.world.next_topic_id += 1
        self.world.topic_rows.append(item)
        self.world.topic_by_slug[slug] = item
        return self._topic(item, with_stories=False)

    async def update_topic(
        self,
        slug: str,
        name: Text | None,
        blurb: Text | None,
        sort_order: int | None,
        is_active: bool | None,
    ) -> Topic:
        row = self.world.topic_by_slug[slug]
        if name is not None:
            row["name"] = name
        if blurb is not None:
            row["blurb"] = blurb
        if sort_order is not None:
            row["sort_order"] = sort_order
        if is_active is not None:
            row["is_active"] = is_active
        if name is not None:
            self.world.refresh_topic_refs(slug)
        return self._topic(row, with_stories=True)

    async def delete_topic(self, slug: str) -> None:
        if any(rec["summary"].topic_slug == slug for rec in self.world.story_records):
            raise AppError(409, "CONFLICT", "Topic still has stories.")
        row = self.world.topic_by_slug.pop(slug)
        self.world.topic_rows.remove(row)

    async def list_sources(self) -> list[Source]:
        return list(self.world.sources)

    async def get_source(self, code: str) -> Source | None:
        return self.world.source_by_code.get(code)

    async def create_source(self, source: Source) -> Source:
        self.world.sources.append(source)
        self.world.source_by_code[source.code] = source
        return source

    async def update_source(self, code: str, source: Source) -> Source:
        for index, item in enumerate(self.world.sources):
            if item.code == code:
                self.world.sources[index] = source
                break
        self.world.source_by_code[code] = source
        return source

    async def delete_source(self, code: str) -> None:
        if any(item["source_code"] == code for item in self.world.articles):
            raise AppError(409, "CONFLICT", "Source still has articles.")
        cited = any(
            citation.source_code == code
            for rec in self.world.story_records
            for citation in rec["story"].sources
        )
        if cited:
            raise AppError(409, "CONFLICT", "Source still has citations.")
        self.world.sources = [item for item in self.world.sources if item.code != code]
        self.world.source_by_code.pop(code, None)


class MemoryAdminEditorialRepository(AdminEditorialRepository):
    def __init__(self, world: MemoryWorld) -> None:
        self.world = world

    async def list_briefings(self, start: date, end: date) -> list[BriefingListItem]:
        return [
            self.world.list_items[day]
            for day in sorted(self.world.list_items)
            if start <= day <= end
        ]

    async def get_briefing(self, day: date) -> Briefing | None:
        return self.world.briefings.get(day)

    async def create_briefing(
        self,
        day: date,
        weekday: Text,
        title: Text,
        more_heading: Text,
        lede: tuple[Text, ...],
        pulse: Pulse,
        published_at: datetime,
    ) -> Briefing:
        briefing = Briefing(
            date=day,
            weekday=weekday,
            published_at=published_at,
            title=title,
            lede=lede,
            more_heading=more_heading,
            pulse=pulse,
            must_read=(),
            more=(),
            status="draft",
        )
        self.world.status_by_date[day] = "draft"
        self.world.briefings[day] = briefing
        self.world.rebuild_day(day)
        return self.world.briefings[day]

    async def update_briefing(
        self,
        day: date,
        weekday: Text | None,
        title: Text | None,
        more_heading: Text | None,
        lede: tuple[Text, ...] | None,
        pulse: Pulse | None,
        published_at: datetime | None,
    ) -> Briefing:
        current = self.world.briefings[day]
        updated = Briefing(
            date=current.date,
            weekday=weekday if weekday is not None else current.weekday,
            published_at=published_at if published_at is not None else current.published_at,
            title=title if title is not None else current.title,
            lede=lede if lede is not None else current.lede,
            more_heading=more_heading if more_heading is not None else current.more_heading,
            pulse=pulse if pulse is not None else current.pulse,
            must_read=current.must_read,
            more=current.more,
            status=current.status,
        )
        self.world.briefings[day] = updated
        self.world.rebuild_day(day)
        return self.world.briefings[day]

    async def set_briefing_status(self, day: date, status: str) -> Briefing:
        self.world.status_by_date[day] = status
        current = self.world.briefings[day]
        self.world.briefings[day] = Briefing(
            date=current.date,
            weekday=current.weekday,
            published_at=current.published_at,
            title=current.title,
            lede=current.lede,
            more_heading=current.more_heading,
            pulse=current.pulse,
            must_read=current.must_read,
            more=current.more,
            status=status,
        )
        self.world.rebuild_day(day)
        return self.world.briefings[day]

    async def delete_briefing(self, day: date) -> None:
        remaining = []
        for rec in self.world.story_records:
            if rec["summary"].date == day:
                self.world.summary_by_slug.pop(rec["story"].slug, None)
                self.world.story_by_slug.pop(rec["story"].slug, None)
            else:
                remaining.append(rec)
        self.world.story_records = remaining
        self.world.briefings.pop(day, None)
        self.world.list_items.pop(day, None)
        self.world.status_by_date.pop(day, None)

    async def list_stories(self, day: date | None, topic_slug: str | None) -> list[StorySummary]:
        recs = list(self.world.story_records)
        if day is not None:
            recs = [item for item in recs if item["summary"].date == day]
        if topic_slug is not None:
            recs = [item for item in recs if item["summary"].topic_slug == topic_slug]
        recs.sort(key=_story_sort_key)
        return [item["summary"] for item in recs]

    async def get_story(self, slug: str) -> Story | None:
        return self.world.story_by_slug.get(slug)

    async def create_story(self, story: Story) -> Story:
        self.world.put_story(story)
        self.world.rebuild_day(story.date)
        return self.world.story_by_slug[story.slug]

    async def update_story(self, slug: str, story: Story) -> Story:
        old = self.world.drop_story(slug)
        old_id = old["id"] if old is not None else None
        old_date = old["summary"].date if old is not None else story.date
        self.world.put_story(story, record_id=old_id)
        self.world.rebuild_day(old_date)
        if story.date != old_date:
            self.world.rebuild_day(story.date)
        return self.world.story_by_slug[story.slug]

    async def delete_story(self, slug: str) -> None:
        rec = self.world.drop_story(slug)
        if rec is not None:
            self.world.rebuild_day(rec["summary"].date)



class MemoryPipelineRepository(PipelineRepository):
    def __init__(self, world: MemoryWorld, identity: IdentityRepository) -> None:
        self.world = world
        self.identity = identity

    def _source_name(self, code: str) -> str:
        source = self.world.source_by_code.get(code)
        return source.name if source is not None else code

    def _article(self, row: dict[str, Any]) -> Article:
        return Article(
            source_code=row["source_code"],
            guid=row["guid"],
            canonical_url=row["canonical_url"],
            title=row["title"],
            summary=row["summary"],
            lang=row["lang"],
            published_at=row["published_at"],
            fetched_at=row["fetched_at"],
            cluster_job_id=row["cluster_job_id"],
            id=row["id"],
            source_name=self._source_name(row["source_code"]),
        )

    async def start_fetch_run(self, source_code: str, feed_url: str, started_at: datetime) -> FetchRun:
        async with self.world.lock:
            assert source_code in self.world.source_by_code
            run_id = self.world.next_fetch_run_id
            self.world.next_fetch_run_id += 1
            run = FetchRun(
                source_code=source_code,
                status="running",
                feed_url=feed_url,
                http_status=None,
                bytes_read=0,
                article_count=0,
                error_code=None,
                error_message=None,
                started_at=started_at,
                finished_at=None,
                id=run_id,
            )
            self.world.fetch_runs.append(run)
            return run

    async def finish_fetch_run(
        self,
        run_id: int,
        status: str,
        http_status: int | None,
        bytes_read: int,
        article_count: int,
        error_code: str | None,
        error_message: str | None,
        finished_at: datetime,
    ) -> FetchRun:
        async with self.world.lock:
            for index, run in enumerate(self.world.fetch_runs):
                if run.id != run_id:
                    continue
                updated = FetchRun(
                    source_code=run.source_code,
                    status=status,
                    feed_url=run.feed_url,
                    http_status=http_status,
                    bytes_read=bytes_read,
                    article_count=article_count,
                    error_code=_clip(error_code, 64),
                    error_message=_clip(error_message, 500),
                    started_at=run.started_at,
                    finished_at=finished_at,
                    id=run.id,
                )
                self.world.fetch_runs[index] = updated
                return updated
            raise AssertionError("missing fetch run")

    async def save_raw_payload(self, fetch_run_id: int, body: str, content_type: str | None) -> None:
        async with self.world.lock:
            self.world.raw_payloads[fetch_run_id] = {
                "body": body[:65536],
                "content_type": _clip(content_type, 200),
            }

    async def upsert_articles(
        self,
        source_code: str,
        fetch_run_id: int,
        articles: list[ParsedArticle],
        fetched_at: datetime,
    ) -> int:
        async with self.world.lock:
            assert source_code in self.world.source_by_code
            by_key = {(row["source_code"], row["guid"]): index for index, row in enumerate(self.world.articles)}
            for item in articles:
                guid = item.guid[:500]
                lang = item.lang if item.lang in {"zh", "en", "und"} else "und"
                title = item.title.strip() or "\u2014"
                payload = {
                    "source_code": source_code,
                    "guid": guid,
                    "canonical_url": item.canonical_url[:500],
                    "title": title[:500],
                    "summary": (item.summary or "")[:8000],
                    "lang": lang,
                    "published_at": item.published_at,
                    "fetched_at": fetched_at,
                    "fetch_run_id": fetch_run_id,
                }
                key = (source_code, guid)
                found = by_key.get(key)
                if found is None:
                    row = {
                        **payload,
                        "id": self.world.next_article_id,
                        "cluster_job_id": None,
                    }
                    self.world.next_article_id += 1
                    by_key[key] = len(self.world.articles)
                    self.world.articles.append(row)
                else:
                    row = self.world.articles[found]
                    row.update(payload)
            return len(articles)

    async def list_runs(self, limit: int) -> list[FetchRun]:
        async with self.world.lock:
            rows = sorted(self.world.fetch_runs, key=lambda item: (item.started_at, item.id or 0), reverse=True)
            return rows[:limit]

    async def list_articles(
        self,
        source_code: str | None,
        start: date | None,
        end: date | None,
    ) -> list[Article]:
        async with self.world.lock:
            rows = list(self.world.articles)
            if source_code is not None:
                rows = [row for row in rows if row["source_code"] == source_code]
            if start is not None and end is not None:
                filtered = []
                for row in rows:
                    local = row["fetched_at"].astimezone(SHANGHAI).date()
                    if start <= local <= end:
                        filtered.append(row)
                rows = filtered
            rows.sort(key=lambda row: (row["fetched_at"], row["id"]), reverse=True)
            return [self._article(row) for row in rows]

    async def list_unclustered_articles(self) -> list[Article]:
        async with self.world.lock:
            rows = [row for row in self.world.articles if row["cluster_job_id"] is None]
            rows.sort(key=lambda row: row["id"])
            return [self._article(row) for row in rows]

    async def mark_clustered(self, article_ids: list[int], cluster_job_id: int) -> None:
        if not article_ids:
            return
        wanted = set(article_ids)
        async with self.world.lock:
            for row in self.world.articles:
                if row["id"] in wanted:
                    row["cluster_job_id"] = cluster_job_id

    async def create_cluster_job(
        self,
        briefing_date: date,
        status: str,
        writer: str,
        story_count: int,
        article_count: int,
        created_at: datetime,
        created_by_id: int | None,
    ) -> ClusterJob:
        email = None
        if created_by_id is not None:
            admin = await self.identity.get_admin_by_id(created_by_id)
            email = admin.email if admin is not None else None
        async with self.world.lock:
            job_id = self.world.next_cluster_job_id
            self.world.next_cluster_job_id += 1
            job = ClusterJob(
                briefing_date=briefing_date,
                status=status,
                writer=writer,
                story_count=story_count,
                article_count=article_count,
                created_at=created_at,
                created_by_email=email,
                id=job_id,
            )
            self.world.cluster_jobs.append(job)
            return job

    async def list_jobs(self, limit: int) -> list[ClusterJob]:
        async with self.world.lock:
            rows = sorted(
                self.world.cluster_jobs,
                key=lambda item: (item.created_at, item.id or 0),
                reverse=True,
            )
            return rows[:limit]
