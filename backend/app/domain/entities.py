from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Text:
    zh: str
    en: str


@dataclass(frozen=True)
class TopicRef:
    slug: str
    name: Text


@dataclass(frozen=True)
class StorySummary:
    slug: str
    date: date
    topic_slug: str
    rank: int | None
    section: str
    title: Text
    dek: Text
    topic: TopicRef
    source_count: int
    source_names: tuple[str, ...]


@dataclass(frozen=True)
class PulseTopic:
    name: Text
    count: int


@dataclass(frozen=True)
class Pulse:
    clusters: int
    articles: int
    zh_en: str
    healthy: int
    total_sources: int
    topics: tuple[PulseTopic, ...]


@dataclass(frozen=True)
class Briefing:
    date: date
    weekday: Text
    published_at: datetime
    title: Text
    lede: tuple[Text, ...]
    more_heading: Text
    pulse: Pulse
    must_read: tuple[StorySummary, ...]
    more: tuple[StorySummary, ...]
    status: str = "published"


@dataclass(frozen=True)
class BriefingListItem:
    date: date
    weekday: Text
    title: Text
    published_at: datetime
    must_read_count: int
    clusters: int
    status: str = "published"


@dataclass(frozen=True)
class Citation:
    name: str
    lang: str
    kind: Text
    cited_at: datetime
    source_code: str | None = None


@dataclass(frozen=True)
class TimelineItem:
    occurred_at: datetime
    text: Text


@dataclass(frozen=True)
class Story:
    slug: str
    date: date
    topic_slug: str
    rank: int | None
    section: str
    title: Text
    dek: Text
    topic: TopicRef
    synthesis: tuple[Text, ...]
    timeline: tuple[TimelineItem, ...]
    sources: tuple[Citation, ...]


@dataclass(frozen=True)
class Topic:
    slug: str
    name: Text
    blurb: Text
    cluster_count: int
    stories: tuple[StorySummary, ...] = ()
    sort_order: int = 0
    is_active: bool = True


@dataclass(frozen=True)
class Source:
    code: str
    name: str
    status: str
    last_fetch_at: datetime | None
    today_count: int
    detail: Text
    consecutive_failures: int = 0
    is_quarantined: bool = False
    homepage_url: str | None = None
    feed_url: str | None = None


@dataclass(frozen=True)
class AdminUser:
    id: int
    email: str
    password_hash: str
    is_active: bool


@dataclass(frozen=True)
class RefreshRecord:
    id: int
    admin_user_id: int
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True)
class AuditEntry:
    action: str
    resource: str
    created_at: datetime
    metadata: dict
    actor_email: str | None

@dataclass(frozen=True)
class HttpFetchResult:
    url: str
    status: str
    http_status: int | None
    body: bytes
    content_type: str | None
    error_code: str | None
    error_message: str | None
    bytes_read: int
    truncated: bool


@dataclass(frozen=True)
class ParsedArticle:
    guid: str
    canonical_url: str
    title: str
    summary: str
    lang: str
    published_at: datetime | None


@dataclass(frozen=True)
class FetchRun:
    source_code: str
    status: str
    feed_url: str
    http_status: int | None
    bytes_read: int
    article_count: int
    error_code: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    id: int | None = None


@dataclass(frozen=True)
class Article:
    source_code: str
    guid: str
    canonical_url: str
    title: str
    summary: str
    lang: str
    published_at: datetime | None
    fetched_at: datetime
    cluster_job_id: int | None = None
    id: int | None = None
    source_name: str = ''


@dataclass(frozen=True)
class ClusterJob:
    briefing_date: date
    status: str
    writer: str
    story_count: int
    article_count: int
    created_at: datetime
    created_by_email: str | None
    id: int | None = None
    slugs: tuple[str, ...] = ()


@dataclass(frozen=True)
class FetchSkip:
    code: str
    reason: str



@dataclass(frozen=True)
class ScheduledTick:
    started_at: datetime
    finished_at: datetime
    trigger: str
    fetch_run_count: int
    skipped_count: int
    cluster_status: str
    story_count: int
    article_count: int
    slugs: tuple[str, ...]
    briefing_date: date | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ScheduleStatus:
    enabled: bool
    times: tuple[str, ...]
    timezone: str
    auto_cluster: bool
    next_run_at: datetime | None
    last_tick: ScheduledTick | None
