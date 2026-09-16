from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy import case, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import (
    ArticleRow,
    BriefingLedeRow,
    BriefingPulseRow,
    BriefingPulseTopicRow,
    BriefingRow,
    SourceRow,
    StoryCitationRow,
    StoryRow,
    StorySynthesisRow,
    StoryTimelineRow,
    TopicRow,
)
from app.adapters.db.repositories import _load_summaries, _topic_ref
from app.domain.entities import (
    Briefing,
    BriefingListItem,
    Citation,
    Pulse,
    PulseTopic,
    Source,
    Story,
    StorySummary,
    Text,
    TimelineItem,
    Topic,
)
from app.domain.exceptions import AppError
from app.domain.interfaces import AdminCatalogRepository, AdminEditorialRepository

SessionFactory = async_sessionmaker[AsyncSession]

_UQ = {
    "topics_slug_uq": "Topic slug already exists.",
    "sources_code_uq": "Source code already exists.",
    "briefings_date_uq": "Briefing date already exists.",
    "stories_slug_uq": "Story slug already exists.",
}


def _conflict(exc: IntegrityError) -> AppError:
    orig = getattr(exc, "orig", None)
    name = getattr(orig, "constraint_name", None) or ""
    diag = getattr(orig, "diag", None)
    if not name and diag is not None:
        name = getattr(diag, "constraint_name", "") or ""
    blob = f"{name} {orig}"
    for key, message in _UQ.items():
        if key in blob:
            return AppError(409, "CONFLICT", message)
    return AppError(409, "CONFLICT", "Conflict.")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_source(row: SourceRow) -> Source:
    return Source(
        code=row.code,
        name=row.name,
        status=row.status,
        last_fetch_at=row.last_fetch_at,
        today_count=row.today_count,
        detail=Text(row.detail_zh, row.detail_en),
        consecutive_failures=row.consecutive_failures,
        is_quarantined=row.is_quarantined,
        homepage_url=row.homepage_url,
        feed_url=row.feed_url,
    )


def _to_topic(row: TopicRow, count: int, stories: tuple[StorySummary, ...] = ()) -> Topic:
    return Topic(
        slug=row.slug,
        name=Text(row.name_zh, row.name_en),
        blurb=Text(row.blurb_zh, row.blurb_en),
        cluster_count=count,
        stories=stories,
        sort_order=row.sort_order,
        is_active=row.is_active,
    )


def _section_order():
    return case((StoryRow.section == "must", 0), else_=1)


def _source_row(source: Source) -> SourceRow:
    return SourceRow(
        code=source.code,
        name=source.name,
        status=source.status,
        last_fetch_at=source.last_fetch_at,
        today_count=source.today_count,
        consecutive_failures=source.consecutive_failures,
        is_quarantined=source.is_quarantined,
        detail_zh=source.detail.zh,
        detail_en=source.detail.en,
        homepage_url=source.homepage_url,
        feed_url=source.feed_url,
    )


