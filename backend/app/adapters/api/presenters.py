from __future__ import annotations

from datetime import timezone

from app.application.timefmt import format_hhmm
from app.domain.entities import Article, AuditEntry, Briefing, BriefingListItem, ClusterJob, FetchRun, FetchSkip, ScheduleStatus, ScheduledTick, Source, Story, StorySummary, Topic


def text_out(value) -> dict[str, str]:
    return {"zh": value.zh, "en": value.en}


def summary_out(item: StorySummary) -> dict:
    return {
        "slug": item.slug,
        "date": item.date.isoformat(),
        "topicSlug": item.topic_slug,
        "rank": item.rank,
        "section": item.section,
        "title": text_out(item.title),
        "dek": text_out(item.dek),
        "topic": {"slug": item.topic.slug, "name": text_out(item.topic.name)},
        "sourceCount": item.source_count,
        "sourceNames": list(item.source_names),
    }


def briefing_out(item: Briefing) -> dict:
    return {
        "date": item.date.isoformat(),
        "weekday": text_out(item.weekday),
        "updatedAt": format_hhmm(item.published_at),
        "title": text_out(item.title),
        "lede": [text_out(row) for row in item.lede],
        "moreHeading": text_out(item.more_heading),
        "pulse": {
            "clusters": item.pulse.clusters,
            "articles": item.pulse.articles,
            "zhEn": item.pulse.zh_en,
            "healthy": item.pulse.healthy,
            "totalSources": item.pulse.total_sources,
            "topics": [
                {"name": text_out(topic.name), "count": topic.count}
                for topic in item.pulse.topics
            ],
        },
        "mustRead": [summary_out(row) for row in item.must_read],
        "more": [summary_out(row) for row in item.more],
    }


def briefing_list_item_out(item: BriefingListItem) -> dict:
    return {
        "date": item.date.isoformat(),
        "weekday": text_out(item.weekday),
        "title": text_out(item.title),
        "updatedAt": format_hhmm(item.published_at),
        "mustReadCount": item.must_read_count,
        "clusters": item.clusters,
    }


def story_out(item: Story) -> dict:
    return {
        "slug": item.slug,
        "date": item.date.isoformat(),
        "topicSlug": item.topic_slug,
        "rank": item.rank,
        "section": item.section,
        "title": text_out(item.title),
        "dek": text_out(item.dek),
        "topic": {"slug": item.topic.slug, "name": text_out(item.topic.name)},
        "synthesis": [text_out(row) for row in item.synthesis],
        "timeline": [
            {"time": format_hhmm(row.occurred_at), "text": text_out(row.text)}
            for row in item.timeline
        ],
        "sources": [
            {
                "name": row.name,
                "lang": row.lang,
                "kind": text_out(row.kind),
                "time": format_hhmm(row.cited_at),
            }
            for row in item.sources
        ],
    }


def topic_list_item_out(item: Topic) -> dict:
    return {
        "slug": item.slug,
        "name": text_out(item.name),
        "blurb": text_out(item.blurb),
        "clusterCount": item.cluster_count,
    }


def topic_detail_out(item: Topic) -> dict:
    payload = topic_list_item_out(item)
    payload["stories"] = [summary_out(row) for row in item.stories]
    return payload


def source_out(item: Source) -> dict:
    return {
        "id": item.code,
        "name": item.name,
        "status": item.status,
        "lastFetch": format_hhmm(item.last_fetch_at, dash_if_none=True),
        "todayCount": item.today_count,
        "detail": text_out(item.detail),
    }



def admin_topic_list_item_out(item: Topic) -> dict:
    payload = topic_list_item_out(item)
    payload["sortOrder"] = item.sort_order
    payload["isActive"] = item.is_active
    return payload


def admin_topic_detail_out(item: Topic) -> dict:
    payload = admin_topic_list_item_out(item)
    payload["stories"] = [summary_out(row) for row in item.stories]
    return payload


def admin_source_out(item: Source) -> dict:
    payload = source_out(item)
    payload["consecutiveFailures"] = item.consecutive_failures
    payload["isQuarantined"] = item.is_quarantined
    payload["homepageUrl"] = item.homepage_url
    payload["feedUrl"] = item.feed_url
    return payload


def admin_briefing_out(item: Briefing) -> dict:
    payload = briefing_out(item)
    payload["status"] = item.status
    return payload


def admin_briefing_list_item_out(item: BriefingListItem) -> dict:
    payload = briefing_list_item_out(item)
    payload["status"] = item.status
    return payload


def admin_story_out(item: Story) -> dict:
    payload = story_out(item)
    for src, row in zip(payload["sources"], item.sources):
        src["sourceCode"] = row.source_code
    return payload


def audit_out(item: AuditEntry) -> dict:
    created = item.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    created = created.astimezone(timezone.utc).replace(microsecond=0)
    stamp = created.isoformat().replace("+00:00", "Z")
    return {
        "action": item.action,
        "resource": item.resource,
        "createdAt": stamp,
        "actorEmail": item.actor_email,
        "metadata": item.metadata,
    }

def iso_z(value) -> str | None:
    if value is None:
        return None
    created = value
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    created = created.astimezone(timezone.utc).replace(microsecond=0)
    return created.isoformat().replace("+00:00", "Z")


def fetch_run_out(item: FetchRun) -> dict:
    return {
        "sourceCode": item.source_code,
        "status": item.status,
        "feedUrl": item.feed_url,
        "httpStatus": item.http_status,
        "bytesRead": item.bytes_read,
        "articleCount": item.article_count,
        "errorCode": item.error_code,
        "errorMessage": item.error_message,
        "startedAt": iso_z(item.started_at),
        "finishedAt": iso_z(item.finished_at),
    }


def article_out(item: Article) -> dict:
    return {
        "sourceCode": item.source_code,
        "guid": item.guid,
        "canonicalUrl": item.canonical_url,
        "title": item.title,
        "summary": item.summary,
        "lang": item.lang,
        "publishedAt": iso_z(item.published_at),
        "fetchedAt": iso_z(item.fetched_at),
        "clustered": item.cluster_job_id is not None,
    }


def cluster_job_out(item: ClusterJob, *, with_slugs: bool = False) -> dict:
    payload = {
        "date": item.briefing_date.isoformat(),
        "status": item.status,
        "writer": item.writer,
        "storyCount": item.story_count,
        "articleCount": item.article_count,
        "createdAt": iso_z(item.created_at),
        "createdByEmail": item.created_by_email,
    }
    if with_slugs:
        payload["slugs"] = list(item.slugs)
    return payload


def fetch_skip_out(item: FetchSkip) -> dict:
    return {"code": item.code, "reason": item.reason}

def scheduled_tick_out(item: ScheduledTick) -> dict:
    return {
        "startedAt": iso_z(item.started_at),
        "finishedAt": iso_z(item.finished_at),
        "trigger": item.trigger,
        "fetchRunCount": item.fetch_run_count,
        "skippedCount": item.skipped_count,
        "clusterStatus": item.cluster_status,
        "storyCount": item.story_count,
        "articleCount": item.article_count,
        "slugs": list(item.slugs),
        "date": item.briefing_date.isoformat() if item.briefing_date else None,
        "errorCode": item.error_code,
        "errorMessage": item.error_message,
    }


def schedule_status_out(item: ScheduleStatus) -> dict:
    return {
        "enabled": item.enabled,
        "times": list(item.times),
        "timezone": item.timezone,
        "autoCluster": item.auto_cluster,
        "nextRunAt": iso_z(item.next_run_at),
        "lastTick": scheduled_tick_out(item.last_tick) if item.last_tick else None,
    }

