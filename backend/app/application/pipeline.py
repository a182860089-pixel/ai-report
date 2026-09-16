from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from dataclasses import replace
from datetime import date
from typing import Any

from app.application.timefmt import combine_hhmm, shanghai_date, weekday_for
from app.domain.entities import (
    AdminUser,
    Article,
    ClusterJob,
    FetchRun,
    FetchSkip,
    Pulse,
    ScheduledTick,
    Source,
    Text,
    Topic,
)
from app.domain.exceptions import AppError, FeedParseError
from app.domain.interfaces import (
    AdminCatalogRepository,
    AdminEditorialRepository,
    Clock,
    FeedParser,
    HttpFetcher,
    IdentityRepository,
    PipelineRepository,
    StoryWriter,
)

TOPIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("open-source", ("open source", "open-source", "opensource", "开源", "huggingface", "hugging face", "weights", "llama", "mistral")),
    ("agents", ("agent", "agents", "智能体", "tool use", "function call", "tool-use")),
    ("chips", ("gpu", "nvidia", "chip", "semiconductor", "芯片", "cuda", "tpu", "rubin", "hopper", "hbm")),
    ("policy", ("policy", "regulation", "act", "law", "监管", "法案", "eu ai", "governance")),
    ("robotics", ("robot", "robotics", "机器人")),
    ("on-device", ("on-device", "on device", "edge", "mobile", "端侧", "on_device")),
    ("industry-cn", ("alibaba", "baidu", "tencent", "bytedance", "huawei", "deepseek", "kimi", "通义", "中国", "字节", "阿里", "智谱", "glm")),
    ("safety", ("safety", "alignment", "jailbreak", "安全", "对齐", "red team")),
    ("models", ("gpt", "claude", "gemini", "model", "llm", "模型", "foundation")),
)

SLUG_SEQ = re.compile(r"^(\d{8})-(\d+)-")


def guess_topic(title: str, summary: str = "") -> str:
    hay = f"{title} {summary}".lower()
    for slug, needles in TOPIC_RULES:
        for needle in needles:
            if needle.lower() in hay:
                return slug
    return "research"


def _clip_payload(body: bytes) -> str:
    text = body.decode("utf-8", "replace")
    return text[:65536]


def _run_status_for(fetch_status: str, error_code: str | None) -> str:
    if fetch_status == "blocked" or error_code in {"SSRF_BLOCKED", "NETWORK_DISABLED"}:
        return "blocked"
    if fetch_status == "ok":
        return "ok"
    return "error"


