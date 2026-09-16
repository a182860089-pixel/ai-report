from __future__ import annotations

import json
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, JWT_SECRET, make_settings
from tests.integration.test_admin_crud import (
    MORE_SLUGS,
    MUST_SLUGS,
    _briefing_body,
    _h,
    _login,
    _source_body,
    _story_body,
    _topic_body,
)
from tests.integration.test_v1_acceptance import (
    DASH,
    DAY1_TITLE_ZH,
    LLAMA_TITLE_ZH,
    MODEL_STORY_SLUGS,
    QUANTUM,
    TODAY_TITLE_ZH,
)
from app.main import create_app

PG_URL = os.environ.get("AI_REPORT_PG_TEST_URL") or os.environ.get("DATABASE_URL")

pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(
        not PG_URL or "postgresql" not in str(PG_URL),
        reason="set AI_REPORT_PG_TEST_URL to a live PostgreSQL 16",
    ),
]

PROBE_DAY = "2099-06-01"
PROBE_TOPIC = "pg-probe-topic"
PROBE_SOURCE = "pg-probe-source"
PROBE_HTTPS = "pg-probe-https"
PROBE_STORY_A = "pg-probe-story-a"
PROBE_STORY_B = "pg-probe-story-b"
PUBLIC_SOURCE_KEYS = {"id", "name", "status", "lastFetch", "todayCount", "detail"}


@pytest.fixture(scope="module")
def pg_client() -> Iterator[TestClient]:
    app = create_app(
        make_settings(
            repository="postgres",
            database_url=PG_URL,
            alembic_database_url=None,
            jwt_secret=JWT_SECRET,
            admin_email=ADMIN_EMAIL,
            admin_password="",
            debug=False,
        )
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(autouse=True)
def _reset_pg_limiter(pg_client: TestClient) -> None:
    pg_client.app.state.limiter.reset()


def _wipe_probe(client: TestClient, token: str) -> None:
    headers = _h(token)
    client.post(f"/api/v1/admin/briefings/{PROBE_DAY}/unpublish", headers=headers)
    client.delete(f"/api/v1/admin/briefings/{PROBE_DAY}", headers=headers)
    for slug in (PROBE_STORY_A, PROBE_STORY_B):
        client.delete(f"/api/v1/admin/stories/{slug}", headers=headers)
    client.delete(f"/api/v1/admin/topics/{PROBE_TOPIC}", headers=headers)
    for code in (PROBE_SOURCE, PROBE_HTTPS):
        client.delete(f"/api/v1/admin/sources/{code}", headers=headers)


def test_readyz_and_meta(pg_client: TestClient) -> None:
    ready = pg_client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json() == {"data": {"status": "ready"}}
    meta = pg_client.get("/api/v1/meta")
    assert meta.status_code == 200
    assert meta.json() == {
        "data": {"currentDate": "2026-09-14", "timezone": "Asia/Shanghai"}
    }


def test_today_briefing_seed(pg_client: TestClient) -> None:
    response = pg_client.get("/api/v1/briefings/today")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["date"] == "2026-09-14"
    assert data["title"]["zh"] == TODAY_TITLE_ZH
    assert data["updatedAt"] == "07:12"
    assert data["pulse"]["clusters"] == 14
    assert data["pulse"]["articles"] == 86
    assert data["pulse"]["zhEn"] == "4 : 3"
    assert data["pulse"]["healthy"] == 24
    assert data["pulse"]["totalSources"] == 26
    assert [row["slug"] for row in data["mustRead"]] == MUST_SLUGS
    llama = data["mustRead"][4]
    assert llama["slug"] == "llama-41-8b"
    assert llama["title"]["zh"] == LLAMA_TITLE_ZH
    assert llama["sourceNames"] == ["Meta", "GitHub", QUANTUM]
    assert [row["slug"] for row in data["more"]] == MORE_SLUGS
    assert all(row["section"] == "more" and row["rank"] is None for row in data["more"])


def test_archive_and_empty_day(pg_client: TestClient) -> None:
    ok = pg_client.get("/api/v1/briefings/2026-09-01")
    assert ok.status_code == 200
    assert ok.json()["data"]["title"]["zh"] == DAY1_TITLE_ZH
    missing = pg_client.get("/api/v1/briefings/2099-01-01")
    assert missing.status_code == 404
    listing = pg_client.get(
        "/api/v1/briefings", params={"from": "2026-09-01", "to": "2026-09-14"}
    )
    items = listing.json()["data"]["items"]
    assert [row["date"] for row in items] == [f"2026-09-{day:02d}" for day in range(1, 15)]
    assert items[-1]["mustReadCount"] == 8
    assert items[-1]["clusters"] == 14


def test_story_topics_sources_search(pg_client: TestClient) -> None:
    story = pg_client.get("/api/v1/stories/claude-memory")
    assert story.status_code == 200
    body = story.json()["data"]
    assert body["slug"] == "claude-memory"
    assert "sourceCode" not in body
    assert [row["name"] for row in body["sources"]][0] == "Anthropic News"
    unknown = pg_client.get("/api/v1/stories/no-such-cluster")
    assert unknown.status_code == 404

    topics = pg_client.get("/api/v1/topics")
    items = topics.json()["data"]["items"]
    assert len(items) == 10
    assert items[0]["slug"] == "models"
    assert items[0]["clusterCount"] == 5
    assert sum(row["clusterCount"] for row in items) == 53
    models = pg_client.get("/api/v1/topics/models")
    assert [row["slug"] for row in models.json()["data"]["stories"]] == MODEL_STORY_SLUGS

    sources = pg_client.get("/api/v1/sources").json()["data"]["items"]
    assert len(sources) == 12
    assert sources[0]["id"] == "openai-blog"
    assert sources[-1]["id"] == "lab-rss"
    assert sources[-1]["lastFetch"] == DASH

    search = pg_client.get("/api/v1/search", params={"q": "Claude"})
    slugs = [row["slug"] for row in search.json()["data"]["items"]]
    assert "claude-memory" in slugs
    dates = [row["date"] for row in search.json()["data"]["items"]]
    assert dates == sorted(dates, reverse=True)


def test_login_and_admin_me(pg_client: TestClient) -> None:
    token, _refresh = _login(pg_client)
    me = pg_client.get("/api/v1/admin/me", headers=_h(token))
    assert me.status_code == 200
    assert me.json()["data"]["email"] == ADMIN_EMAIL
    bad = pg_client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "wrong-password-12"},
    )
    assert bad.status_code == 401
    assert bad.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid credentials."}}


