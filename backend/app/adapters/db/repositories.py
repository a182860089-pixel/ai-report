from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from ipaddress import ip_address
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import (
    AdminUserRow,
    AuditLogRow,
    BriefingLedeRow,
    BriefingPulseRow,
    BriefingPulseTopicRow,
    BriefingRow,
    RefreshTokenRow,
    SourceRow,
    StoryCitationRow,
    StoryRow,
    StorySynthesisRow,
    StoryTimelineRow,
    TopicRow,
)
from app.domain.entities import (
    AdminUser,
    AuditEntry,
    Briefing,
    BriefingListItem,
    Citation,
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
from app.domain.interfaces import CatalogRepository, EditorialRepository, HealthRepository, IdentityRepository

SessionFactory = async_sessionmaker[AsyncSession]


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


def _topic_ref(row: TopicRow) -> TopicRef:
    return TopicRef(slug=row.slug, name=Text(row.name_zh, row.name_en))


def _summary(story: StoryRow, topic: TopicRow, names: list[str]) -> StorySummary:
    return StorySummary(
        slug=story.slug,
        date=story.briefing.date if story.briefing is not None else date.min,
        topic_slug=topic.slug,
        rank=story.rank,
        section=story.section,
        title=Text(story.title_zh, story.title_en),
        dek=Text(story.dek_zh, story.dek_en),
        topic=_topic_ref(topic),
        source_count=len(names),
        source_names=tuple(names[:3]),
    )


class PgEditorialRepository(EditorialRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self.sessions = sessions

    async def get_current_date(self) -> date | None:
        async with self.sessions() as session:
            value = await session.scalar(
                select(BriefingRow.date)
                .where(BriefingRow.status == "published")
                .order_by(BriefingRow.date.desc())
                .limit(1)
            )
            return value

    async def get_published_briefing(self, day: date) -> Briefing | None:
        async with self.sessions() as session:
            briefing = await session.scalar(
                select(BriefingRow).where(BriefingRow.date == day, BriefingRow.status == "published")
            )
            if briefing is None:
                return None
            ledes = (
                await session.scalars(
                    select(BriefingLedeRow)
                    .where(BriefingLedeRow.briefing_id == briefing.id)
                    .order_by(BriefingLedeRow.sort_order)
                )
            ).all()
            pulse = await session.get(BriefingPulseRow, briefing.id)
            pulse_topics = (
                await session.scalars(
                    select(BriefingPulseTopicRow)
                    .where(BriefingPulseTopicRow.briefing_id == briefing.id)
                    .order_by(BriefingPulseTopicRow.sort_order)
                )
            ).all()
            stories = (
                await session.scalars(
                    select(StoryRow).where(StoryRow.briefing_id == briefing.id).order_by(StoryRow.id)
                )
            ).all()
            summaries = await _load_summaries(session, stories)
            must = tuple(
                sorted(
                    [item for item in summaries if item.section == "must"],
                    key=lambda item: item.rank or 0,
                )
            )
            more = tuple(item for item in summaries if item.section == "more")
            assert pulse is not None
            return Briefing(
                date=briefing.date,
                weekday=Text(briefing.weekday_zh, briefing.weekday_en),
                published_at=briefing.published_at,
                title=Text(briefing.title_zh, briefing.title_en),
                lede=tuple(Text(row.text_zh, row.text_en) for row in ledes),
                more_heading=Text(briefing.more_heading_zh, briefing.more_heading_en),
                pulse=Pulse(
                    clusters=pulse.clusters,
                    articles=pulse.articles,
                    zh_en=pulse.zh_en,
                    healthy=pulse.healthy,
                    total_sources=pulse.total_sources,
                    topics=tuple(
                        PulseTopic(name=Text(row.name_zh, row.name_en), count=row.count)
                        for row in pulse_topics
                    ),
                ),
                must_read=must,
                more=more,
            )

    async def list_published_briefings(self, start: date, end: date) -> list[BriefingListItem]:
        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(BriefingRow, BriefingPulseRow.clusters)
                    .join(BriefingPulseRow, BriefingPulseRow.briefing_id == BriefingRow.id)
                    .where(
                        BriefingRow.status == "published",
                        BriefingRow.date >= start,
                        BriefingRow.date <= end,
                    )
                    .order_by(BriefingRow.date.asc())
                )
            ).all()
            briefing_ids = [row[0].id for row in rows]
            counts: dict[int, int] = defaultdict(int)
            if briefing_ids:
                must_rows = (
                    await session.execute(
                        select(StoryRow.briefing_id, StoryRow.id).where(
                            StoryRow.briefing_id.in_(briefing_ids), StoryRow.section == "must"
                        )
                    )
                ).all()
                for briefing_id, _story_id in must_rows:
                    counts[briefing_id] += 1
            return [
                BriefingListItem(
                    date=briefing.date,
                    weekday=Text(briefing.weekday_zh, briefing.weekday_en),
                    title=Text(briefing.title_zh, briefing.title_en),
                    published_at=briefing.published_at,
                    must_read_count=counts[briefing.id],
                    clusters=clusters,
                )
                for briefing, clusters in rows
            ]

    async def get_published_story(self, slug: str) -> Story | None:
        async with self.sessions() as session:
            story = await session.scalar(select(StoryRow).where(StoryRow.slug == slug))
            if story is None:
                return None
            briefing = await session.get(BriefingRow, story.briefing_id)
            if briefing is None or briefing.status != "published":
                return None
            topic = await session.get(TopicRow, story.topic_id)
            assert topic is not None
            synthesis = (
                await session.scalars(
                    select(StorySynthesisRow)
                    .where(StorySynthesisRow.story_id == story.id)
                    .order_by(StorySynthesisRow.sort_order)
                )
            ).all()
            timeline = (
                await session.scalars(
                    select(StoryTimelineRow)
                    .where(StoryTimelineRow.story_id == story.id)
                    .order_by(StoryTimelineRow.sort_order)
                )
            ).all()
            citations = (
                await session.scalars(
                    select(StoryCitationRow)
                    .where(StoryCitationRow.story_id == story.id)
                    .order_by(StoryCitationRow.sort_order)
                )
            ).all()
            source_ids = {row.source_id for row in citations if row.source_id is not None}
            codes: dict[int, str] = {}
            if source_ids:
                sources = (
                    await session.scalars(select(SourceRow).where(SourceRow.id.in_(source_ids)))
                ).all()
                codes = {row.id: row.code for row in sources}
            return Story(
                slug=story.slug,
                date=briefing.date,
                topic_slug=topic.slug,
                rank=story.rank,
                section=story.section,
                title=Text(story.title_zh, story.title_en),
                dek=Text(story.dek_zh, story.dek_en),
                topic=_topic_ref(topic),
                synthesis=tuple(Text(row.text_zh, row.text_en) for row in synthesis),
                timeline=tuple(
                    TimelineItem(occurred_at=row.occurred_at, text=Text(row.text_zh, row.text_en))
                    for row in timeline
                ),
                sources=tuple(
                    Citation(
                        name=row.source_name,
                        lang=row.lang,
                        kind=Text(row.kind_zh, row.kind_en),
                        cited_at=row.cited_at,
                        source_code=codes.get(row.source_id) if row.source_id is not None else None,
                    )
                    for row in citations
                ),
            )

    async def search_published_stories(self, query: str) -> list[StorySummary]:
        sql = text(
            """
            SELECT s.id
            FROM stories s
            JOIN briefings b ON b.id = s.briefing_id
            JOIN topics t ON t.id = s.topic_id
            WHERE b.status = 'published'
              AND (
                s.search_zh % :q
                OR s.search_en % :q
                OR s.search_en_tsv @@ plainto_tsquery('english', :q)
                OR position(lower(:q) in lower(s.search_zh)) > 0
                OR position(lower(:q) in lower(s.search_en)) > 0
                OR EXISTS (
                  SELECT 1 FROM story_synthesis syn
                  WHERE syn.story_id = s.id
                    AND (
                      syn.text_zh % :q OR syn.text_en % :q
                      OR position(lower(:q) in lower(syn.text_zh)) > 0
                      OR position(lower(:q) in lower(syn.text_en)) > 0
                    )
                )
                OR EXISTS (
                  SELECT 1 FROM story_citations c
                  WHERE c.story_id = s.id
                    AND (
                      c.source_name % :q
                      OR position(lower(:q) in lower(c.source_name)) > 0
                    )
                )
                OR t.name_zh % :q OR t.name_en % :q
                OR position(lower(:q) in lower(t.name_zh)) > 0
                OR position(lower(:q) in lower(t.name_en)) > 0
              )
            ORDER BY b.date DESC,
                     CASE WHEN s.section = 'must' THEN 0 ELSE 1 END,
                     s.rank NULLS LAST,
                     s.id
            """
        )
        async with self.sessions() as session:
            ids = [row[0] for row in (await session.execute(sql, {"q": query})).all()]
            if not ids:
                return []
            stories = (
                await session.scalars(select(StoryRow).where(StoryRow.id.in_(ids)))
            ).all()
            by_id = {row.id: row for row in stories}
            ordered = [by_id[i] for i in ids if i in by_id]
            return await _load_summaries(session, ordered)


