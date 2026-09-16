from __future__ import annotations

from datetime import date

TODAY_TITLE_ZH = "\u53d1\u5e03\u5468\u5bf9\u649e\uff1a\u95ed\u6e90\u964d\u4ef7\uff0c\u5f00\u6e90\u62a2\u699c"
DAY1_TITLE_ZH = "\u65b0\u57fa\u51c6\u5468\u62c9\u5f00\uff1a\u5e7b\u89c9\u88ab\u62c6\u5f00\u6253\u5206"
LLAMA_TITLE_ZH = "Llama 4.1 8B\uff1a\u624b\u673a\u7aef 30 tok/s"
QUANTUM = "\u91cf\u5b50\u4f4d"
DASH = "\u2014"

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
MODEL_STORY_SLUGS = [
    "gpt-55-price",
    "claude-memory",
    "20260911-03-models",
    "20260909-02-models",
    "20260903-02-models",
]


def test_healthz_does_not_touch_db(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}


def test_readyz_memory_is_ready(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ready"}}


def test_meta_current_date(client):
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    assert response.json() == {
        "data": {"currentDate": "2026-09-14", "timezone": "Asia/Shanghai"}
    }


def test_today_briefing_shape_and_seed(client):
    response = client.get("/api/v1/briefings/today")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["date"] == "2026-09-14"
    assert data["title"]["zh"] == TODAY_TITLE_ZH
    assert data["updatedAt"] == "07:12"
    assert data["pulse"] == {
        "clusters": 14,
        "articles": 86,
        "zhEn": "4 : 3",
        "healthy": 24,
        "totalSources": 26,
        "topics": data["pulse"]["topics"],
    }
    assert data["pulse"]["totalSources"] == 26
    assert data["pulse"]["clusters"] == 14
    assert [row["slug"] for row in data["mustRead"]] == MUST_SLUGS
    assert [row["rank"] for row in data["mustRead"]] == list(range(1, 9))
    assert all(row["section"] == "must" for row in data["mustRead"])
    llama = data["mustRead"][4]
    assert llama["slug"] == "llama-41-8b"
    assert llama["rank"] == 5
    assert llama["section"] == "must"
    assert llama["title"]["zh"] == LLAMA_TITLE_ZH
    assert llama["title"]["en"] == "Llama 4.1 8B: 30 tok/s on phones"
    assert llama["sourceNames"] == ["Meta", "GitHub", QUANTUM]
    assert llama["sourceCount"] == 3
    assert [row["slug"] for row in data["more"]] == MORE_SLUGS
    assert all(row["section"] == "more" and row["rank"] is None for row in data["more"])
    assert "llama-41-8b" not in [row["slug"] for row in data["more"]]


def test_briefing_by_date_and_empty_day(client):
    ok = client.get("/api/v1/briefings/2026-09-01")
    assert ok.status_code == 200
    data = ok.json()["data"]
    assert data["title"]["zh"] == DAY1_TITLE_ZH
    assert data["updatedAt"] == "07:08"
    assert data["pulse"]["clusters"] == 11
    missing = client.get("/api/v1/briefings/2099-01-01")
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {"code": "NOT_FOUND", "message": "No briefing for this date."}
    }


def test_archive_range(client):
    response = client.get("/api/v1/briefings", params={"from": "2026-09-01", "to": "2026-09-14"})
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [row["date"] for row in items] == [f"2026-09-{day:02d}" for day in range(1, 15)]
    first = items[0]
    last = items[-1]
    assert first["mustReadCount"] == 2
    assert first["clusters"] == 11
    assert last["mustReadCount"] == 8
    assert last["clusters"] == 14


def test_story_claude_memory(client):
    response = client.get("/api/v1/stories/claude-memory")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["slug"] == "claude-memory"
    assert data["section"] == "must"
    assert data["rank"] == 2
    assert len(data["synthesis"]) >= 2
    assert len(data["timeline"]) == 4
    assert data["timeline"][0]["time"] == "06:28"
    assert [row["name"] for row in data["sources"]] == [
        "Anthropic News",
        "Wired",
        "36\u6c2a",
        "The Information",
    ]
    unknown = client.get("/api/v1/stories/no-such-cluster")
    assert unknown.status_code == 404
    assert unknown.json() == {"error": {"code": "NOT_FOUND", "message": "Unknown cluster."}}


def test_topics_and_models_detail(client):
    listing = client.get("/api/v1/topics")
    assert listing.status_code == 200
    items = listing.json()["data"]["items"]
    assert len(items) == 10
    assert items[0]["slug"] == "models"
    assert items[0]["clusterCount"] == 5
    assert sum(row["clusterCount"] for row in items) == 53
    detail = client.get("/api/v1/topics/models")
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["clusterCount"] == 5
    assert [row["slug"] for row in data["stories"]] == MODEL_STORY_SLUGS
    missing = client.get("/api/v1/topics/not-a-topic")
    assert missing.status_code == 404
    assert missing.json() == {"error": {"code": "NOT_FOUND", "message": "Unknown topic."}}


def test_sources_order_and_lab_rss(client):
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 12
    assert items[0]["id"] == "openai-blog"
    lab = items[-1]
    assert lab["id"] == "lab-rss"
    assert lab["status"] == "bad"
    assert lab["lastFetch"] == DASH
    assert all(isinstance(row["id"], str) for row in items)


def test_search_claude(client):
    response = client.get("/api/v1/search", params={"q": "Claude"})
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["query"] == "Claude"
    slugs = [row["slug"] for row in payload["items"]]
    assert "claude-memory" in slugs
    dates = [row["date"] for row in payload["items"]]
    assert dates == sorted(dates, reverse=True)


def test_validation_errors(client):
    q = client.get("/api/v1/search", params={"q": "x" * 101})
    assert q.status_code == 422
    assert q.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Invalid query."}}
    missing_q = client.get("/api/v1/search")
    assert missing_q.status_code == 422
    assert missing_q.json()["error"]["message"] == "Invalid query."
    bad_date = client.get("/api/v1/briefings/2026-13-01")
    assert bad_date.status_code == 422
    assert bad_date.json() == {
        "error": {"code": "VALIDATION_ERROR", "message": "Invalid date. Use YYYY-MM-DD."}
    }
    compact = client.get("/api/v1/briefings/20260914")
    assert compact.status_code == 422
    bad_slug = client.get("/api/v1/stories/Not_A_Slug")
    assert bad_slug.status_code == 422
    assert bad_slug.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Invalid slug."}}
    bad_range = client.get("/api/v1/briefings", params={"from": "2026-09-14", "to": "2026-09-01"})
    assert bad_range.status_code == 422
    assert bad_range.json() == {
        "error": {"code": "VALIDATION_ERROR", "message": "Invalid date range."}
    }


def test_draft_briefing_is_hidden(client):
    client.app.state.world.add_draft_briefing(date(2099, 1, 1))
    assert client.get("/api/v1/briefings/2099-01-01").status_code == 404
    listing = client.get("/api/v1/briefings", params={"from": "2099-01-01", "to": "2099-01-01"})
    assert listing.status_code == 200
    assert listing.json()["data"]["items"] == []
    story = client.get("/api/v1/stories/draft-2099-01-01")
    assert story.status_code == 404
    today = client.get("/api/v1/briefings/today")
    assert today.status_code == 200
    assert today.json()["data"]["date"] == "2026-09-14"


def test_memory_world_story_count(client):
    assert len(client.app.state.world.story_records) == 53