from __future__ import annotations

import re

from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

EXTENSION_SQL = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
    CREATE EXTENSION pg_trgm;
  END IF;
END
$$
"""

DDL = r"""
CREATE TABLE topics (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug          TEXT NOT NULL,
  name_zh       TEXT NOT NULL,
  name_en       TEXT NOT NULL,
  blurb_zh      TEXT NOT NULL,
  blurb_en      TEXT NOT NULL,
  sort_order    BIGINT NOT NULL DEFAULT 0,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT topics_slug_format CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  CONSTRAINT topics_slug_len CHECK (LENGTH(slug) BETWEEN 1 AND 64),
  CONSTRAINT topics_name_zh_len CHECK (LENGTH(name_zh) BETWEEN 1 AND 80),
  CONSTRAINT topics_name_en_len CHECK (LENGTH(name_en) BETWEEN 1 AND 80),
  CONSTRAINT topics_blurb_zh_len CHECK (LENGTH(blurb_zh) BETWEEN 1 AND 240),
  CONSTRAINT topics_blurb_en_len CHECK (LENGTH(blurb_en) BETWEEN 1 AND 240)
);
CREATE UNIQUE INDEX topics_slug_uq ON topics (slug);
CREATE INDEX topics_active_sort_idx ON topics (is_active, sort_order, id);