class PipelineUseCases:
    def __init__(
        self,
        catalog: AdminCatalogRepository,
        editorial: AdminEditorialRepository,
        pipeline: PipelineRepository,
        fetcher: HttpFetcher,
        parser: FeedParser,
        writer: StoryWriter,
        clock: Clock,
        identity: IdentityRepository,
    ) -> None:
        self.catalog = catalog
        self.editorial = editorial
        self.pipeline = pipeline
        self.fetcher = fetcher
        self.parser = parser
        self.writer = writer
        self.clock = clock
        self.identity = identity

    async def fetch(
        self,
        codes: list[str] | None,
        admin: AdminUser,
        ip: str | None,
        ua: str | None,
    ) -> tuple[list[FetchRun], list[FetchSkip]]:
        sources = await self.catalog.list_sources()
        by_code = {item.code: item for item in sources}
        if codes is not None:
            missing = [code for code in codes if code not in by_code]
            if missing:
                raise AppError(422, "VALIDATION_ERROR", "Unknown source.")
            selected = [by_code[code] for code in codes]
        else:
            selected = list(sources)

        skipped: list[FetchSkip] = []
        to_fetch: list[Source] = []
        for source in selected:
            if source.is_quarantined:
                skipped.append(FetchSkip(source.code, "quarantined"))
            elif not source.feed_url:
                skipped.append(FetchSkip(source.code, "no_feed"))
            else:
                to_fetch.append(source)

        sem = asyncio.Semaphore(4)

        async def _one(source: Source) -> FetchRun:
            async with sem:
                return await self._fetch_one(source)

        runs = list(await asyncio.gather(*[_one(item) for item in to_fetch])) if to_fetch else []
        await self.identity.insert_audit(
            admin.id,
            "pipeline.fetch",
            "pipeline/fetch",
            ip,
            ua,
            {"codes": codes, "runCount": len(runs), "skipped": [item.code for item in skipped]},
        )
        return runs, skipped

    async def _fetch_one(self, source: Source) -> FetchRun:
        assert source.feed_url is not None
        started = self.clock.now()
        run = await self.pipeline.start_fetch_run(source.code, source.feed_url, started)
        assert run.id is not None
        result = await self.fetcher.fetch(source.feed_url)
        await self.pipeline.save_raw_payload(run.id, _clip_payload(result.body), result.content_type)

        article_count = 0
        error_code = result.error_code
        error_message = result.error_message
        status = _run_status_for(result.status, error_code)
        if result.status == "ok":
            try:
                parsed = self.parser.parse(result.body)
            except FeedParseError as exc:
                status = "error"
                error_code = "PARSE_ERROR"
                error_message = str(exc)[:200] or "Malformed XML."
            else:
                article_count = await self.pipeline.upsert_articles(source.code, run.id, parsed, started)
                status = "ok"
                error_code = None
                error_message = None

        finished = self.clock.now()
        finished_run = await self.pipeline.finish_fetch_run(
            run.id,
            status,
            result.http_status,
            result.bytes_read,
            article_count,
            error_code,
            error_message,
            finished,
        )
        await self._update_source_health(source, finished_run)
        return finished_run

    async def _update_source_health(self, source: Source, run: FetchRun) -> None:
        now = run.finished_at or self.clock.now()
        if run.status == "ok":
            updated = replace(
                source,
                status="ok",
                consecutive_failures=0,
                today_count=run.article_count,
                last_fetch_at=now,
                detail=Text("抓取正常", "Fetch ok"),
            )
        else:
            failures = source.consecutive_failures + 1
            status = "late" if failures == 1 else "bad"
            updated = replace(
                source,
                status=status,
                consecutive_failures=failures,
                last_fetch_at=now,
                detail=Text("抓取失败", "Fetch failed"),
            )
        await self.catalog.update_source(source.code, updated)

    async def list_runs(self, limit: int) -> list[FetchRun]:
        return await self.pipeline.list_runs(limit)

    async def list_articles(
        self,
        source_code: str | None,
        start: date | None,
        end: date | None,
    ) -> list[Article]:
        if source_code is not None and await self.catalog.get_source(source_code) is None:
            return []
        return await self.pipeline.list_articles(source_code, start, end)

    async def list_jobs(self, limit: int) -> list[ClusterJob]:
        return await self.pipeline.list_jobs(limit)

    async def cluster(
        self,
        day: date,
        admin: AdminUser,
        ip: str | None,
        ua: str | None,
    ) -> ClusterJob:
        briefing = await self.editorial.get_briefing(day)
        if briefing is not None and briefing.status == "published":
            raise AppError(409, "CONFLICT", "Cannot cluster a published briefing.")
        if briefing is None:
            sources = await self.catalog.list_sources()
            healthy = sum(1 for item in sources if item.status == "ok")
            await self.editorial.create_briefing(
                day,
                weekday_for(day),
                Text("采集草稿", "Pipeline draft"),
                Text("采集划版", "Pipeline copy"),
                (),
                Pulse(
                    clusters=0,
                    articles=0,
                    zh_en="1 : 1",
                    healthy=healthy,
                    total_sources=len(sources),
                    topics=(),
                ),
                combine_hhmm(day, "07:00"),
            )

        topics = {item.slug: item for item in await self.catalog.list_topics()}
        articles = await self.pipeline.list_unclustered_articles()
        groups: dict[str, list[Article]] = defaultdict(list)
        for article in articles:
            slug = guess_topic(article.title, article.summary)
            if slug not in topics:
                slug = "research"
            groups[slug].append(article)

        existing = await self.editorial.list_stories(day, None)
        prefix = day.strftime("%Y%m%d")
        seq = 0
        for summary in existing:
            match = SLUG_SEQ.match(summary.slug)
            if match and match.group(1) == prefix:
                seq = max(seq, int(match.group(2)))

        slugs: list[str] = []
        used_ids: list[int] = []
        for topic_slug in sorted(groups):
            topic = topics[topic_slug]
            batch = groups[topic_slug]
            seq += 1
            slug = f"{prefix}-{seq}-{topic.slug}"
            story = self.writer.write(slug=slug, day=day, topic=topic, articles=batch)
            await self.editorial.create_story(story)
            slugs.append(slug)
            used_ids.extend(item.id for item in batch if item.id is not None)

        job = await self.pipeline.create_cluster_job(
            day,
            "ok",
            "template",
            len(slugs),
            len(articles),
            self.clock.now(),
            admin.id,
        )
        if used_ids:
            assert job.id is not None
            await self.pipeline.mark_clustered(used_ids, job.id)
        await self.identity.insert_audit(
            admin.id,
            "pipeline.cluster",
            f"pipeline/{day.isoformat()}",
            ip,
            ua,
            {"date": day.isoformat(), "storyCount": len(slugs), "articleCount": len(articles)},
        )
        return replace(job, slugs=tuple(slugs))

    async def scheduled_tick(
        self,
        admin: AdminUser,
        *,
        auto_cluster: bool,
        trigger: str,
        ip: str | None,
        ua: str | None,
    ) -> ScheduledTick:
        started = self.clock.now()
        runs, skipped = await self.fetch(None, admin, ip, ua)
        cluster_status = "skipped_disabled"
        story_count = 0
        article_count = 0
        slugs: tuple[str, ...] = ()
        briefing_date = shanghai_date(started)
        error_code = None
        error_message = None
        if auto_cluster:
            unclustered = await self.pipeline.list_unclustered_articles()
            if not unclustered:
                cluster_status = "skipped_empty"
            else:
                try:
                    job = await self.cluster(briefing_date, admin, ip, ua)
                    cluster_status = "ok"
                    story_count = job.story_count
                    article_count = job.article_count
                    slugs = job.slugs
                except AppError as exc:
                    if exc.status == 409 and exc.code == "CONFLICT":
                        cluster_status = "skipped_published"
                    else:
                        raise
        finished = self.clock.now()
        await self.identity.insert_audit(
            admin.id,
            "pipeline.tick",
            f"pipeline/{briefing_date.isoformat()}",
            ip,
            ua,
            {
                "trigger": trigger,
                "fetchRunCount": len(runs),
                "skippedCount": len(skipped),
                "clusterStatus": cluster_status,
                "storyCount": story_count,
                "articleCount": article_count,
            },
        )
        return ScheduledTick(
            started_at=started,
            finished_at=finished,
            trigger=trigger,
            fetch_run_count=len(runs),
            skipped_count=len(skipped),
            cluster_status=cluster_status,
            story_count=story_count,
            article_count=article_count,
            slugs=slugs,
            briefing_date=briefing_date,
            error_code=error_code,
            error_message=error_message,
        )
