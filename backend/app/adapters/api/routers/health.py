from __future__ import annotations

from fastapi import APIRouter, Request

from app.adapters.api.deps import public_reads

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    return {"data": {"status": "ok"}}


@router.get("/readyz")
async def readyz(request: Request) -> dict:
    await public_reads(request).ready()
    return {"data": {"status": "ready"}}