from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

from app.domain.entities import (
    AdminUser,
    Article,
    AuditEntry,
    Briefing,
    BriefingListItem,
    ClusterJob,
    FetchRun,
    HttpFetchResult,
    ParsedArticle,
    Pulse,
    RefreshRecord,
    Source,
    Story,
    StorySummary,
    Text,
    Topic,
)


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...


class EditorialRepository(ABC):
    @abstractmethod
    async def get_current_date(self) -> date | None: ...

    @abstractmethod
    async def get_published_briefing(self, day: date) -> Briefing | None: ...

    @abstractmethod
    async def list_published_briefings(self, start: date, end: date) -> list[BriefingListItem]: ...

    @abstractmethod
    async def get_published_story(self, slug: str) -> Story | None: ...

    @abstractmethod
    async def search_published_stories(self, query: str) -> list[StorySummary]: ...


class CatalogRepository(ABC):
    @abstractmethod
    async def list_active_topics(self) -> list[Topic]: ...

    @abstractmethod
    async def get_active_topic_with_stories(self, slug: str) -> Topic | None: ...

    @abstractmethod
    async def list_sources(self) -> list[Source]: ...


class IdentityRepository(ABC):
    @abstractmethod
    async def get_admin_by_email(self, email: str) -> AdminUser | None: ...

    @abstractmethod
    async def get_admin_by_id(self, admin_id: int) -> AdminUser | None: ...

    @abstractmethod
    async def update_last_login(self, admin_id: int, at: datetime) -> None: ...

    @abstractmethod
    async def insert_refresh(
        self,
        admin_user_id: int,
        token_hash: str,
        expires_at: datetime,
        ip: str | None,
        user_agent: str | None,
    ) -> None: ...

    @abstractmethod
    async def get_refresh_by_hash(self, token_hash: str) -> RefreshRecord | None: ...

    @abstractmethod
    async def revoke_refresh(self, token_hash: str, at: datetime) -> None: ...

    @abstractmethod
    async def revoke_all_refresh(self, admin_user_id: int, at: datetime) -> None: ...

    @abstractmethod
    async def insert_audit(
        self,
        actor_id: int | None,
        action: str,
        resource: str,
        ip: str | None,
        user_agent: str | None,
        metadata: dict[str, Any],
    ) -> None: ...

    @abstractmethod
    async def list_audits(self, limit: int) -> list[AuditEntry]: ...


class HealthRepository(ABC):
    @abstractmethod
    async def ping(self) -> bool: ...


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool: ...

    @abstractmethod
    def dummy_hash(self) -> str: ...


class TokenService(ABC):
    @abstractmethod
    def issue_access(self, admin_id: int, email: str) -> str: ...

    @abstractmethod
    def parse_access(self, token: str) -> tuple[int, str]: ...

    @abstractmethod
    def new_refresh(self) -> str: ...

    @abstractmethod
    def hash_refresh(self, token: str) -> str: ...


class AdminCatalogRepository(ABC):
    @abstractmethod
    async def list_topics(self) -> list[Topic]: ...

    @abstractmethod
    async def get_topic(self, slug: str) -> Topic | None: ...

    @abstractmethod
    async def create_topic(self, slug: str, name: Text, blurb: Text, sort_order: int) -> Topic: ...

    @abstractmethod
    async def update_topic(
        self,
        slug: str,
        name: Text | None,
        blurb: Text | None,
        sort_order: int | None,
        is_active: bool | None,
    ) -> Topic: ...

    @abstractmethod
    async def delete_topic(self, slug: str) -> None: ...

    @abstractmethod
    async def list_sources(self) -> list[Source]: ...

    @abstractmethod
    async def get_source(self, code: str) -> Source | None: ...

    @abstractmethod
    async def create_source(self, source: Source) -> Source: ...

    @abstractmethod
    async def update_source(self, code: str, source: Source) -> Source: ...

    @abstractmethod
    async def delete_source(self, code: str) -> None: ...


class AdminEditorialRepository(ABC):
    @abstractmethod
    async def list_briefings(self, start: date, end: date) -> list[BriefingListItem]: ...

    @abstractmethod
    async def get_briefing(self, day: date) -> Briefing | None: ...

    @abstractmethod
    async def create_briefing(
        self,
        day: date,
        weekday: Text,
        title: Text,
        more_heading: Text,
        lede: tuple[Text, ...],
        pulse: Pulse,
        published_at: datetime,
    ) -> Briefing: ...

    @abstractmethod
    async def update_briefing(
        self,
        day: date,
        weekday: Text | None,
        title: Text | None,
        more_heading: Text | None,
        lede: tuple[Text, ...] | None,
        pulse: Pulse | None,
        published_at: datetime | None,
    ) -> Briefing: ...

    @abstractmethod
    async def set_briefing_status(self, day: date, status: str) -> Briefing: ...

    @abstractmethod
    async def delete_briefing(self, day: date) -> None: ...

    @abstractmethod
    async def list_stories(self, day: date | None, topic_slug: str | None) -> list[StorySummary]: ...

    @abstractmethod
    async def get_story(self, slug: str) -> Story | None: ...

    @abstractmethod
    async def create_story(self, story: Story) -> Story: ...

    @abstractmethod
    async def update_story(self, slug: str, story: Story) -> Story: ...

    @abstractmethod
    async def delete_story(self, slug: str) -> None: ...

class HttpFetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> HttpFetchResult: ...


class FeedParser(ABC):
    @abstractmethod
    def parse(self, body: bytes) -> list[ParsedArticle]: ...


class StoryWriter(ABC):
    @abstractmethod
    def write(
        self,
        *,
        slug: str,
        day: date,
        topic: Topic,
        articles: list[Article],
    ) -> Story: ...


class PipelineRepository(ABC):
    @abstractmethod
    async def start_fetch_run(self, source_code: str, feed_url: str, started_at: datetime) -> FetchRun: ...

    @abstractmethod
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
    ) -> FetchRun: ...

    @abstractmethod
    async def save_raw_payload(self, fetch_run_id: int, body: str, content_type: str | None) -> None: ...

    @abstractmethod
    async def upsert_articles(
        self,
        source_code: str,
        fetch_run_id: int,
        articles: list[ParsedArticle],
        fetched_at: datetime,
    ) -> int: ...

    @abstractmethod
    async def list_runs(self, limit: int) -> list[FetchRun]: ...

    @abstractmethod
    async def list_articles(
        self,
        source_code: str | None,
        start: date | None,
        end: date | None,
    ) -> list[Article]: ...

    @abstractmethod
    async def list_unclustered_articles(self) -> list[Article]: ...

    @abstractmethod
    async def mark_clustered(self, article_ids: list[int], cluster_job_id: int) -> None: ...

    @abstractmethod
    async def create_cluster_job(
        self,
        briefing_date: date,
        status: str,
        writer: str,
        story_count: int,
        article_count: int,
        created_at: datetime,
        created_by_id: int | None,
    ) -> ClusterJob: ...

    @abstractmethod
    async def list_jobs(self, limit: int) -> list[ClusterJob]: ...

