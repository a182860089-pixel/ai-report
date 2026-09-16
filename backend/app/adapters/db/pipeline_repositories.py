from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import AdminUserRow, ArticleRow, ClusterJobRow, FetchRunRow, RawPayloadRow, SourceRow
from app.domain.entities import Article, ClusterJob, FetchRun, ParsedArticle
from app.domain.interfaces import PipelineRepository

SessionFactory = async_sessionmaker[AsyncSession]


def _clip(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


def _run(row: FetchRunRow, source_code: str) -> FetchRun:
    return FetchRun(
        source_code=source_code,
        status=row.status,
        feed_url=row.feed_url,
        http_status=row.http_status,
        bytes_read=row.bytes_read,
        article_count=row.article_count,
        error_code=row.error_code,
        error_message=row.error_message,
        started_at=row.started_at,
        finished_at=row.finished_at,
        id=row.id,
    )


def _article(row: ArticleRow, source_code: str, source_name: str) -> Article:
    return Article(
        source_code=source_code,
        guid=row.guid,
        canonical_url=row.canonical_url,
        title=row.title,
        summary=row.summary,
        lang=row.lang,
        published_at=row.published_at,
        fetched_at=row.fetched_at,
        cluster_job_id=row.cluster_job_id,
        id=row.id,
        source_name=source_name,
    )


def _job(row: ClusterJobRow, email: str | None) -> ClusterJob:
    return ClusterJob(
        briefing_date=row.briefing_date,
        status=row.status,
        writer=row.writer,
        story_count=row.story_count,
        article_count=row.article_count,
        created_at=row.created_at,
        created_by_email=email,
        id=row.id,
    )


class PgPipelineRepository(PipelineRepository):
    def __init__(self, sessions: SessionFactory) -> None:
        self.sessions = sessions

    async def start_fetch_run(self, source_code: str, feed_url: str, started_at: datetime) -> FetchRun:
        async with self.sessions() as session:
            source = await session.scalar(select(SourceRow).where(SourceRow.code == source_code))
            assert source is not None
            row = FetchRunRow(
                source_id=source.id,
                status="running",
                feed_url=feed_url,
                http_status=None,
                bytes_read=0,
                article_count=0,
                error_code=None,
                error_message=None,
                started_at=started_at,
                finished_at=None,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _run(row, source.code)

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
        async with self.sessions() as session:
            row = await session.get(FetchRunRow, run_id)
            assert row is not None
            row.status = status
            row.http_status = http_status
            row.bytes_read = bytes_read
            row.article_count = article_count
            row.error_code = _clip(error_code, 64)
            row.error_message = _clip(error_message, 500)
            row.finished_at = finished_at
            source = await session.get(SourceRow, row.source_id)
            await session.commit()
            await session.refresh(row)
            assert source is not None
            return _run(row, source.code)

    async def save_raw_payload(self, fetch_run_id: int, body: str, content_type: str | None) -> None:
        async with self.sessions() as session:
            existing = await session.get(RawPayloadRow, fetch_run_id)
            clipped = body[:65536]
            ct = _clip(content_type, 200)
            if existing is None:
                session.add(RawPayloadRow(fetch_run_id=fetch_run_id, body=clipped, content_type=ct))
            else:
                existing.body = clipped
                existing.content_type = ct
            await session.commit()

    async def upsert_articles(
        self,
        source_code: str,
        fetch_run_id: int,
        articles: list[ParsedArticle],
        fetched_at: datetime,
    ) -> int:
        async with self.sessions() as session:
            source = await session.scalar(select(SourceRow).where(SourceRow.code == source_code))
            assert source is not None
            for item in articles:
                title = item.title.strip() or "—"
                stmt = insert(ArticleRow).values(
                    source_id=source.id,
                    fetch_run_id=fetch_run_id,
                    guid=item.guid[:500],
                    canonical_url=item.canonical_url[:500],
                    title=title[:500],
                    summary=(item.summary or "")[:8000],
                    lang=item.lang if item.lang in {"zh", "en", "und"} else "und",
                    published_at=item.published_at,
                    fetched_at=fetched_at,
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="articles_source_guid_uq",
                    set_={
                        "title": stmt.excluded.title,
                        "summary": stmt.excluded.summary,
                        "canonical_url": stmt.excluded.canonical_url,
                        "lang": stmt.excluded.lang,
                        "published_at": stmt.excluded.published_at,
                        "fetched_at": stmt.excluded.fetched_at,
                        "fetch_run_id": stmt.excluded.fetch_run_id,
                    },
                )
                await session.execute(stmt)
            await session.commit()
        return len(articles)

    async def list_runs(self, limit: int) -> list[FetchRun]:
        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(FetchRunRow, SourceRow.code)
                    .join(SourceRow, SourceRow.id == FetchRunRow.source_id)
                    .order_by(FetchRunRow.started_at.desc(), FetchRunRow.id.desc())
                    .limit(limit)
                )
            ).all()
            return [_run(row, code) for row, code in rows]

    async def list_articles(
        self,
        source_code: str | None,
        start: date | None,
        end: date | None,
    ) -> list[Article]:
        async with self.sessions() as session:
            stmt = (
                select(ArticleRow, SourceRow.code, SourceRow.name)
                .join(SourceRow, SourceRow.id == ArticleRow.source_id)
            )
            if source_code is not None:
                stmt = stmt.where(SourceRow.code == source_code)
            if start is not None and end is not None:
                local_date = func.date(func.timezone("Asia/Shanghai", ArticleRow.fetched_at))
                stmt = stmt.where(local_date >= start, local_date <= end)
            stmt = stmt.order_by(ArticleRow.fetched_at.desc(), ArticleRow.id.desc())
            rows = (await session.execute(stmt)).all()
            return [_article(row, code, name) for row, code, name in rows]

    async def list_unclustered_articles(self) -> list[Article]:
        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(ArticleRow, SourceRow.code, SourceRow.name)
                    .join(SourceRow, SourceRow.id == ArticleRow.source_id)
                    .where(ArticleRow.cluster_job_id.is_(None))
                    .order_by(ArticleRow.id.asc())
                )
            ).all()
            return [_article(row, code, name) for row, code, name in rows]

    async def mark_clustered(self, article_ids: list[int], cluster_job_id: int) -> None:
        if not article_ids:
            return
        async with self.sessions() as session:
            await session.execute(
                update(ArticleRow)
                .where(ArticleRow.id.in_(article_ids))
                .values(cluster_job_id=cluster_job_id)
            )
            await session.commit()

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
        async with self.sessions() as session:
            row = ClusterJobRow(
                briefing_date=briefing_date,
                status=status,
                writer=writer,
                story_count=story_count,
                article_count=article_count,
                created_at=created_at,
                created_by=created_by_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            email = None
            if created_by_id is not None:
                admin = await session.get(AdminUserRow, created_by_id)
                email = admin.email if admin is not None else None
            return _job(row, email)

    async def list_jobs(self, limit: int) -> list[ClusterJob]:
        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(ClusterJobRow, AdminUserRow.email)
                    .outerjoin(AdminUserRow, AdminUserRow.id == ClusterJobRow.created_by)
                    .order_by(ClusterJobRow.created_at.desc(), ClusterJobRow.id.desc())
                    .limit(limit)
                )
            ).all()
            return [_job(row, email) for row, email in rows]