class PgAdminCatalogRepository(AdminCatalogRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self.sessions = sessions

    async def list_topics(self) -> list[Topic]:
        async with self.sessions() as session:
            rows = (
                await session.scalars(select(TopicRow).order_by(TopicRow.sort_order, TopicRow.id))
            ).all()
            counts = await _topic_counts_all(session)
            return [_to_topic(row, counts.get(row.id, 0)) for row in rows]

    async def get_topic(self, slug: str) -> Topic | None:
        async with self.sessions() as session:
            row = await session.scalar(select(TopicRow).where(TopicRow.slug == slug))
            if row is None:
                return None
            stories = await _stories_for_topic(session, row.id)
            return _to_topic(row, len(stories), tuple(stories))

    async def create_topic(self, slug: str, name: Text, blurb: Text, sort_order: int) -> Topic:
        async with self.sessions() as session:
            now = _now()
            session.add(
                TopicRow(
                    slug=slug,
                    name_zh=name.zh,
                    name_en=name.en,
                    blurb_zh=blurb.zh,
                    blurb_en=blurb.en,
                    sort_order=sort_order,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise _conflict(exc) from exc
        found = await self.get_topic(slug)
        assert found is not None
        return found

    async def update_topic(
        self,
        slug: str,
        name: Text | None,
        blurb: Text | None,
        sort_order: int | None,
        is_active: bool | None,
    ) -> Topic:
        async with self.sessions() as session:
            row = await session.scalar(select(TopicRow).where(TopicRow.slug == slug))
            assert row is not None
            if name is not None:
                row.name_zh = name.zh
                row.name_en = name.en
            if blurb is not None:
                row.blurb_zh = blurb.zh
                row.blurb_en = blurb.en
            if sort_order is not None:
                row.sort_order = sort_order
            if is_active is not None:
                row.is_active = is_active
            row.updated_at = _now()
            await session.commit()
        found = await self.get_topic(slug)
        assert found is not None
        return found

    async def delete_topic(self, slug: str) -> None:
        async with self.sessions() as session:
            row = await session.scalar(select(TopicRow).where(TopicRow.slug == slug))
            assert row is not None
            count = await session.scalar(select(func.count(StoryRow.id)).where(StoryRow.topic_id == row.id))
            if count:
                raise AppError(409, "CONFLICT", "Topic still has stories.")
            await session.delete(row)
            await session.commit()

    async def list_sources(self) -> list[Source]:
        async with self.sessions() as session:
            rows = (await session.scalars(select(SourceRow).order_by(SourceRow.id))).all()
            return [_to_source(row) for row in rows]

    async def get_source(self, code: str) -> Source | None:
        async with self.sessions() as session:
            row = await session.scalar(select(SourceRow).where(SourceRow.code == code))
            return None if row is None else _to_source(row)

    async def create_source(self, source: Source) -> Source:
        async with self.sessions() as session:
            session.add(_source_row(source))
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise _conflict(exc) from exc
        found = await self.get_source(source.code)
        assert found is not None
        return found

    async def update_source(self, code: str, source: Source) -> Source:
        async with self.sessions() as session:
            row = await session.scalar(select(SourceRow).where(SourceRow.code == code))
            assert row is not None
            row.name = source.name
            row.status = source.status
            row.last_fetch_at = source.last_fetch_at
            row.today_count = source.today_count
            row.consecutive_failures = source.consecutive_failures
            row.is_quarantined = source.is_quarantined
            row.detail_zh = source.detail.zh
            row.detail_en = source.detail.en
            row.homepage_url = source.homepage_url
            row.feed_url = source.feed_url
            await session.commit()
        found = await self.get_source(code)
        assert found is not None
        return found

    async def delete_source(self, code: str) -> None:
        async with self.sessions() as session:
            row = await session.scalar(select(SourceRow).where(SourceRow.code == code))
            assert row is not None
            article_count = await session.scalar(
                select(func.count(ArticleRow.id)).where(ArticleRow.source_id == row.id)
            )
            if article_count:
                raise AppError(409, "CONFLICT", "Source still has articles.")
            count = await session.scalar(
                select(func.count(StoryCitationRow.id)).where(StoryCitationRow.source_id == row.id)
            )
            if count:
                raise AppError(409, "CONFLICT", "Source still has citations.")
            await session.delete(row)
            await session.commit()


class PgAdminEditorialRepository(AdminEditorialRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self.sessions = sessions

    async def list_briefings(self, start: date, end: date) -> list[BriefingListItem]:
        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(BriefingRow, BriefingPulseRow.clusters)
                    .join(BriefingPulseRow, BriefingPulseRow.briefing_id == BriefingRow.id)
                    .where(BriefingRow.date >= start, BriefingRow.date <= end)
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
                for briefing_id, _sid in must_rows:
                    counts[briefing_id] += 1
            return [
                BriefingListItem(
                    date=briefing.date,
                    weekday=Text(briefing.weekday_zh, briefing.weekday_en),
                    title=Text(briefing.title_zh, briefing.title_en),
                    published_at=briefing.published_at,
                    must_read_count=counts[briefing.id],
                    clusters=clusters,
                    status=briefing.status,
                )
                for briefing, clusters in rows
            ]

    async def get_briefing(self, day: date) -> Briefing | None:
        async with self.sessions() as session:
            briefing = await session.scalar(select(BriefingRow).where(BriefingRow.date == day))
            if briefing is None:
                return None
            return await _briefing_entity(session, briefing)

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
        async with self.sessions() as session:
            row = BriefingRow(
                date=day,
                weekday_zh=weekday.zh,
                weekday_en=weekday.en,
                title_zh=title.zh,
                title_en=title.en,
                more_heading_zh=more_heading.zh,
                more_heading_en=more_heading.en,
                status="draft",
                published_at=published_at,
            )
            session.add(row)
            try:
                await session.flush()
            except IntegrityError as exc:
                await session.rollback()
                raise _conflict(exc) from exc
            await _replace_ledes(session, row.id, lede)
            await _replace_pulse(session, row.id, pulse)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise _conflict(exc) from exc
        found = await self.get_briefing(day)
        assert found is not None
        return found

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
        async with self.sessions() as session:
            row = await session.scalar(select(BriefingRow).where(BriefingRow.date == day))
            assert row is not None
            if weekday is not None:
                row.weekday_zh = weekday.zh
                row.weekday_en = weekday.en
            if title is not None:
                row.title_zh = title.zh
                row.title_en = title.en
            if more_heading is not None:
                row.more_heading_zh = more_heading.zh
                row.more_heading_en = more_heading.en
            if published_at is not None:
                row.published_at = published_at
            if lede is not None:
                await _replace_ledes(session, row.id, lede)
            if pulse is not None:
                await _replace_pulse(session, row.id, pulse)
            await session.commit()
        found = await self.get_briefing(day)
        assert found is not None
        return found

    async def set_briefing_status(self, day: date, status: str) -> Briefing:
        async with self.sessions() as session:
            row = await session.scalar(select(BriefingRow).where(BriefingRow.date == day))
            assert row is not None
            row.status = status
            await session.commit()
        found = await self.get_briefing(day)
        assert found is not None
        return found

    async def delete_briefing(self, day: date) -> None:
        async with self.sessions() as session:
            row = await session.scalar(select(BriefingRow).where(BriefingRow.date == day))
            assert row is not None
            briefing_id = row.id
            await session.execute(delete(StoryRow).where(StoryRow.briefing_id == briefing_id))
            await session.execute(delete(BriefingLedeRow).where(BriefingLedeRow.briefing_id == briefing_id))
            await session.execute(
                delete(BriefingPulseTopicRow).where(BriefingPulseTopicRow.briefing_id == briefing_id)
            )
            await session.execute(delete(BriefingPulseRow).where(BriefingPulseRow.briefing_id == briefing_id))
            await session.delete(row)
            await session.commit()

    async def list_stories(self, day: date | None, topic_slug: str | None) -> list[StorySummary]:
        async with self.sessions() as session:
            stmt = (
                select(StoryRow)
                .join(BriefingRow, BriefingRow.id == StoryRow.briefing_id)
                .join(TopicRow, TopicRow.id == StoryRow.topic_id)
            )
            if day is not None:
                stmt = stmt.where(BriefingRow.date == day)
            if topic_slug is not None:
                stmt = stmt.where(TopicRow.slug == topic_slug)
            stmt = stmt.order_by(
                BriefingRow.date.desc(),
                _section_order(),
                StoryRow.rank.nulls_last(),
                StoryRow.id,
            )
            stories = (await session.scalars(stmt)).all()
            return await _load_summaries(session, list(stories))

    async def get_story(self, slug: str) -> Story | None:
        async with self.sessions() as session:
            story = await session.scalar(select(StoryRow).where(StoryRow.slug == slug))
            if story is None:
                return None
            return await _story_entity(session, story)

    async def create_story(self, story: Story) -> Story:
        async with self.sessions() as session:
            briefing = await session.scalar(select(BriefingRow).where(BriefingRow.date == story.date))
            topic = await session.scalar(select(TopicRow).where(TopicRow.slug == story.topic_slug))
            assert briefing is not None and topic is not None
            row = StoryRow(
                slug=story.slug,
                briefing_id=briefing.id,
                topic_id=topic.id,
                section=story.section,
                rank=story.rank,
                title_zh=story.title.zh,
                title_en=story.title.en,
                dek_zh=story.dek.zh,
                dek_en=story.dek.en,
            )
            session.add(row)
            try:
                await session.flush()
            except IntegrityError as exc:
                await session.rollback()
                raise _conflict(exc) from exc
            await _replace_story_children(session, row.id, story)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise _conflict(exc) from exc
        found = await self.get_story(story.slug)
        assert found is not None
        return found

    async def update_story(self, slug: str, story: Story) -> Story:
        async with self.sessions() as session:
            row = await session.scalar(select(StoryRow).where(StoryRow.slug == slug))
            assert row is not None
            briefing = await session.scalar(select(BriefingRow).where(BriefingRow.date == story.date))
            topic = await session.scalar(select(TopicRow).where(TopicRow.slug == story.topic_slug))
            assert briefing is not None and topic is not None
            row.briefing_id = briefing.id
            row.topic_id = topic.id
            row.section = story.section
            row.rank = story.rank
            row.title_zh = story.title.zh
            row.title_en = story.title.en
            row.dek_zh = story.dek.zh
            row.dek_en = story.dek.en
            await _replace_story_children(session, row.id, story)
            await session.commit()
        found = await self.get_story(slug)
        assert found is not None
        return found

    async def delete_story(self, slug: str) -> None:
        async with self.sessions() as session:
            row = await session.scalar(select(StoryRow).where(StoryRow.slug == slug))
            assert row is not None
            await session.delete(row)
            await session.commit()


async def _topic_counts_all(session: AsyncSession) -> dict[int, int]:
    rows = (await session.execute(select(StoryRow.topic_id, StoryRow.id))).all()
    counts: dict[int, int] = defaultdict(int)
    for topic_id, _sid in rows:
        counts[topic_id] += 1
    return counts


async def _stories_for_topic(session: AsyncSession, topic_id: int) -> list[StorySummary]:
    stories = (
        await session.scalars(
            select(StoryRow)
            .join(BriefingRow, BriefingRow.id == StoryRow.briefing_id)
            .where(StoryRow.topic_id == topic_id)
            .order_by(
                BriefingRow.date.desc(),
                _section_order(),
                StoryRow.rank.nulls_last(),
                StoryRow.id,
            )
        )
    ).all()
    return await _load_summaries(session, list(stories))


async def _replace_ledes(session: AsyncSession, briefing_id: int, lede: tuple[Text, ...]) -> None:
    await session.execute(delete(BriefingLedeRow).where(BriefingLedeRow.briefing_id == briefing_id))
    session.add_all(
        [
            BriefingLedeRow(
                briefing_id=briefing_id,
                sort_order=index,
                text_zh=item.zh,
                text_en=item.en,
            )
            for index, item in enumerate(lede)
        ]
    )


async def _replace_pulse(session: AsyncSession, briefing_id: int, pulse: Pulse) -> None:
    row = await session.get(BriefingPulseRow, briefing_id)
    if row is None:
        session.add(
            BriefingPulseRow(
                briefing_id=briefing_id,
                clusters=pulse.clusters,
                articles=pulse.articles,
                zh_en=pulse.zh_en,
                healthy=pulse.healthy,
                total_sources=pulse.total_sources,
            )
        )
    else:
        row.clusters = pulse.clusters
        row.articles = pulse.articles
        row.zh_en = pulse.zh_en
        row.healthy = pulse.healthy
        row.total_sources = pulse.total_sources
    await session.execute(delete(BriefingPulseTopicRow).where(BriefingPulseTopicRow.briefing_id == briefing_id))
    session.add_all(
        [
            BriefingPulseTopicRow(
                briefing_id=briefing_id,
                sort_order=index,
                name_zh=item.name.zh,
                name_en=item.name.en,
                count=item.count,
            )
            for index, item in enumerate(pulse.topics)
        ]
    )


async def _replace_story_children(session: AsyncSession, story_id: int, story: Story) -> None:
    await session.execute(delete(StorySynthesisRow).where(StorySynthesisRow.story_id == story_id))
    await session.execute(delete(StoryTimelineRow).where(StoryTimelineRow.story_id == story_id))
    await session.execute(delete(StoryCitationRow).where(StoryCitationRow.story_id == story_id))
    codes = {item.source_code for item in story.sources if item.source_code}
    code_to_id: dict[str, int] = {}
    if codes:
        rows = (await session.scalars(select(SourceRow).where(SourceRow.code.in_(codes)))).all()
        code_to_id = {row.code: row.id for row in rows}
    session.add_all(
        [
            StorySynthesisRow(story_id=story_id, sort_order=index, text_zh=item.zh, text_en=item.en)
            for index, item in enumerate(story.synthesis)
        ]
    )
    session.add_all(
        [
            StoryTimelineRow(
                story_id=story_id,
                sort_order=index,
                occurred_at=item.occurred_at,
                text_zh=item.text.zh,
                text_en=item.text.en,
            )
            for index, item in enumerate(story.timeline)
        ]
    )
    session.add_all(
        [
            StoryCitationRow(
                story_id=story_id,
                source_id=code_to_id.get(item.source_code) if item.source_code else None,
                source_name=item.name,
                lang=item.lang,
                kind_zh=item.kind.zh,
                kind_en=item.kind.en,
                cited_at=item.cited_at,
                sort_order=index,
            )
            for index, item in enumerate(story.sources)
        ]
    )


async def _briefing_entity(session: AsyncSession, briefing: BriefingRow) -> Briefing:
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
        await session.scalars(select(StoryRow).where(StoryRow.briefing_id == briefing.id).order_by(StoryRow.id))
    ).all()
    summaries = await _load_summaries(session, list(stories))
    must = tuple(sorted([item for item in summaries if item.section == "must"], key=lambda item: item.rank or 0))
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
            topics=tuple(PulseTopic(name=Text(row.name_zh, row.name_en), count=row.count) for row in pulse_topics),
        ),
        must_read=must,
        more=more,
        status=briefing.status,
    )


async def _story_entity(session: AsyncSession, story: StoryRow) -> Story:
    briefing = await session.get(BriefingRow, story.briefing_id)
    topic = await session.get(TopicRow, story.topic_id)
    assert briefing is not None and topic is not None
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
        sources = (await session.scalars(select(SourceRow).where(SourceRow.id.in_(source_ids)))).all()
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
            TimelineItem(occurred_at=row.occurred_at, text=Text(row.text_zh, row.text_en)) for row in timeline
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
