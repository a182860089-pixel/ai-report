from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.adapters.api.deps import admin_uc, auth_uc, settings
from app.adapters.api.middleware import client_ip
from app.adapters.api.presenters import (
    admin_briefing_list_item_out,
    admin_briefing_out,
    admin_source_out,
    admin_story_out,
    admin_topic_detail_out,
    admin_topic_list_item_out,
    audit_out,
    summary_out,
)
from app.adapters.api.validate import (
    ADMIN_MAX_BODY,
    parse_audit_limit,
    parse_date,
    parse_date_range,
    parse_slug,
    read_json,
    require_bearer,
)

router = APIRouter()


async def _require_admin(request: Request):
    admin = await auth_uc(request).require_admin(require_bearer(request))
    ip = client_ip(request, settings(request).trust_proxy)
    ua = request.headers.get("user-agent")
    return admin, ip, ua


@router.get("/admin/topics")
async def list_topics(request: Request) -> dict:
    await _require_admin(request)
    items = await admin_uc(request).list_topics()
    return {"data": {"items": [admin_topic_list_item_out(item) for item in items]}}


@router.get("/admin/topics/{slug}")
async def get_topic(slug: str, request: Request) -> dict:
    await _require_admin(request)
    parsed = parse_slug(slug, max_len=64)
    return {"data": admin_topic_detail_out(await admin_uc(request).get_topic(parsed))}


@router.post("/admin/topics")
async def create_topic(request: Request) -> JSONResponse:
    admin, ip, ua = await _require_admin(request)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    topic = await admin_uc(request).create_topic(payload, admin, ip, ua)
    return JSONResponse({"data": admin_topic_list_item_out(topic)}, status_code=201)


@router.patch("/admin/topics/{slug}")
async def update_topic(slug: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    parsed = parse_slug(slug, max_len=64)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    topic = await admin_uc(request).update_topic(parsed, payload, admin, ip, ua)
    return {"data": admin_topic_list_item_out(topic)}


@router.delete("/admin/topics/{slug}")
async def delete_topic(slug: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    parsed = parse_slug(slug, max_len=64)
    await admin_uc(request).delete_topic(parsed, admin, ip, ua)
    return {"data": {"ok": True}}


@router.get("/admin/sources")
async def list_sources(request: Request) -> dict:
    await _require_admin(request)
    items = await admin_uc(request).list_sources()
    return {"data": {"items": [admin_source_out(item) for item in items]}}


@router.get("/admin/sources/{code}")
async def get_source(code: str, request: Request) -> dict:
    await _require_admin(request)
    parsed = parse_slug(code, max_len=64)
    return {"data": admin_source_out(await admin_uc(request).get_source(parsed))}


@router.post("/admin/sources")
async def create_source(request: Request) -> JSONResponse:
    admin, ip, ua = await _require_admin(request)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    source = await admin_uc(request).create_source(payload, admin, ip, ua)
    return JSONResponse({"data": admin_source_out(source)}, status_code=201)


@router.patch("/admin/sources/{code}")
async def update_source(code: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    parsed = parse_slug(code, max_len=64)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    source = await admin_uc(request).update_source(parsed, payload, admin, ip, ua)
    return {"data": admin_source_out(source)}


@router.delete("/admin/sources/{code}")
async def delete_source(code: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    parsed = parse_slug(code, max_len=64)
    await admin_uc(request).delete_source(parsed, admin, ip, ua)
    return {"data": {"ok": True}}


@router.get("/admin/briefings")
async def list_briefings(request: Request) -> dict:
    await _require_admin(request)
    start, end = parse_date_range(request.query_params.get("from"), request.query_params.get("to"))
    items = await admin_uc(request).list_briefings(start, end)
    return {"data": {"items": [admin_briefing_list_item_out(item) for item in items]}}


@router.get("/admin/briefings/{date}")
async def get_briefing(date: str, request: Request) -> dict:
    await _require_admin(request)
    day = parse_date(date)
    return {"data": admin_briefing_out(await admin_uc(request).get_briefing(day))}


@router.post("/admin/briefings")
async def create_briefing(request: Request) -> JSONResponse:
    admin, ip, ua = await _require_admin(request)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    briefing = await admin_uc(request).create_briefing(payload, admin, ip, ua)
    return JSONResponse({"data": admin_briefing_out(briefing)}, status_code=201)


@router.patch("/admin/briefings/{date}")
async def update_briefing(date: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    day = parse_date(date)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    briefing = await admin_uc(request).update_briefing(day, payload, admin, ip, ua)
    return {"data": admin_briefing_out(briefing)}


@router.post("/admin/briefings/{date}/publish")
async def publish_briefing(date: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    day = parse_date(date)
    briefing = await admin_uc(request).publish(day, admin, ip, ua)
    return {"data": admin_briefing_out(briefing)}


@router.post("/admin/briefings/{date}/unpublish")
async def unpublish_briefing(date: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    day = parse_date(date)
    briefing = await admin_uc(request).unpublish(day, admin, ip, ua)
    return {"data": admin_briefing_out(briefing)}


@router.delete("/admin/briefings/{date}")
async def delete_briefing(date: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    day = parse_date(date)
    await admin_uc(request).delete_briefing(day, admin, ip, ua)
    return {"data": {"ok": True}}


@router.get("/admin/stories")
async def list_stories(request: Request) -> dict:
    await _require_admin(request)
    date_raw = request.query_params.get("date")
    topic_raw = request.query_params.get("topic")
    day = parse_date(date_raw) if date_raw is not None else None
    topic = parse_slug(topic_raw, max_len=64) if topic_raw is not None else None
    items = await admin_uc(request).list_stories(day, topic)
    return {"data": {"items": [summary_out(item) for item in items]}}


@router.get("/admin/stories/{slug}")
async def get_story(slug: str, request: Request) -> dict:
    await _require_admin(request)
    parsed = parse_slug(slug)
    return {"data": admin_story_out(await admin_uc(request).get_story(parsed))}


@router.post("/admin/stories")
async def create_story(request: Request) -> JSONResponse:
    admin, ip, ua = await _require_admin(request)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    story = await admin_uc(request).create_story(payload, admin, ip, ua)
    return JSONResponse({"data": admin_story_out(story)}, status_code=201)


@router.patch("/admin/stories/{slug}")
async def update_story(slug: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    parsed = parse_slug(slug)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    story = await admin_uc(request).update_story(parsed, payload, admin, ip, ua)
    return {"data": admin_story_out(story)}


@router.delete("/admin/stories/{slug}")
async def delete_story(slug: str, request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    parsed = parse_slug(slug)
    await admin_uc(request).delete_story(parsed, admin, ip, ua)
    return {"data": {"ok": True}}


@router.get("/admin/audit")
async def list_audits(request: Request) -> dict:
    await _require_admin(request)
    limit = parse_audit_limit(request.query_params.get("limit"))
    items = await admin_uc(request).list_audits(limit)
    return {"data": {"items": [audit_out(item) for item in items]}}