class PgCatalogRepository(CatalogRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self.sessions = sessions

    async def list_active_topics(self) -> list[Topic]:
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(TopicRow)
                    .where(TopicRow.is_active.is_(True))
                    .order_by(TopicRow.sort_order, TopicRow.id)
                )
            ).all()
            counts = await _topic_counts(session)
            return [
                Topic(
                    slug=row.slug,
                    name=Text(row.name_zh, row.name_en),
                    blurb=Text(row.blurb_zh, row.blurb_en),
                    cluster_count=counts.get(row.id, 0),
                )
                for row in rows
            ]

    async def get_active_topic_with_stories(self, slug: str) -> Topic | None:
        async with self.sessions() as session:
            topic = await session.scalar(
                select(TopicRow).where(TopicRow.slug == slug, TopicRow.is_active.is_(True))
            )
            if topic is None:
                return None
            stories = (
                await session.scalars(
                    select(StoryRow)
                    .join(BriefingRow, BriefingRow.id == StoryRow.briefing_id)
                    .where(StoryRow.topic_id == topic.id, BriefingRow.status == "published")
                    .order_by(
                        BriefingRow.date.desc(),
                        text("CASE WHEN stories.section = 'must' THEN 0 ELSE 1 END"),
                        StoryRow.rank.nulls_last(),
                        StoryRow.id,
                    )
                )
            ).all()
            summaries = await _load_summaries(session, stories)
            return Topic(
                slug=topic.slug,
                name=Text(topic.name_zh, topic.name_en),
                blurb=Text(topic.blurb_zh, topic.blurb_en),
                cluster_count=len(summaries),
                stories=tuple(summaries),
            )

    async def list_sources(self) -> list[Source]:
        async with self.sessions() as session:
            rows = (await session.scalars(select(SourceRow).order_by(SourceRow.id))).all()
            return [
                Source(
                    code=row.code,
                    name=row.name,
                    status=row.status,
                    last_fetch_at=row.last_fetch_at,
                    today_count=row.today_count,
                    detail=Text(row.detail_zh, row.detail_en),
                )
                for row in rows
            ]