def test_draft_briefing_hidden_from_public(pg_client: TestClient) -> None:
    token, _refresh = _login(pg_client)
    day = "2099-01-02"
    pg_client.delete(f"/api/v1/admin/briefings/{day}", headers=_h(token))
    created = pg_client.post(
        "/api/v1/admin/briefings",
        headers=_h(token),
        json=_briefing_body(date=day),
    )
    assert created.status_code == 201
    try:
        public = pg_client.get(f"/api/v1/briefings/{day}")
        assert public.status_code == 404
        listing = pg_client.get("/api/v1/briefings", params={"from": day, "to": day})
        assert listing.json()["data"]["items"] == []
        today = pg_client.get("/api/v1/briefings/today")
        assert today.json()["data"]["date"] == "2026-09-14"
    finally:
        deleted = pg_client.delete(f"/api/v1/admin/briefings/{day}", headers=_h(token))
        assert deleted.status_code == 200


def test_admin_write_requires_token(pg_client: TestClient) -> None:
    missing = pg_client.post("/api/v1/admin/topics", json=_topic_body(slug=PROBE_TOPIC))
    assert missing.status_code == 401
    assert missing.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid access token."}}
    bad = pg_client.patch(
        f"/api/v1/admin/topics/{PROBE_TOPIC}",
        headers={"Authorization": "Bearer not-a-jwt"},
        json={"sortOrder": 1},
    )
    assert bad.status_code == 401
    invalid = pg_client.get("/api/v1/admin/topics/Not_A_Slug")
    assert invalid.status_code == 401
    token, _refresh = _login(pg_client)
    parsed = pg_client.get("/api/v1/admin/topics/Not_A_Slug", headers=_h(token))
    assert parsed.status_code == 422
    assert parsed.json()["error"]["message"] == "Invalid slug."