CREATE TABLE sources (
  id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code                  TEXT NOT NULL,
  name                  TEXT NOT NULL,
  status                TEXT NOT NULL,
  last_fetch_at         TIMESTAMPTZ,
  today_count           BIGINT NOT NULL DEFAULT 0,
  consecutive_failures  BIGINT NOT NULL DEFAULT 0,
  is_quarantined        BOOLEAN NOT NULL DEFAULT FALSE,
  detail_zh             TEXT NOT NULL,
  detail_en             TEXT NOT NULL,
  homepage_url          TEXT,
  feed_url              TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT sources_code_format CHECK (code ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  CONSTRAINT sources_code_len CHECK (LENGTH(code) BETWEEN 1 AND 64),
  CONSTRAINT sources_name_len CHECK (LENGTH(name) BETWEEN 1 AND 120),
  CONSTRAINT sources_status_chk CHECK (status IN ('ok', 'late', 'bad')),
  CONSTRAINT sources_today_count_chk CHECK (today_count >= 0),
  CONSTRAINT sources_fail_chk CHECK (consecutive_failures >= 0),
  CONSTRAINT sources_detail_zh_len CHECK (LENGTH(detail_zh) BETWEEN 1 AND 240),
  CONSTRAINT sources_detail_en_len CHECK (LENGTH(detail_en) BETWEEN 1 AND 240),
  CONSTRAINT sources_homepage_url_len CHECK (homepage_url IS NULL OR LENGTH(homepage_url) <= 500),
  CONSTRAINT sources_feed_url_len CHECK (feed_url IS NULL OR LENGTH(feed_url) <= 500),
  CONSTRAINT sources_homepage_url_proto CHECK (
    homepage_url IS NULL OR homepage_url ~ '^https://'
  ),
  CONSTRAINT sources_feed_url_proto CHECK (
    feed_url IS NULL OR feed_url ~ '^https://'
  )
);
CREATE UNIQUE INDEX sources_code_uq ON sources (code);
CREATE INDEX sources_status_idx ON sources (status);

CREATE TABLE briefings (
  id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  date               DATE NOT NULL,
  weekday_zh         TEXT NOT NULL,
  weekday_en         TEXT NOT NULL,
  title_zh           TEXT NOT NULL,
  title_en           TEXT NOT NULL,
  more_heading_zh    TEXT NOT NULL,
  more_heading_en    TEXT NOT NULL,
  status             TEXT NOT NULL DEFAULT 'published',
  published_at       TIMESTAMPTZ NOT NULL,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT briefings_title_zh_len CHECK (LENGTH(title_zh) BETWEEN 1 AND 200),
  CONSTRAINT briefings_title_en_len CHECK (LENGTH(title_en) BETWEEN 1 AND 200),
  CONSTRAINT briefings_weekday_zh_len CHECK (LENGTH(weekday_zh) BETWEEN 1 AND 16),
  CONSTRAINT briefings_weekday_en_len CHECK (LENGTH(weekday_en) BETWEEN 1 AND 16),
  CONSTRAINT briefings_more_zh_len CHECK (LENGTH(more_heading_zh) BETWEEN 1 AND 80),
  CONSTRAINT briefings_more_en_len CHECK (LENGTH(more_heading_en) BETWEEN 1 AND 80),
  CONSTRAINT briefings_status_chk CHECK (status IN ('draft', 'published'))
);
CREATE UNIQUE INDEX briefings_date_uq ON briefings (date);
CREATE INDEX briefings_published_idx ON briefings (status, date DESC);

CREATE TABLE briefing_ledes (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  briefing_id   BIGINT NOT NULL REFERENCES briefings (id) ON DELETE CASCADE,
  sort_order    BIGINT NOT NULL,
  text_zh       TEXT NOT NULL,
  text_en       TEXT NOT NULL,
  CONSTRAINT briefing_ledes_sort_chk CHECK (sort_order >= 0),
  CONSTRAINT briefing_ledes_zh_len CHECK (LENGTH(text_zh) BETWEEN 1 AND 400),
  CONSTRAINT briefing_ledes_en_len CHECK (LENGTH(text_en) BETWEEN 1 AND 400),
  CONSTRAINT briefing_ledes_order_uq UNIQUE (briefing_id, sort_order)
);
CREATE INDEX briefing_ledes_briefing_idx ON briefing_ledes (briefing_id);

CREATE TABLE briefing_pulse (
  briefing_id     BIGINT PRIMARY KEY REFERENCES briefings (id) ON DELETE CASCADE,
  clusters        BIGINT NOT NULL,
  articles        BIGINT NOT NULL,
  zh_en           TEXT NOT NULL,
  healthy         BIGINT NOT NULL,
  total_sources   BIGINT NOT NULL,
  CONSTRAINT briefing_pulse_clusters_chk CHECK (clusters >= 0),
  CONSTRAINT briefing_pulse_articles_chk CHECK (articles >= 0),
  CONSTRAINT briefing_pulse_healthy_chk CHECK (healthy >= 0),
  CONSTRAINT briefing_pulse_total_chk CHECK (total_sources >= 0),
  CONSTRAINT briefing_pulse_health_le_total CHECK (healthy <= total_sources),
  CONSTRAINT briefing_pulse_zh_en_len CHECK (LENGTH(zh_en) BETWEEN 1 AND 32)
);

CREATE TABLE briefing_pulse_topics (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  briefing_id   BIGINT NOT NULL REFERENCES briefings (id) ON DELETE CASCADE,
  sort_order    BIGINT NOT NULL,
  name_zh       TEXT NOT NULL,
  name_en       TEXT NOT NULL,
  count         BIGINT NOT NULL,
  CONSTRAINT briefing_pulse_topics_sort_chk CHECK (sort_order >= 0),
  CONSTRAINT briefing_pulse_topics_count_chk CHECK (count >= 0),
  CONSTRAINT briefing_pulse_topics_name_zh_len CHECK (LENGTH(name_zh) BETWEEN 1 AND 80),
  CONSTRAINT briefing_pulse_topics_name_en_len CHECK (LENGTH(name_en) BETWEEN 1 AND 80),
  CONSTRAINT briefing_pulse_topics_order_uq UNIQUE (briefing_id, sort_order)
);
CREATE INDEX briefing_pulse_topics_briefing_idx ON briefing_pulse_topics (briefing_id);

CREATE TABLE stories (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug          TEXT NOT NULL,
  briefing_id   BIGINT NOT NULL REFERENCES briefings (id) ON DELETE RESTRICT,
  topic_id      BIGINT NOT NULL REFERENCES topics (id) ON DELETE RESTRICT,
  section       TEXT NOT NULL,
  rank          BIGINT,
  title_zh      TEXT NOT NULL,
  title_en      TEXT NOT NULL,
  dek_zh        TEXT NOT NULL,
  dek_en        TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  search_zh     TEXT GENERATED ALWAYS AS (slug || ' ' || title_zh || ' ' || dek_zh) STORED,
  search_en     TEXT GENERATED ALWAYS AS (slug || ' ' || title_en || ' ' || dek_en) STORED,
  search_en_tsv TSVECTOR GENERATED ALWAYS AS (
                  to_tsvector('english', title_en || ' ' || dek_en)
                ) STORED,
  CONSTRAINT stories_slug_format CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  CONSTRAINT stories_slug_len CHECK (LENGTH(slug) BETWEEN 1 AND 80),
  CONSTRAINT stories_section_chk CHECK (section IN ('must', 'more')),
  CONSTRAINT stories_rank_chk CHECK (rank IS NULL OR rank > 0),
  CONSTRAINT stories_must_rank_chk CHECK (
    (section = 'must' AND rank IS NOT NULL) OR (section = 'more')
  ),
  CONSTRAINT stories_title_zh_len CHECK (LENGTH(title_zh) BETWEEN 1 AND 200),
  CONSTRAINT stories_title_en_len CHECK (LENGTH(title_en) BETWEEN 1 AND 200),
  CONSTRAINT stories_dek_zh_len CHECK (LENGTH(dek_zh) BETWEEN 1 AND 400),
  CONSTRAINT stories_dek_en_len CHECK (LENGTH(dek_en) BETWEEN 1 AND 400)
);
CREATE UNIQUE INDEX stories_slug_uq ON stories (slug);
CREATE INDEX stories_briefing_section_rank_idx ON stories (briefing_id, section, rank);
CREATE INDEX stories_topic_id_idx ON stories (topic_id, id DESC);
CREATE INDEX stories_search_zh_trgm_idx ON stories USING GIN (search_zh gin_trgm_ops);
CREATE INDEX stories_search_en_trgm_idx ON stories USING GIN (search_en gin_trgm_ops);
CREATE INDEX stories_search_en_tsv_idx ON stories USING GIN (search_en_tsv);

CREATE TABLE story_synthesis (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  story_id      BIGINT NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
  sort_order    BIGINT NOT NULL,
  text_zh       TEXT NOT NULL,
  text_en       TEXT NOT NULL,
  CONSTRAINT story_synthesis_sort_chk CHECK (sort_order >= 0),
  CONSTRAINT story_synthesis_zh_len CHECK (LENGTH(text_zh) BETWEEN 1 AND 2000),
  CONSTRAINT story_synthesis_en_len CHECK (LENGTH(text_en) BETWEEN 1 AND 2000),
  CONSTRAINT story_synthesis_order_uq UNIQUE (story_id, sort_order)
);
CREATE INDEX story_synthesis_story_idx ON story_synthesis (story_id);

CREATE TABLE story_timeline (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  story_id      BIGINT NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
  sort_order    BIGINT NOT NULL,
  occurred_at   TIMESTAMPTZ NOT NULL,
  text_zh       TEXT NOT NULL,
  text_en       TEXT NOT NULL,
  CONSTRAINT story_timeline_sort_chk CHECK (sort_order >= 0),
  CONSTRAINT story_timeline_zh_len CHECK (LENGTH(text_zh) BETWEEN 1 AND 400),
  CONSTRAINT story_timeline_en_len CHECK (LENGTH(text_en) BETWEEN 1 AND 400),
  CONSTRAINT story_timeline_order_uq UNIQUE (story_id, sort_order)
);
CREATE INDEX story_timeline_story_idx ON story_timeline (story_id, sort_order);

CREATE TABLE story_citations (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  story_id      BIGINT NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
  source_id     BIGINT REFERENCES sources (id) ON DELETE SET NULL,
  source_name   TEXT NOT NULL,
  lang          TEXT NOT NULL,
  kind_zh       TEXT NOT NULL,
  kind_en       TEXT NOT NULL,
  cited_at      TIMESTAMPTZ NOT NULL,
  sort_order    BIGINT NOT NULL,
  CONSTRAINT story_citations_sort_chk CHECK (sort_order >= 0),
  CONSTRAINT story_citations_lang_chk CHECK (lang IN ('zh', 'en')),
  CONSTRAINT story_citations_name_len CHECK (LENGTH(source_name) BETWEEN 1 AND 120),
  CONSTRAINT story_citations_kind_zh_len CHECK (LENGTH(kind_zh) BETWEEN 1 AND 32),
  CONSTRAINT story_citations_kind_en_len CHECK (LENGTH(kind_en) BETWEEN 1 AND 32),
  CONSTRAINT story_citations_order_uq UNIQUE (story_id, sort_order)
);
CREATE INDEX story_citations_story_idx ON story_citations (story_id, sort_order);
CREATE INDEX story_citations_source_idx ON story_citations (source_id);

CREATE TABLE admin_users (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email           TEXT NOT NULL,
  password_hash   TEXT NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at   TIMESTAMPTZ,
  CONSTRAINT admin_users_email_len CHECK (LENGTH(email) BETWEEN 3 AND 254),
  CONSTRAINT admin_users_email_format CHECK (email ~ '^[^@]+@[^@]+$'),
  CONSTRAINT admin_users_hash_len CHECK (LENGTH(password_hash) BETWEEN 20 AND 255)
);
CREATE UNIQUE INDEX admin_users_email_lower_uq ON admin_users (LOWER(email));

CREATE TABLE refresh_tokens (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  admin_user_id   BIGINT NOT NULL REFERENCES admin_users (id) ON DELETE CASCADE,
  token_hash      TEXT NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL,
  revoked_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_agent      TEXT,
  ip              INET,
  CONSTRAINT refresh_tokens_hash_len CHECK (LENGTH(token_hash) = 64),
  CONSTRAINT refresh_tokens_ua_len CHECK (user_agent IS NULL OR LENGTH(user_agent) <= 300)
);
CREATE UNIQUE INDEX refresh_tokens_hash_uq ON refresh_tokens (token_hash);
CREATE INDEX refresh_tokens_user_idx ON refresh_tokens (admin_user_id);
CREATE INDEX refresh_tokens_active_idx ON refresh_tokens (admin_user_id, expires_at)
  WHERE revoked_at IS NULL;

CREATE TABLE audit_logs (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_id      BIGINT REFERENCES admin_users (id) ON DELETE SET NULL,
  action        TEXT NOT NULL,
  resource      TEXT NOT NULL,
  ip            INET,
  user_agent    TEXT,
  metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT audit_logs_action_len CHECK (LENGTH(action) BETWEEN 1 AND 64),
  CONSTRAINT audit_logs_resource_len CHECK (LENGTH(resource) BETWEEN 1 AND 128),
  CONSTRAINT audit_logs_ua_len CHECK (user_agent IS NULL OR LENGTH(user_agent) <= 300)
);
CREATE INDEX audit_logs_created_idx ON audit_logs (created_at DESC);
CREATE INDEX audit_logs_actor_idx ON audit_logs (actor_id, created_at DESC);
"""

GRANT_SQL = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_report_app') THEN
    GRANT USAGE ON SCHEMA public TO ai_report_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON
      topics, sources, briefings, briefing_ledes, briefing_pulse, briefing_pulse_topics,
      stories, story_synthesis, story_timeline, story_citations,
      admin_users, refresh_tokens
    TO ai_report_app;
    GRANT SELECT, INSERT ON audit_logs TO ai_report_app;
    REVOKE UPDATE, DELETE ON audit_logs FROM ai_report_app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ai_report_app;
  END IF;
END
$$
"""

DROP_SQL = """
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS refresh_tokens;
DROP TABLE IF EXISTS admin_users;
DROP TABLE IF EXISTS story_citations;
DROP TABLE IF EXISTS story_timeline;
DROP TABLE IF EXISTS story_synthesis;
DROP TABLE IF EXISTS stories;
DROP TABLE IF EXISTS briefing_pulse_topics;
DROP TABLE IF EXISTS briefing_pulse;
DROP TABLE IF EXISTS briefing_ledes;
DROP TABLE IF EXISTS briefings;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS topics;
"""


def split_sql(sql: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        if sql[i] == "$":
            match = re.match(r"\$[A-Za-z0-9_]*\$", sql[i:])
            if match:
                tag = match.group(0)
                end = sql.find(tag, i + len(tag))
                if end < 0:
                    raise ValueError("unterminated dollar-quote")
                buf.append(sql[i : end + len(tag)])
                i = end + len(tag)
                continue
        if sql[i] == ";":
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(sql[i])
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _execute_many(sql: str) -> None:
    for stmt in split_sql(sql):
        op.execute(stmt)


def upgrade() -> None:
    _execute_many(EXTENSION_SQL)
    _execute_many(DDL)
    _execute_many(GRANT_SQL)


def downgrade() -> None:
    _execute_many(DROP_SQL)