class PgIdentityRepository(IdentityRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self.sessions = sessions

    async def get_admin_by_email(self, email: str) -> AdminUser | None:
        async with self.sessions() as session:
            row = await session.scalar(
                select(AdminUserRow).where(func.lower(AdminUserRow.email) == email.lower())
            )
            return _admin(row)

    async def get_admin_by_id(self, admin_id: int) -> AdminUser | None:
        async with self.sessions() as session:
            row = await session.get(AdminUserRow, admin_id)
            return _admin(row)

    async def update_last_login(self, admin_id: int, at: datetime) -> None:
        async with self.sessions() as session:
            await session.execute(
                update(AdminUserRow).where(AdminUserRow.id == admin_id).values(last_login_at=at)
            )
            await session.commit()

    async def insert_refresh(
        self,
        admin_user_id: int,
        token_hash: str,
        expires_at: datetime,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        async with self.sessions() as session:
            session.add(
                RefreshTokenRow(
                    admin_user_id=admin_user_id,
                    token_hash=token_hash,
                    expires_at=expires_at,
                    user_agent=_clip(user_agent, 300),
                    ip=_safe_ip(ip),
                )
            )
            await session.commit()

    async def get_refresh_by_hash(self, token_hash: str) -> RefreshRecord | None:
        async with self.sessions() as session:
            row = await session.scalar(select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash))
            if row is None:
                return None
            return RefreshRecord(row.id, row.admin_user_id, row.token_hash, row.expires_at, row.revoked_at)

    async def revoke_refresh(self, token_hash: str, at: datetime) -> None:
        async with self.sessions() as session:
            await session.execute(
                update(RefreshTokenRow)
                .where(RefreshTokenRow.token_hash == token_hash)
                .values(revoked_at=at)
            )
            await session.commit()

    async def revoke_all_refresh(self, admin_user_id: int, at: datetime) -> None:
        async with self.sessions() as session:
            await session.execute(
                update(RefreshTokenRow)
                .where(RefreshTokenRow.admin_user_id == admin_user_id, RefreshTokenRow.revoked_at.is_(None))
                .values(revoked_at=at)
            )
            await session.commit()

    async def insert_audit(
        self,
        actor_id: int | None,
        action: str,
        resource: str,
        ip: str | None,
        user_agent: str | None,
        metadata: dict[str, Any],
    ) -> None:
        async with self.sessions() as session:
            session.add(
                AuditLogRow(
                    actor_id=actor_id,
                    action=action,
                    resource=resource,
                    ip=_safe_ip(ip),
                    user_agent=_clip(user_agent, 300),
                    metadata_=metadata,
                    created_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def list_audits(self, limit: int) -> list[AuditEntry]:
        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(AuditLogRow, AdminUserRow.email)
                    .outerjoin(AdminUserRow, AdminUserRow.id == AuditLogRow.actor_id)
                    .order_by(AuditLogRow.id.desc())
                    .limit(limit)
                )
            ).all()
            return [
                AuditEntry(
                    action=log.action,
                    resource=log.resource,
                    created_at=log.created_at,
                    metadata=log.metadata_,
                    actor_email=email,
                )
                for log, email in rows
            ]


class PgHealthRepository(HealthRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self.sessions = sessions

    async def ping(self) -> bool:
        try:
            async with self.sessions() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


def _admin(row: AdminUserRow | None) -> AdminUser | None:
    if row is None:
        return None
    return AdminUser(id=row.id, email=row.email, password_hash=row.password_hash, is_active=row.is_active)


async def _load_summaries(session: AsyncSession, stories: list[StoryRow]) -> list[StorySummary]:
    if not stories:
        return []
    ids = [row.id for row in stories]
    topic_ids = {row.topic_id for row in stories}
    briefing_ids = {row.briefing_id for row in stories}
    topics = {
        row.id: row
        for row in (await session.scalars(select(TopicRow).where(TopicRow.id.in_(topic_ids)))).all()
    }
    briefings = {
        row.id: row
        for row in (await session.scalars(select(BriefingRow).where(BriefingRow.id.in_(briefing_ids)))).all()
    }
    citations = (
        await session.scalars(
            select(StoryCitationRow)
            .where(StoryCitationRow.story_id.in_(ids))
            .order_by(StoryCitationRow.story_id, StoryCitationRow.sort_order)
        )
    ).all()
    names: dict[int, list[str]] = defaultdict(list)
    for row in citations:
        names[row.story_id].append(row.source_name)
    out: list[StorySummary] = []
    for story in stories:
        story.briefing = briefings[story.briefing_id]
        out.append(_summary(story, topics[story.topic_id], names[story.id]))
    return out


async def _topic_counts(session: AsyncSession) -> dict[int, int]:
    rows = (
        await session.execute(
            select(StoryRow.topic_id, StoryRow.id)
            .join(BriefingRow, BriefingRow.id == StoryRow.briefing_id)
            .where(BriefingRow.status == "published")
        )
    ).all()
    counts: dict[int, int] = defaultdict(int)
    for topic_id, _sid in rows:
        counts[topic_id] += 1
    return counts