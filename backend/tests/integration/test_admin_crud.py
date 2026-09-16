from __future__ import annotations

import json

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, make_client

DRAFT_DAY = "2026-09-15"
PUBLIC_SOURCE_KEYS = {"id", "name", "status", "lastFetch", "todayCount", "detail"}
MUST_SLUGS = [
    "gpt-55-price",
    "claude-memory",
    "kimi-open-weights",
    "gemini-robotics-2",
    "llama-41-8b",
    "rubin-supply",
    "eu-ai-act-phase-2",
    "glm-agent-bench",
]
MORE_SLUGS = ["diffusion-lm-code", "hf-free-tier", "tongyi-cockpit"]


def _login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    return data["accessToken"], data["refreshToken"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _topic_body(**overrides):
    payload = {
        "slug": "eval-tools",
        "name": {"zh": "评测工具", "en": "Eval tools"},
        "blurb": {"zh": "新套件", "en": "New suites"},
        "sortOrder": 20,
    }
    payload.update(overrides)
    return payload


def _source_body(**overrides):
    payload = {
        "id": "papers-with-code",
        "name": "Papers with Code",
        "status": "ok",
        "detail": {"zh": "正常", "en": "Healthy"},
        "lastFetch": "06:00",
        "homepageUrl": "https://paperswithcode.com",
        "feedUrl": None,
    }
    payload.update(overrides)
    return payload


def _briefing_body(**overrides):
    payload = {
        "date": DRAFT_DAY,
        "title": {"zh": "草稿日", "en": "Draft day"},
        "moreHeading": {"zh": "更多", "en": "More"},
        "lede": [{"zh": "要点", "en": "Lede"}],
        "updatedAt": "07:00",
        "pulse": {
            "clusters": 7,
            "articles": 10,
            "zhEn": "1 : 1",
            "healthy": 1,
            "totalSources": 26,
            "topics": [],
        },
    }
    payload.update(overrides)
    return payload


def _story_body(**overrides):
    payload = {
        "slug": "draft-eval-suite",
        "date": DRAFT_DAY,
        "topicSlug": "research",
        "section": "must",
        "rank": 1,
        "title": {"zh": "新评测", "en": "New eval"},
        "dek": {"zh": "摘要", "en": "Dek"},
        "synthesis": [{"zh": "段", "en": "Para"}],
        "timeline": [{"time": "06:00", "text": {"zh": "发生", "en": "Happened"}}],
        "sources": [
            {
                "name": "OpenAI Blog",
                "lang": "en",
                "kind": {"zh": "一手", "en": "Primary"},
                "time": "06:12",
                "sourceCode": "openai-blog",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_admin_write_requires_token():
    with make_client() as client:
        missing = client.post("/api/v1/admin/topics", json=_topic_body())
        assert missing.status_code == 401
        assert missing.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid access token."}}
        bad = client.patch(
            "/api/v1/admin/topics/models",
            headers={"Authorization": "Bearer not-a-jwt"},
            json={"sortOrder": 1},
        )
        assert bad.status_code == 401
        assert bad.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid access token."}}


def test_disabled_account_write_is_403():
    with make_client() as client:
        token, _refresh = _login(client)
        identity = client.app.state.identity
        admin_id = next(iter(identity.admins))
        identity.set_active(admin_id, False)
        response = client.post("/api/v1/admin/topics", headers=_h(token), json=_topic_body())
        assert response.status_code == 403
        assert response.json() == {"error": {"code": "FORBIDDEN", "message": "Account disabled."}}


def test_unknown_field_on_topic_post_is_422():
    with make_client() as client:
        token, _refresh = _login(client)
        response = client.post(
            "/api/v1/admin/topics",
            headers=_h(token),
            json=_topic_body(id=1),
        )
        assert response.status_code == 422
        assert response.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Unknown field."}}


def test_duplicate_slug_code_date_are_409():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        created = client.post("/api/v1/admin/topics", headers=headers, json=_topic_body())
        assert created.status_code == 201
        again = client.post("/api/v1/admin/topics", headers=headers, json=_topic_body())
        assert again.status_code == 409
        assert again.json() == {"error": {"code": "CONFLICT", "message": "Topic slug already exists."}}

        source = client.post("/api/v1/admin/sources", headers=headers, json=_source_body())
        assert source.status_code == 201
        source_again = client.post("/api/v1/admin/sources", headers=headers, json=_source_body())
        assert source_again.status_code == 409
        assert source_again.json() == {"error": {"code": "CONFLICT", "message": "Source code already exists."}}

        briefing = client.post("/api/v1/admin/briefings", headers=headers, json=_briefing_body())
        assert briefing.status_code == 201
        briefing_again = client.post("/api/v1/admin/briefings", headers=headers, json=_briefing_body())
        assert briefing_again.status_code == 409
        assert briefing_again.json() == {
            "error": {"code": "CONFLICT", "message": "Briefing date already exists."}
        }


def test_topic_delete_and_inactive_hides_public():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        blocked = client.delete("/api/v1/admin/topics/models", headers=headers)
        assert blocked.status_code == 409
        assert blocked.json() == {"error": {"code": "CONFLICT", "message": "Topic still has stories."}}

        created = client.post("/api/v1/admin/topics", headers=headers, json=_topic_body())
        assert created.status_code == 201
        assert created.json()["data"]["clusterCount"] == 0
        assert created.json()["data"]["isActive"] is True
        deleted = client.delete("/api/v1/admin/topics/eval-tools", headers=headers)
        assert deleted.status_code == 200
        assert deleted.json() == {"data": {"ok": True}}
        missing = client.get("/api/v1/admin/topics/eval-tools", headers=headers)
        assert missing.status_code == 404

        hidden = client.patch(
            "/api/v1/admin/topics/models",
            headers=headers,
            json={"isActive": False},
        )
        assert hidden.status_code == 200
        assert hidden.json()["data"]["isActive"] is False
        listing = client.get("/api/v1/topics")
        assert listing.status_code == 200
        assert "models" not in [row["slug"] for row in listing.json()["data"]["items"]]
        detail = client.get("/api/v1/topics/models")
        assert detail.status_code == 404
        admin_detail = client.get("/api/v1/admin/topics/models", headers=headers)
        assert admin_detail.status_code == 200
        assert admin_detail.json()["data"]["isActive"] is False
        assert "stories" in admin_detail.json()["data"]


def test_source_citation_block_and_public_has_no_url():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        blocked = client.delete("/api/v1/admin/sources/openai-blog", headers=headers)
        assert blocked.status_code == 409
        assert blocked.json() == {"error": {"code": "CONFLICT", "message": "Source still has citations."}}

        created = client.post(
            "/api/v1/admin/sources",
            headers=headers,
            json=_source_body(),
        )
        assert created.status_code == 201
        assert created.json()["data"]["homepageUrl"] == "https://paperswithcode.com"
        public = client.get("/api/v1/sources")
        assert public.status_code == 200
        dumped = json.dumps(public.json())
        assert "homepageUrl" not in dumped
        assert "feedUrl" not in dumped
        assert "consecutiveFailures" not in dumped
        assert "isQuarantined" not in dumped
        assert all(set(row) == PUBLIC_SOURCE_KEYS for row in public.json()["data"]["items"])


def test_http_source_url_is_422_https_is_stored():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        bad = client.post(
            "/api/v1/admin/sources",
            headers=headers,
            json=_source_body(homepageUrl="http://example.com"),
        )
        assert bad.status_code == 422
        assert bad.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Invalid URL."}}
        ok = client.post(
            "/api/v1/admin/sources",
            headers=headers,
            json=_source_body(id="https-lab", homepageUrl="https://example.com/feed"),
        )
        assert ok.status_code == 201
        assert ok.json()["data"]["homepageUrl"] == "https://example.com/feed"
        public = client.get("/api/v1/sources")
        assert "homepageUrl" not in json.dumps(public.json())
        assert "https://example.com/feed" not in json.dumps(public.json())


def test_lab_rss_admin_fields_hidden_on_public():
    with make_client() as client:
        token, _refresh = _login(client)
        admin = client.get("/api/v1/admin/sources/lab-rss", headers=_h(token))
        assert admin.status_code == 200
        data = admin.json()["data"]
        assert data["id"] == "lab-rss"
        assert data["consecutiveFailures"] == 2
        assert data["isQuarantined"] is True
        public = client.get("/api/v1/sources")
        lab = next(row for row in public.json()["data"]["items"] if row["id"] == "lab-rss")
        assert set(lab) == PUBLIC_SOURCE_KEYS
        assert "consecutiveFailures" not in lab
        assert "isQuarantined" not in lab
        assert "homepageUrl" not in lab


def test_briefing_draft_publish_unpublish_and_delete_rules():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        created = client.post("/api/v1/admin/briefings", headers=headers, json=_briefing_body())
        assert created.status_code == 201
        data = created.json()["data"]
        assert data["status"] == "draft"
        assert data["weekday"] == {"zh": "星期二", "en": "Tuesday"}
        assert data["mustRead"] == []
        assert data["more"] == []
        assert data["pulse"]["clusters"] == 7
        assert client.get(f"/api/v1/briefings/{DRAFT_DAY}").status_code == 404

        published = client.post(f"/api/v1/admin/briefings/{DRAFT_DAY}/publish", headers=headers)
        assert published.status_code == 200
        assert published.json()["data"]["status"] == "published"
        again = client.post(f"/api/v1/admin/briefings/{DRAFT_DAY}/publish", headers=headers)
        assert again.status_code == 200
        visible = client.get(f"/api/v1/briefings/{DRAFT_DAY}")
        assert visible.status_code == 200
        assert visible.json()["data"]["title"]["zh"] == "草稿日"
        assert "status" not in visible.json()["data"]

        unpublished = client.post(f"/api/v1/admin/briefings/{DRAFT_DAY}/unpublish", headers=headers)
        assert unpublished.status_code == 200
        assert unpublished.json()["data"]["status"] == "draft"
        assert client.get(f"/api/v1/briefings/{DRAFT_DAY}").status_code == 404

        published_delete = client.delete("/api/v1/admin/briefings/2026-09-14", headers=headers)
        assert published_delete.status_code == 409
        assert published_delete.json() == {
            "error": {"code": "CONFLICT", "message": "Cannot delete a published briefing."}
        }

        story = client.post("/api/v1/admin/stories", headers=headers, json=_story_body())
        assert story.status_code == 201
        deleted = client.delete(f"/api/v1/admin/briefings/{DRAFT_DAY}", headers=headers)
        assert deleted.status_code == 200
        assert deleted.json() == {"data": {"ok": True}}
        assert client.get(f"/api/v1/admin/briefings/{DRAFT_DAY}", headers=headers).status_code == 404
        assert client.get("/api/v1/admin/stories/draft-eval-suite", headers=headers).status_code == 404
        assert client.get("/api/v1/stories/draft-eval-suite").status_code == 404


def test_draft_story_admin_visible_public_hidden_and_more_rank_null():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        assert client.post("/api/v1/admin/briefings", headers=headers, json=_briefing_body()).status_code == 201
        created = client.post("/api/v1/admin/stories", headers=headers, json=_story_body())
        assert created.status_code == 201
        assert created.json()["data"]["sources"][0]["sourceCode"] == "openai-blog"
        public = client.get("/api/v1/stories/draft-eval-suite")
        assert public.status_code == 404
        admin = client.get("/api/v1/admin/stories/draft-eval-suite", headers=headers)
        assert admin.status_code == 200
        assert admin.json()["data"]["slug"] == "draft-eval-suite"

        more = client.post(
            "/api/v1/admin/stories",
            headers=headers,
            json=_story_body(slug="draft-more-item", section="more", rank=9),
        )
        assert more.status_code == 201
        assert more.json()["data"]["section"] == "more"
        assert more.json()["data"]["rank"] is None

        seed_more = client.get("/api/v1/admin/stories/hf-free-tier", headers=headers)
        assert seed_more.status_code == 200
        assert seed_more.json()["data"]["rank"] is None
        public_seed = client.get("/api/v1/stories/hf-free-tier")
        assert public_seed.status_code == 200
        assert public_seed.json()["data"]["rank"] is None
        assert "sourceCode" not in json.dumps(public_seed.json())

        wired = client.get("/api/v1/admin/stories/claude-memory", headers=headers)
        names = {row["name"]: row["sourceCode"] for row in wired.json()["data"]["sources"]}
        assert names["Wired"] is None
        public_wired = client.get("/api/v1/stories/claude-memory")
        assert all("sourceCode" not in row for row in public_wired.json()["data"]["sources"])


def test_story_rank_rebuild_does_not_rewrite_pulse():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        created = client.post("/api/v1/admin/briefings", headers=headers, json=_briefing_body())
        assert created.status_code == 201
        assert created.json()["data"]["pulse"]["clusters"] == 7
        second = client.post(
            "/api/v1/admin/stories",
            headers=headers,
            json=_story_body(slug="draft-second", rank=2),
        )
        first = client.post(
            "/api/v1/admin/stories",
            headers=headers,
            json=_story_body(slug="draft-first", rank=1),
        )
        assert second.status_code == 201
        assert first.status_code == 201
        briefing = client.get(f"/api/v1/admin/briefings/{DRAFT_DAY}", headers=headers)
        assert briefing.status_code == 200
        data = briefing.json()["data"]
        assert data["pulse"]["clusters"] == 7
        assert data["pulse"]["totalSources"] == 26
        assert [row["slug"] for row in data["mustRead"]] == ["draft-first", "draft-second"]
        assert [row["rank"] for row in data["mustRead"]] == [1, 2]


def test_mutation_writes_audit_without_internal_ids():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        created = client.post("/api/v1/admin/topics", headers=headers, json=_topic_body())
        assert created.status_code == 201
        audit = client.get("/api/v1/admin/audit", headers=headers)
        assert audit.status_code == 200
        items = audit.json()["data"]["items"]
        create = next(row for row in items if row["action"] == "topic.create")
        assert create["resource"] == "topics/eval-tools"
        assert create["actorEmail"] == ADMIN_EMAIL
        assert "actor_id" not in create
        assert "id" not in create
        dumped = json.dumps(items)
        assert "password_hash" not in dumped
        assert "token_hash" not in dumped
        login_row = next(row for row in items if row["action"] == "login")
        assert login_row["actorEmail"] == ADMIN_EMAIL


def test_refresh_replay_revokes_family_and_unknown_hash_is_silent():
    with make_client() as client:
        access, refresh = _login(client)
        rotated = client.post("/api/v1/auth/refresh", json={"refreshToken": refresh})
        assert rotated.status_code == 200
        new_refresh = rotated.json()["data"]["refreshToken"]
        replay = client.post("/api/v1/auth/refresh", json={"refreshToken": refresh})
        assert replay.status_code == 401
        assert replay.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid refresh token."}}
        family = client.post("/api/v1/auth/refresh", json={"refreshToken": new_refresh})
        assert family.status_code == 401
        audit = client.get("/api/v1/admin/audit", headers=_h(access))
        assert audit.status_code == 200
        actions = [row["action"] for row in audit.json()["data"]["items"]]
        assert "refresh_replay" in actions

    with make_client() as clean:
        access, _refresh = _login(clean)
        unknown = clean.post("/api/v1/auth/refresh", json={"refreshToken": "totally-unknown-refresh-token"})
        assert unknown.status_code == 401
        audit = clean.get("/api/v1/admin/audit", headers=_h(access))
        actions = [row["action"] for row in audit.json()["data"]["items"]]
        assert "refresh_replay" not in actions


def test_twenty_first_admin_write_is_429():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        statuses = [
            client.patch("/api/v1/admin/topics/research", headers=headers, json={"sortOrder": 3}).status_code
            for _ in range(20)
        ]
        assert statuses == [200] * 20
        twenty_first = client.patch(
            "/api/v1/admin/topics/research",
            headers=headers,
            json={"sortOrder": 3},
        )
        assert twenty_first.status_code == 429
        assert twenty_first.json() == {"error": {"code": "RATE_LIMITED", "message": "Too many requests."}}
        assert twenty_first.headers.get("Retry-After")


def test_public_seed_today_untouched_on_clean_client():
    with make_client() as client:
        response = client.get("/api/v1/briefings/today")
        assert response.status_code == 200
        data = response.json()["data"]
        assert [row["slug"] for row in data["mustRead"]] == MUST_SLUGS
        assert [row["slug"] for row in data["more"]] == MORE_SLUGS
        assert data["pulse"]["totalSources"] == 26
        assert data["pulse"]["clusters"] == 14
        assert len(client.app.state.world.story_records) == 53


def test_admin_auth_before_invalid_path():
    with make_client() as client:
        missing = client.get("/api/v1/admin/topics/Not_A_Slug")
        assert missing.status_code == 401
        token, _refresh = _login(client)
        invalid = client.get("/api/v1/admin/topics/Not_A_Slug", headers=_h(token))
        assert invalid.status_code == 422
        assert invalid.json()["error"]["message"] == "Invalid slug."


def test_admin_story_filters_and_unknown_topic_is_empty():
    with make_client() as client:
        token, _refresh = _login(client)
        headers = _h(token)
        listing = client.get("/api/v1/admin/stories", headers=headers, params={"date": "2026-09-14"})
        assert listing.status_code == 200
        slugs = [row["slug"] for row in listing.json()["data"]["items"]]
        assert slugs[:8] == MUST_SLUGS
        empty = client.get(
            "/api/v1/admin/stories",
            headers=headers,
            params={"topic": "does-not-exist"},
        )
        assert empty.status_code == 200
        assert empty.json() == {"data": {"items": []}}
        bad = client.get("/api/v1/admin/stories", headers=headers, params={"date": "20260914"})
        assert bad.status_code == 422
