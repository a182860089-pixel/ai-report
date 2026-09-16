from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    MetaData,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData()


class TopicRow(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name_zh: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    blurb_zh: Mapped[str] = mapped_column(Text, nullable=False)
    blurb_en: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    today_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    consecutive_failures: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_quarantined: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detail_zh: Mapped[str] = mapped_column(Text, nullable=False)
    detail_en: Mapped[str] = mapped_column(Text, nullable=False)
    homepage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class BriefingRow(Base):
    __tablename__ = "briefings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    weekday_zh: Mapped[str] = mapped_column(Text, nullable=False)
    weekday_en: Mapped[str] = mapped_column(Text, nullable=False)
    title_zh: Mapped[str] = mapped_column(Text, nullable=False)
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    more_heading_zh: Mapped[str] = mapped_column(Text, nullable=False)
    more_heading_en: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="published")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ledes: Mapped[list["BriefingLedeRow"]] = relationship(
        back_populates="briefing",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    pulse: Mapped["BriefingPulseRow | None"] = relationship(
        back_populates="briefing",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    pulse_topics: Mapped[list["BriefingPulseTopicRow"]] = relationship(
        back_populates="briefing",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    stories: Mapped[list["StoryRow"]] = relationship(
        back_populates="briefing",
        passive_deletes=True,
    )


class BriefingLedeRow(Base):
    __tablename__ = "briefing_ledes"
    __table_args__ = (UniqueConstraint("briefing_id", "sort_order"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    briefing_id: Mapped[int] = mapped_column(ForeignKey("briefings.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text_zh: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    briefing: Mapped[BriefingRow] = relationship(back_populates="ledes")


class BriefingPulseRow(Base):
    __tablename__ = "briefing_pulse"

    briefing_id: Mapped[int] = mapped_column(ForeignKey("briefings.id", ondelete="CASCADE"), primary_key=True)
    clusters: Mapped[int] = mapped_column(BigInteger, nullable=False)
    articles: Mapped[int] = mapped_column(BigInteger, nullable=False)
    zh_en: Mapped[str] = mapped_column(Text, nullable=False)
    healthy: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_sources: Mapped[int] = mapped_column(BigInteger, nullable=False)
    briefing: Mapped[BriefingRow] = relationship(back_populates="pulse")


class BriefingPulseTopicRow(Base):
    __tablename__ = "briefing_pulse_topics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    briefing_id: Mapped[int] = mapped_column(ForeignKey("briefings.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name_zh: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    briefing: Mapped[BriefingRow] = relationship(back_populates="pulse_topics")


class StoryRow(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    briefing_id: Mapped[int] = mapped_column(ForeignKey("briefings.id", ondelete="RESTRICT"), nullable=False)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False)
    section: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title_zh: Mapped[str] = mapped_column(Text, nullable=False)
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    dek_zh: Mapped[str] = mapped_column(Text, nullable=False)
    dek_en: Mapped[str] = mapped_column(Text, nullable=False)

    briefing: Mapped[BriefingRow] = relationship(back_populates="stories")
    topic: Mapped[TopicRow] = relationship()
    synthesis: Mapped[list["StorySynthesisRow"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    timeline: Mapped[list["StoryTimelineRow"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    citations: Mapped[list["StoryCitationRow"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class StorySynthesisRow(Base):
    __tablename__ = "story_synthesis"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text_zh: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    story: Mapped[StoryRow] = relationship(back_populates="synthesis")


class StoryTimelineRow(Base):
    __tablename__ = "story_timeline"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    text_zh: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    story: Mapped[StoryRow] = relationship(back_populates="timeline")


class StoryCitationRow(Base):
    __tablename__ = "story_citations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(Text, nullable=False)
    kind_zh: Mapped[str] = mapped_column(Text, nullable=False)
    kind_en: Mapped[str] = mapped_column(Text, nullable=False)
    cited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False)
    story: Mapped[StoryRow] = relationship(back_populates="citations")


class AdminUserRow(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshTokenRow(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip = mapped_column(INET, nullable=True)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    ip = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)



class FetchRunRow(Base):
    __tablename__ = "fetch_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    feed_url: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bytes_read: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    article_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RawPayloadRow(Base):
    __tablename__ = "raw_payloads"

    fetch_run_id: Mapped[int] = mapped_column(ForeignKey("fetch_runs.id", ondelete="CASCADE"), primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(Text, nullable=True)


class ClusterJobRow(Base):
    __tablename__ = "cluster_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    briefing_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    writer: Mapped[str] = mapped_column(Text, nullable=False)
    story_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    article_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)


class ArticleRow(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("source_id", "guid", name="articles_source_guid_uq"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False)
    fetch_run_id: Mapped[int | None] = mapped_column(ForeignKey("fetch_runs.id", ondelete="SET NULL"), nullable=True)
    cluster_job_id: Mapped[int | None] = mapped_column(ForeignKey("cluster_jobs.id", ondelete="SET NULL"), nullable=True)
    guid: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
