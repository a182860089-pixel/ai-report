from __future__ import annotations

from fastapi import APIRouter, Request

from app.adapters.api.deps import public_reads
from app.adapters.api.presenters import source_out, topic_detail_out, topic_list_item_out
from app.adapters.api.validate import parse_slug

router = APIRouter()


@router.get("/topics")
async def list_topics(request: Request) -> dict:
    items = await public_reads(request).topics()
    return {"data": {"items": [topic_list_item_out(item) for item in items]}}


@router.get("/topics/{slug}")
async def topic_detail(slug: str, request: Request) -> dict:
    parsed = parse_slug(slug)
    return {"data": topic_detail_out(await public_reads(request).topic(parsed))}


@router.get("/sources")
async def list_sources(request: Request) -> dict:
    items = await public_reads(request).sources()
    return {"data": {"items": [source_out(item) for item in items]}}