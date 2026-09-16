from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone

from app.adapters.http.fetcher import FakeHttpFetcher
from app.adapters.memory.repositories import MemoryIdentityRepository, MemoryPipelineRepository, MemoryWorld
from app.domain.entities import HttpFetchResult, ParsedArticle
from tests.conftest import make_client
from tests.integration.test_admin_crud import _h, _login

OPENAI_FEED = "https://openai.com/news/rss.xml"
CLUSTER_DAY = "2026-09-16"
RSS = (
    b"""<?xml version="1.0" encoding="UTF-8"?>"""
    b"""<rss version="2.0"><channel><title>OpenAI</title>"""
    b"""<item><title>GPT-5</title><link>https://openai.com/news/gpt-5</link>"""
    b"""<guid>https://openai.com/news/gpt-5</guid><description>New model</description></item>"""
    b"""<item><title>Agents everywhere</title><link>https://openai.com/news/agents-everywhere</link>"""
    b"""<guid>https://openai.com/news/agents-everywhere</guid><description>Tool use</description></item>"""
    b"""</channel></rss>"""
)
NO_FEED = {"anthropic", "deepmind", "jiqizhixin", "qbitai", "github", "36kr"}
WITH_FEED = {"openai-blog", "hf", "arxiv", "hn", "verge"}


def _openai_fetcher() -> FakeHttpFetcher:
    return FakeHttpFetcher(
        {
            OPENAI_FEED: HttpFetchResult(
                url=OPENAI_FEED,
                status="ok",
                http_status=200,
                body=RSS,
                content_type="application/rss+xml",
                error_code=None,
                error_message=None,
                bytes_read=len(RSS),
                truncated=False,
            )
        }
    )


def test_pipeline_requires_token():
    with make_client() as client:
        missing = client.post("/api/v1/admin/pipeline/fetch", json={})
        assert missing.status_code == 401
        assert missing.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid access token."}}
        listed = client.get("/api/v1/admin/pipeline/runs")
        assert listed.status_code == 401


def test_unknown_field_and_unknown_source_are_422():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        unknown_field = client.post(
            "/api/v1/admin/pipeline/fetch",
            headers=headers,
            json={"codes": ["openai-blog"], "extra": 1},
        )
        assert unknown_field.status_code == 422
        assert unknown_field.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Unknown field."}}
        unknown_source = client.post(
            "/api/v1/admin/pipeline/fetch",
            headers=headers,
            json={"codes": ["openai-blog", "nope"]},
        )
        assert unknown_source.status_code == 422
        assert unknown_source.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Unknown source."}}
        empty = client.post("/api/v1/admin/pipeline/fetch", headers=headers, json={"codes": []})
        assert empty.status_code == 200
        assert empty.json() == {"data": {"runs": [], "skipped": []}}
        assert client.app.state.world.fetch_runs == []


def test_memory_default_fetch_is_blocked_and_skips():
    with make_client() as client:
        token, _refresh = _login(client)
        response = client.post("/api/v1/admin/pipeline/fetch", headers=_h(token), json={})
        assert response.status_code == 200
        data = response.json()["data"]
        skipped = {row["code"]: row["reason"] for row in data["skipped"]}
        assert skipped["lab-rss"] == "quarantined"
        assert {code for code, reason in skipped.items() if reason == "no_feed"} == NO_FEED
        assert {row["sourceCode"] for row in data["runs"]} == WITH_FEED
        assert all(row["status"] == "blocked" and row["errorCode"] == "NETWORK_DISABLED" for row in data["runs"])
        public = json.dumps(client.get("/api/v1/sources").json())
        assert "homepageUrl" not in public
        assert "feedUrl" not in public


