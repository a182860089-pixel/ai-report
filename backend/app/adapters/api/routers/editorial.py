from __future__ import annotations

from fastapi import APIRouter, Request

from app.adapters.api.deps import public_reads
from app.adapters.api.presenters import briefing_list_item_out, briefing_out, story_out, summary_out
from app.adapters.api.validate import parse_date, parse_date_range, parse_search_query, parse_slug

router = APIRouter()


@router.get("/meta")
async def meta(request: Request) -> dict:
    return {"data": await public_reads(request).meta()}


@router.get("/briefings/today")
async def briefing_today(request: Request) -> dict:
    return {"data": briefing_out(await public_reads(request).today())}


@router.get("/briefings")
async def list_briefings(request: Request) -> dict:
    start, end = parse_date_range(request.query_params.get("from"), request.query_params.get("to"))
    items = await public_reads(request).list_briefings(start, end)
    return {"data": {"items": [briefing_list_item_out(item) for item in items]}}


@router.get("/briefings/{date}")
async def briefing_by_date(date: str, request: Request) -> dict:
    day = parse_date(date)
    return {"data": briefing_out(await public_reads(request).briefing(day))}


@router.get("/stories/{slug}")
async def story_detail(slug: str, request: Request) -> dict:
    parsed = parse_slug(slug)
    return {"data": story_out(await public_reads(request).story(parsed))}


@router.get("/search")
async def search(request: Request) -> dict:
    cleaned = parse_search_query(request.query_params.get("q"), present="q" in request.query_params)
    if cleaned is None:
        return {"data": {"query": "", "items": []}}
    items = await public_reads(request).search(cleaned)
    return {"data": {"query": cleaned, "items": [summary_out(item) for item in items]}}