def test_pg_admin_crud_lifecycle(pg_client: TestClient) -> None:
    token, _refresh = _login(pg_client)
    headers = _h(token)
    _wipe_probe(pg_client, token)
    pg_client.app.state.limiter.reset()
    try:
        unknown_field = pg_client.post(
            "/api/v1/admin/topics",
            headers=headers,
            json=_topic_body(slug=PROBE_TOPIC, id=1),
        )
        assert unknown_field.status_code == 422
        assert unknown_field.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Unknown field."}}

        topic = pg_client.post("/api/v1/admin/topics", headers=headers, json=_topic_body(slug=PROBE_TOPIC))
        assert topic.status_code == 201
        assert topic.json()["data"]["clusterCount"] == 0
        assert topic.json()["data"]["isActive"] is True
        dup_topic = pg_client.post("/api/v1/admin/topics", headers=headers, json=_topic_body(slug=PROBE_TOPIC))
        assert dup_topic.status_code == 409
        assert dup_topic.json() == {"error": {"code": "CONFLICT", "message": "Topic slug already exists."}}

        http_source = pg_client.post(
            "/api/v1/admin/sources",
            headers=headers,
            json=_source_body(id=PROBE_SOURCE, homepageUrl="http://example.com"),
        )
        assert http_source.status_code == 422
        assert http_source.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Invalid URL."}}

        source = pg_client.post(
            "/api/v1/admin/sources",
            headers=headers,
            json=_source_body(id=PROBE_SOURCE, homepageUrl="https://example.com/feed"),
        )
        assert source.status_code == 201
        assert source.json()["data"]["homepageUrl"] == "https://example.com/feed"
        dup_source = pg_client.post(
            "/api/v1/admin/sources",
            headers=headers,
            json=_source_body(id=PROBE_SOURCE),
        )
        assert dup_source.status_code == 409
        assert dup_source.json() == {"error": {"code": "CONFLICT", "message": "Source code already exists."}}
        public_sources = pg_client.get("/api/v1/sources")
        dumped = json.dumps(public_sources.json())
        assert "homepageUrl" not in dumped
        assert "https://example.com/feed" not in dumped
        assert "consecutiveFailures" not in dumped
        assert "isQuarantined" not in dumped
        assert all(set(row) == PUBLIC_SOURCE_KEYS for row in public_sources.json()["data"]["items"])

        briefing = pg_client.post(
            "/api/v1/admin/briefings",
            headers=headers,
            json=_briefing_body(date=PROBE_DAY),
        )
        assert briefing.status_code == 201
        assert briefing.json()["data"]["status"] == "draft"
        assert briefing.json()["data"]["weekday"] == {"zh": "\u661f\u671f\u4e00", "en": "Monday"}
        assert briefing.json()["data"]["pulse"]["clusters"] == 7
        assert briefing.json()["data"]["pulse"]["totalSources"] == 26
        assert pg_client.get(f"/api/v1/briefings/{PROBE_DAY}").status_code == 404
        dup_briefing = pg_client.post(
            "/api/v1/admin/briefings",
            headers=headers,
            json=_briefing_body(date=PROBE_DAY),
        )
        assert dup_briefing.status_code == 409
        assert dup_briefing.json() == {
            "error": {"code": "CONFLICT", "message": "Briefing date already exists."}
        }

        first = pg_client.post(
            "/api/v1/admin/stories",
            headers=headers,
            json=_story_body(
                slug=PROBE_STORY_A,
                date=PROBE_DAY,
                topicSlug=PROBE_TOPIC,
                rank=2,
                sources=[
                    {
                        "name": "Probe Source",
                        "lang": "en",
                        "kind": {"zh": "\u4e00\u624b", "en": "Primary"},
                        "time": "06:12",
                        "sourceCode": PROBE_SOURCE,
                    }
                ],
            ),
        )
        second = pg_client.post(
            "/api/v1/admin/stories",
            headers=headers,
            json=_story_body(
                slug=PROBE_STORY_B,
                date=PROBE_DAY,
                topicSlug=PROBE_TOPIC,
                rank=1,
                section="more",
            ),
        )
        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["data"]["sources"][0]["sourceCode"] == PROBE_SOURCE
        assert second.json()["data"]["section"] == "more"
        assert second.json()["data"]["rank"] is None
        assert pg_client.get(f"/api/v1/stories/{PROBE_STORY_A}").status_code == 404
        admin_story = pg_client.get(f"/api/v1/admin/stories/{PROBE_STORY_A}", headers=headers)
        assert admin_story.status_code == 200
        assert admin_story.json()["data"]["slug"] == PROBE_STORY_A

        blocked_topic = pg_client.delete(f"/api/v1/admin/topics/{PROBE_TOPIC}", headers=headers)
        assert blocked_topic.status_code == 409
        assert blocked_topic.json() == {"error": {"code": "CONFLICT", "message": "Topic still has stories."}}
        blocked_source = pg_client.delete(f"/api/v1/admin/sources/{PROBE_SOURCE}", headers=headers)
        assert blocked_source.status_code == 409
        assert blocked_source.json() == {
            "error": {"code": "CONFLICT", "message": "Source still has citations."}
        }

        admin_briefing = pg_client.get(f"/api/v1/admin/briefings/{PROBE_DAY}", headers=headers)
        data = admin_briefing.json()["data"]
        assert data["pulse"]["clusters"] == 7
        assert data["pulse"]["totalSources"] == 26
        assert [row["slug"] for row in data["mustRead"]] == [PROBE_STORY_A]
        assert [row["slug"] for row in data["more"]] == [PROBE_STORY_B]

        published = pg_client.post(f"/api/v1/admin/briefings/{PROBE_DAY}/publish", headers=headers)
        assert published.status_code == 200
        assert published.json()["data"]["status"] == "published"
        visible = pg_client.get(f"/api/v1/briefings/{PROBE_DAY}")
        assert visible.status_code == 200
        assert visible.json()["data"]["title"]["zh"] == "\u8349\u7a3f\u65e5"
        assert "status" not in visible.json()["data"]
        public_story = pg_client.get(f"/api/v1/stories/{PROBE_STORY_A}")
        assert public_story.status_code == 200
        assert "sourceCode" not in json.dumps(public_story.json())

        blocked_published = pg_client.delete(f"/api/v1/admin/briefings/{PROBE_DAY}", headers=headers)
        assert blocked_published.status_code == 409
        assert blocked_published.json() == {
            "error": {"code": "CONFLICT", "message": "Cannot delete a published briefing."}
        }

        hidden = pg_client.patch(
            f"/api/v1/admin/topics/{PROBE_TOPIC}",
            headers=headers,
            json={"isActive": False},
        )
        assert hidden.status_code == 200
        listing = pg_client.get("/api/v1/topics")
        assert PROBE_TOPIC not in [row["slug"] for row in listing.json()["data"]["items"]]
        assert pg_client.get(f"/api/v1/topics/{PROBE_TOPIC}").status_code == 404
        admin_topic = pg_client.get(f"/api/v1/admin/topics/{PROBE_TOPIC}", headers=headers)
        assert admin_topic.status_code == 200
        assert admin_topic.json()["data"]["isActive"] is False

        unpublished = pg_client.post(f"/api/v1/admin/briefings/{PROBE_DAY}/unpublish", headers=headers)
        assert unpublished.status_code == 200
        assert unpublished.json()["data"]["status"] == "draft"
        assert pg_client.get(f"/api/v1/briefings/{PROBE_DAY}").status_code == 404
        assert pg_client.get(f"/api/v1/stories/{PROBE_STORY_A}").status_code == 404

        audit = pg_client.get("/api/v1/admin/audit", headers=headers)
        assert audit.status_code == 200
        items = audit.json()["data"]["items"]
        actions = {row["action"] for row in items}
        assert "topic.create" in actions
        assert "briefing.publish" in actions
        assert "story.create" in actions
        dumped_audit = json.dumps(items)
        assert "password_hash" not in dumped_audit
        assert "token_hash" not in dumped_audit
        assert "actor_id" not in dumped_audit
        create = next(row for row in items if row["action"] == "topic.create" and row["resource"] == f"topics/{PROBE_TOPIC}")
        assert create["actorEmail"] == ADMIN_EMAIL

        deleted = pg_client.delete(f"/api/v1/admin/briefings/{PROBE_DAY}", headers=headers)
        assert deleted.status_code == 200
        assert deleted.json() == {"data": {"ok": True}}
        assert pg_client.get(f"/api/v1/admin/briefings/{PROBE_DAY}", headers=headers).status_code == 404
        assert pg_client.get(f"/api/v1/admin/stories/{PROBE_STORY_A}", headers=headers).status_code == 404

        gone_topic = pg_client.delete(f"/api/v1/admin/topics/{PROBE_TOPIC}", headers=headers)
        assert gone_topic.status_code == 200
        gone_source = pg_client.delete(f"/api/v1/admin/sources/{PROBE_SOURCE}", headers=headers)
        assert gone_source.status_code == 200
    finally:
        pg_client.app.state.limiter.reset()
        _wipe_probe(pg_client, token)

    today = pg_client.get("/api/v1/briefings/today")
    assert today.status_code == 200
    data = today.json()["data"]
    assert data["date"] == "2026-09-14"
    assert [row["slug"] for row in data["mustRead"]] == MUST_SLUGS
    assert [row["slug"] for row in data["more"]] == MORE_SLUGS
    assert data["pulse"]["totalSources"] == 26
    assert data["pulse"]["clusters"] == 14
    topics = pg_client.get("/api/v1/topics").json()["data"]["items"]
    assert len(topics) == 10
    assert PROBE_TOPIC not in [row["slug"] for row in topics]


