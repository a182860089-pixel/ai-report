from __future__ import annotations

import re

from alembic import op

revision = "0002_pipeline"
down_revision = "0001_init"
branch_labels = None
depends_on = None

DDL = r"""
CREATE TABLE fetch_runs (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_id       BIGINT NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
  status          TEXT NOT NULL,
  feed_url        TEXT NOT NULL,
  http_status     BIGINT,
  bytes_read      BIGINT NOT NULL DEFAULT 0,
  article_count   BIGINT NOT NULL DEFAULT 0,
  error_code      TEXT,
  error_message   TEXT,
  started_at      TIMESTAMPTZ NOT NULL,
  finished_at     TIMESTAMPTZ,
  CONSTRAINT fetch_runs_status_chk CHECK (status IN ('running', 'ok', 'error', 'blocked')),
  CONSTRAINT fetch_runs_feed_url_proto CHECK (feed_url ~ '^https://'),
  CONSTRAINT fetch_runs_feed_url_len CHECK (LENGTH(feed_url) BETWEEN 1 AND 500),
  CONSTRAINT fetch_runs_bytes_chk CHECK (bytes_read >= 0),
  CONSTRAINT fetch_runs_article_chk CHECK (article_count >= 0),
  CONSTRAINT fetch_runs_http_chk CHECK (http_status IS NULL OR http_status BETWEEN 0 AND 999),
  CONSTRAINT fetch_runs_error_code_len CHECK (error_code IS NULL OR LENGTH(error_code) BETWEEN 1 AND 64),
  CONSTRAINT fetch_runs_error_msg_len CHECK (error_message IS NULL OR LENGTH(error_message) <= 500)
);
CREATE INDEX fetch_runs_source_idx ON fetch_runs (source_id);
CREATE INDEX fetch_runs_started_idx ON fetch_runs (started_at DESC);

CREATE TABLE raw_payloads (
  fetch_run_id    BIGINT PRIMARY KEY REFERENCES fetch_runs (id) ON DELETE CASCADE,
  body            TEXT NOT NULL,
  content_type    TEXT,
  CONSTRAINT raw_payloads_body_len CHECK (LENGTH(body) <= 65536),
  CONSTRAINT raw_payloads_ct_len CHECK (content_type IS NULL OR LENGTH(content_type) <= 200)
);

CREATE TABLE cluster_jobs (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  briefing_date   DATE NOT NULL,
  status          TEXT NOT NULL,
  writer          TEXT NOT NULL,
  story_count     BIGINT NOT NULL DEFAULT 0,
  article_count   BIGINT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL,
  created_by      BIGINT REFERENCES admin_users (id) ON DELETE SET NULL,
  CONSTRAINT cluster_jobs_status_chk CHECK (status IN ('ok', 'error')),
  CONSTRAINT cluster_jobs_writer_chk CHECK (writer IN ('template', 'llm')),
  CONSTRAINT cluster_jobs_story_chk CHECK (story_count >= 0),
  CONSTRAINT cluster_jobs_article_chk CHECK (article_count >= 0)
);
CREATE INDEX cluster_jobs_date_idx ON cluster_jobs (briefing_date);
CREATE INDEX cluster_jobs_created_idx ON cluster_jobs (created_at DESC);
CREATE INDEX cluster_jobs_created_by_idx ON cluster_jobs (created_by);

CREATE TABLE articles (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_id       BIGINT NOT NULL REFERENCES sources (id) ON DELETE RESTRICT,
  fetch_run_id    BIGINT REFERENCES fetch_runs (id) ON DELETE SET NULL,
  cluster_job_id  BIGINT REFERENCES cluster_jobs (id) ON DELETE SET NULL,
  guid            TEXT NOT NULL,
  canonical_url   TEXT NOT NULL,
  title           TEXT NOT NULL,
  summary         TEXT NOT NULL,
  lang            TEXT NOT NULL,
  published_at    TIMESTAMPTZ,
  fetched_at      TIMESTAMPTZ NOT NULL,
  CONSTRAINT articles_source_guid_uq UNIQUE (source_id, guid),
  CONSTRAINT articles_guid_len CHECK (LENGTH(guid) BETWEEN 1 AND 500),
  CONSTRAINT articles_url_proto CHECK (canonical_url ~ '^https://'),
  CONSTRAINT articles_url_len CHECK (LENGTH(canonical_url) BETWEEN 1 AND 500),
  CONSTRAINT articles_title_len CHECK (LENGTH(title) BETWEEN 1 AND 500),
  CONSTRAINT articles_summary_len CHECK (LENGTH(summary) <= 8000),
  CONSTRAINT articles_lang_chk CHECK (lang IN ('zh', 'en', 'und'))
);
CREATE INDEX articles_source_idx ON articles (source_id);
CREATE INDEX articles_fetch_run_idx ON articles (fetch_run_id);
CREATE INDEX articles_cluster_job_idx ON articles (cluster_job_id);
CREATE INDEX articles_fetched_idx ON articles (fetched_at DESC);
"""

GRANT_SQL = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_report_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON
      fetch_runs, raw_payloads, cluster_jobs, articles
    TO ai_report_app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ai_report_app;
  END IF;
END
$$
"""

DROP_SQL = """
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS cluster_jobs;
DROP TABLE IF EXISTS raw_payloads;
DROP TABLE IF EXISTS fetch_runs;
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
    _execute_many(DDL)
    _execute_many(GRANT_SQL)


def downgrade() -> None:
    _execute_many(DROP_SQL)