def test_fake_fetch_cluster_and_published_conflict():
    fetcher = _openai_fetcher()
    with make_client(http_fetcher=fetcher) as client:
        token, _refresh = _login(client)
        headers = _h(token)
        fetched = client.post(
            "/api/v1/admin/pipeline/fetch",
            headers=headers,
            json={"codes": ["openai-blog"]},
        )
        assert fetched.status_code == 200
        payload = fetched.json()["data"]
        assert payload["skipped"] == []
        assert len(payload["runs"]) == 1
        run = payload["runs"][0]
        assert run["sourceCode"] == "openai-blog"
        assert run["status"] == "ok"
        assert run["feedUrl"] == OPENAI_FEED
        assert run["articleCount"] == 2
        assert run["httpStatus"] == 200
        assert fetcher.calls == [OPENAI_FEED]

        source = client.get("/api/v1/admin/sources/openai-blog", headers=headers).json()["data"]
        assert source["todayCount"] == 2
        assert source["status"] == "ok"
        assert source["homepageUrl"] == "https://openai.com/news"
        assert source["feedUrl"] == OPENAI_FEED
        public = json.dumps(client.get("/api/v1/sources").json())
        assert "homepageUrl" not in public
        assert OPENAI_FEED not in public

        articles = client.get("/api/v1/admin/pipeline/articles?source=openai-blog", headers=headers)
        assert articles.status_code == 200
        items = articles.json()["data"]["items"]
        assert {row["title"] for row in items} == {"GPT-5", "Agents everywhere"}
        assert all(row["clustered"] is False for row in items)

        published = client.post(
            "/api/v1/admin/pipeline/cluster",
            headers=headers,
            json={"date": "2026-09-14"},
        )
        assert published.status_code == 409
        assert published.json() == {
            "error": {"code": "CONFLICT", "message": "Cannot cluster a published briefing."}
        }

        clustered = client.post(
            "/api/v1/admin/pipeline/cluster",
            headers=headers,
            json={"date": CLUSTER_DAY},
        )
        assert clustered.status_code == 200
        job = clustered.json()["data"]
        assert job["date"] == CLUSTER_DAY
        assert job["status"] == "ok"
        assert job["writer"] == "template"
        assert job["storyCount"] == 2
        assert job["articleCount"] == 2
        assert job["createdByEmail"] == "admin@example.com"
        assert job["slugs"] == ["20260916-1-agents", "20260916-2-models"]
        assert "id" not in job

        jobs = client.get("/api/v1/admin/pipeline/jobs", headers=headers)
        assert jobs.status_code == 200
        listed = jobs.json()["data"]["items"]
        assert listed
        assert "slugs" not in listed[0]
        assert listed[0]["date"] == CLUSTER_DAY

        after = client.get("/api/v1/admin/pipeline/articles?source=openai-blog", headers=headers).json()["data"]["items"]
        assert all(row["clustered"] is True for row in after)

        briefing = client.get(f"/api/v1/admin/briefings/{CLUSTER_DAY}", headers=headers).json()["data"]
        assert briefing["status"] == "draft"
        assert briefing["title"] == {"zh": "\u91c7\u96c6\u8349\u7a3f", "en": "Pipeline draft"}
        assert briefing["moreHeading"] == {"zh": "\u91c7\u96c6\u5212\u7248", "en": "Pipeline copy"}
        assert briefing["pulse"]["totalSources"] == 12
        assert briefing["pulse"]["clusters"] == 0
        assert client.get(f"/api/v1/briefings/{CLUSTER_DAY}").status_code == 404
        assert client.get("/api/v1/stories/20260916-1-agents").status_code == 404

        story = client.get("/api/v1/admin/stories/20260916-1-agents", headers=headers).json()["data"]
        assert story["section"] == "more"
        assert story["rank"] is None
        assert story["title"]["zh"] == "Agents everywhere"
        models = client.get("/api/v1/admin/stories/20260916-2-models", headers=headers).json()["data"]
        assert models["title"]["zh"] == "GPT-5"

        again = client.post(
            "/api/v1/admin/pipeline/cluster",
            headers=headers,
            json={"date": CLUSTER_DAY},
        )
        assert again.status_code == 200
        assert again.json()["data"]["storyCount"] == 0
        assert again.json()["data"]["articleCount"] == 0
        assert again.json()["data"]["slugs"] == []
        pulse = client.get(f"/api/v1/admin/briefings/{CLUSTER_DAY}", headers=headers).json()["data"]["pulse"]
        assert pulse["totalSources"] == 12
        assert pulse["clusters"] == 0

        blocked = client.delete("/api/v1/admin/sources/openai-blog", headers=headers)
        assert blocked.status_code == 409
        assert blocked.json() == {"error": {"code": "CONFLICT", "message": "Source still has articles."}}

        audit = client.get("/api/v1/admin/audit", headers=headers).json()["data"]["items"]
        actions = [row["action"] for row in audit]
        assert "pipeline.fetch" in actions
        assert "pipeline.cluster" in actions

        only_from = client.get("/api/v1/admin/pipeline/articles?from=2026-09-16", headers=headers)
        assert only_from.status_code == 422
        bad_range = client.get(
            "/api/v1/admin/pipeline/articles?from=2026-09-17&to=2026-09-16",
            headers=headers,
        )
        assert bad_range.status_code == 422
        unknown = client.get("/api/v1/admin/pipeline/articles?source=does-not-exist", headers=headers)
        assert unknown.status_code == 200
        assert unknown.json() == {"data": {"items": []}}
        invalid = client.get("/api/v1/admin/pipeline/articles?source=Not_A_Slug", headers=headers)
        assert invalid.status_code == 422


