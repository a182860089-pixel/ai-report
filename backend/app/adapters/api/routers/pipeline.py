from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request

from app.adapters.api.deps import pipeline_uc, auth_uc, scheduler, settings
from app.adapters.api.middleware import client_ip
from app.adapters.api.presenters import article_out, cluster_job_out, fetch_run_out, fetch_skip_out, schedule_status_out, scheduled_tick_out
from app.adapters.api.validate import (
    ADMIN_MAX_BODY,
    parse_audit_limit,
    parse_date,
    parse_optional_date_pair,
    parse_slug,
    read_json,
    require_bearer,
)
from app.domain.exceptions import AppError

router = APIRouter()


async def _require_admin(request: Request):
    admin = await auth_uc(request).require_admin(require_bearer(request))
    ip = client_ip(request, settings(request).trust_proxy)
    ua = request.headers.get("user-agent")
    return admin, ip, ua


def _unknown(payload: dict, allowed: set[str]) -> None:
    if set(payload) - allowed:
        raise AppError(422, "VALIDATION_ERROR", "Unknown field.")


def parse_fetch_body(payload: dict) -> list[str] | None:
    _unknown(payload, {"codes"})
    if "codes" not in payload:
        return None
    codes = payload["codes"]
    if not isinstance(codes, list):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    out: list[str] = []
    for item in codes:
        if not isinstance(item, str):
            raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
        out.append(parse_slug(item, max_len=64))
    return out


def parse_cluster_body(payload: dict) -> date:
    _unknown(payload, {"date"})
    if "date" not in payload:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    value = payload["date"]
    if not isinstance(value, str):
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return parse_date(value)


@router.post("/admin/pipeline/fetch")
async def fetch_feeds(request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    payload = await read_json(request, required=False, max_bytes=ADMIN_MAX_BODY)
    codes = parse_fetch_body(payload)
    runs, skipped = await pipeline_uc(request).fetch(codes, admin, ip, ua)
    return {
        "data": {
            "runs": [fetch_run_out(item) for item in runs],
            "skipped": [fetch_skip_out(item) for item in skipped],
        }
    }


@router.get("/admin/pipeline/runs")
async def list_runs(request: Request) -> dict:
    await _require_admin(request)
    limit = parse_audit_limit(request.query_params.get("limit"))
    items = await pipeline_uc(request).list_runs(limit)
    return {"data": {"items": [fetch_run_out(item) for item in items]}}


@router.get("/admin/pipeline/articles")
async def list_articles(request: Request) -> dict:
    await _require_admin(request)
    source_raw = request.query_params.get("source")
    source = parse_slug(source_raw, max_len=64) if source_raw is not None and source_raw != "" else None
    start, end = parse_optional_date_pair(request.query_params.get("from"), request.query_params.get("to"))
    items = await pipeline_uc(request).list_articles(source, start, end)
    return {"data": {"items": [article_out(item) for item in items]}}


@router.post("/admin/pipeline/cluster")
async def cluster_day(request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    payload = await read_json(request, required=True, max_bytes=ADMIN_MAX_BODY)
    day = parse_cluster_body(payload)
    job = await pipeline_uc(request).cluster(day, admin, ip, ua)
    return {"data": cluster_job_out(job, with_slugs=True)}


@router.get("/admin/pipeline/jobs")
async def list_jobs(request: Request) -> dict:
    await _require_admin(request)
    limit = parse_audit_limit(request.query_params.get("limit"))
    items = await pipeline_uc(request).list_jobs(limit)
    return {"data": {"items": [cluster_job_out(item, with_slugs=False) for item in items]}}


@router.get("/admin/pipeline/schedule")
async def pipeline_schedule(request: Request) -> dict:
    await _require_admin(request)
    return {"data": schedule_status_out(scheduler(request).snapshot())}


@router.post("/admin/pipeline/tick")
async def pipeline_tick(request: Request) -> dict:
    admin, ip, ua = await _require_admin(request)
    payload = await read_json(request, required=False, max_bytes=ADMIN_MAX_BODY)
    _unknown(payload, set())
    tick = await scheduler(request).run_tick(admin, trigger="manual", ip=ip, ua=ua)
    return {"data": scheduled_tick_out(tick)}