def test_pg_refresh_replay_revokes_family(pg_client: TestClient) -> None:
    access, refresh = _login(pg_client)
    rotated = pg_client.post("/api/v1/auth/refresh", json={"refreshToken": refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["data"]["refreshToken"]
    replay = pg_client.post("/api/v1/auth/refresh", json={"refreshToken": refresh})
    assert replay.status_code == 401
    assert replay.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid refresh token."}}
    family = pg_client.post("/api/v1/auth/refresh", json={"refreshToken": new_refresh})
    assert family.status_code == 401
    audit = pg_client.get("/api/v1/admin/audit", headers=_h(access))
    assert audit.status_code == 200
    actions = [row["action"] for row in audit.json()["data"]["items"]]
    assert "refresh_replay" in actions

    unknown = pg_client.post("/api/v1/auth/refresh", json={"refreshToken": "totally-unknown-refresh-token"})
    assert unknown.status_code == 401


def test_pg_admin_story_filters(pg_client: TestClient) -> None:
    token, _refresh = _login(pg_client)
    headers = _h(token)
    listing = pg_client.get("/api/v1/admin/stories", headers=headers, params={"date": "2026-09-14"})
    assert listing.status_code == 200
    slugs = [row["slug"] for row in listing.json()["data"]["items"]]
    assert slugs[:8] == MUST_SLUGS
    empty = pg_client.get(
        "/api/v1/admin/stories",
        headers=headers,
        params={"topic": "does-not-exist"},
    )
    assert empty.status_code == 200
    assert empty.json() == {"data": {"items": []}}
    bad = pg_client.get("/api/v1/admin/stories", headers=headers, params={"date": "20260914"})
    assert bad.status_code == 422

    seed_more = pg_client.get("/api/v1/admin/stories/hf-free-tier", headers=headers)
    assert seed_more.status_code == 200
    assert seed_more.json()["data"]["rank"] is None
    public_seed = pg_client.get("/api/v1/stories/hf-free-tier")
    assert public_seed.status_code == 200
    assert public_seed.json()["data"]["rank"] is None
    assert "sourceCode" not in json.dumps(public_seed.json())

    wired = pg_client.get("/api/v1/admin/stories/claude-memory", headers=headers)
    names = {row["name"]: row["sourceCode"] for row in wired.json()["data"]["sources"]}
    assert names["Wired"] is None
    public_wired = pg_client.get("/api/v1/stories/claude-memory")
    assert all("sourceCode" not in row for row in public_wired.json()["data"]["sources"])


def test_pg_cannot_delete_seed_published_or_cited(pg_client: TestClient) -> None:
    token, _refresh = _login(pg_client)
    headers = _h(token)
    published_delete = pg_client.delete("/api/v1/admin/briefings/2026-09-14", headers=headers)
    assert published_delete.status_code == 409
    assert published_delete.json() == {
        "error": {"code": "CONFLICT", "message": "Cannot delete a published briefing."}
    }
    blocked_topic = pg_client.delete("/api/v1/admin/topics/models", headers=headers)
    assert blocked_topic.status_code == 409
    blocked_source = pg_client.delete("/api/v1/admin/sources/openai-blog", headers=headers)
    assert blocked_source.status_code == 409
    lab = pg_client.get("/api/v1/admin/sources/lab-rss", headers=headers)
    assert lab.status_code == 200
    data = lab.json()["data"]
    assert data["consecutiveFailures"] == 2
    assert data["isQuarantined"] is True
    public = pg_client.get("/api/v1/sources")
    row = next(item for item in public.json()["data"]["items"] if item["id"] == "lab-rss")
    assert set(row) == PUBLIC_SOURCE_KEYS
    today = pg_client.get("/api/v1/briefings/today")
    assert today.json()["data"]["date"] == "2026-09-14"
    assert today.json()["data"]["pulse"]["totalSources"] == 26