def test_shanghai_calendar_filter_on_memory_repo():
    world = MemoryWorld()
    repo = MemoryPipelineRepository(world, MemoryIdentityRepository())
    fetched = datetime(2026, 9, 15, 16, 0, 0, tzinfo=timezone.utc)
    parsed = [
        ParsedArticle(
            guid="https://openai.com/news/gpt-5",
            canonical_url="https://openai.com/news/gpt-5",
            title="   ",
            summary="x",
            lang="en",
            published_at=None,
        )
    ]

    async def go() -> None:
        run = await repo.start_fetch_run("openai-blog", OPENAI_FEED, fetched)
        assert run.id is not None
        count = await repo.upsert_articles("openai-blog", run.id, parsed, fetched)
        assert count == 1
        day = date(2026, 9, 16)
        hit = await repo.list_articles(None, day, day)
        assert len(hit) == 1
        assert hit[0].title == "\u2014"
        miss = await repo.list_articles(None, date(2026, 9, 15), date(2026, 9, 15))
        assert miss == []

    asyncio.run(go())

def test_schedule_status_and_manual_tick():
    missing_client = make_client()
    with missing_client as client:
        missing = client.get("/api/v1/admin/pipeline/schedule")
        assert missing.status_code == 401
        assert missing.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid access token."}}
        tick_missing = client.post("/api/v1/admin/pipeline/tick", json={})
        assert tick_missing.status_code == 401

    fetcher = _openai_fetcher()
    with make_client(http_fetcher=fetcher) as client:
        token, _refresh = _login(client)
        headers = _h(token)
        shown = client.get("/api/v1/admin/pipeline/schedule", headers=headers)
        assert shown.status_code == 200
        data = shown.json()["data"]
        assert data["enabled"] is False
        assert data["times"] == ["06:30", "12:30", "18:30"]
        assert data["timezone"] == "Asia/Shanghai"
        assert data["autoCluster"] is True
        assert data["nextRunAt"] is None
        assert data["lastTick"] is None

        unknown = client.post("/api/v1/admin/pipeline/tick", headers=headers, json={"extra": 1})
        assert unknown.status_code == 422
        assert unknown.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Unknown field."}}

        tick = client.post("/api/v1/admin/pipeline/tick", headers=headers, json={})
        assert tick.status_code == 200
        body = tick.json()["data"]
        assert body["trigger"] == "manual"
        assert body["fetchRunCount"] == 5
        assert body["skippedCount"] == 7
        assert body["clusterStatus"] in {"ok", "skipped_published"}
        assert body["errorCode"] is None
        if body["clusterStatus"] == "ok":
            assert body["storyCount"] == 2
            assert body["articleCount"] == 2
            assert body["slugs"] == ["%s-1-agents" % body["date"].replace("-", ""), "%s-2-models" % body["date"].replace("-", "")]
            assert body["date"] is not None

        after = client.get("/api/v1/admin/pipeline/schedule", headers=headers).json()["data"]
        assert after["lastTick"]["trigger"] == "manual"
        assert after["lastTick"]["fetchRunCount"] == 5


def test_enabled_schedule_exposes_next_run():
    from datetime import datetime
    from app.application.timefmt import SHANGHAI

    now = datetime.now(SHANGHAI)
    current = now.strftime("%H:%M")
    safe = "00:00" if current != "00:00" else "00:01"
    with make_client(pipeline_scheduler_enabled=True, pipeline_schedule=safe) as client:
        token, _refresh = _login(client)
        data = client.get("/api/v1/admin/pipeline/schedule", headers=_h(token)).json()["data"]
        assert data["enabled"] is True
        assert data["times"] == [safe]
        assert data["nextRunAt"]
        assert data["lastTick"] is None
