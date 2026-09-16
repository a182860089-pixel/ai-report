from __future__ import annotations

from fastapi import APIRouter, Request

from app.adapters.api.deps import auth_uc, settings
from app.adapters.api.middleware import client_ip
from app.adapters.api.validate import bearer_token, parse_login, parse_refresh, read_json, require_bearer

router = APIRouter()


def _ctx(request: Request) -> tuple[str, str | None]:
    return client_ip(request, settings(request).trust_proxy), request.headers.get("user-agent")


@router.post("/auth/login")
async def login(request: Request) -> dict:
    email, password = parse_login(await read_json(request, required=True))
    ip, ua = _ctx(request)
    payload = await auth_uc(request).login(email, password, ip, ua)
    return {"data": payload}


@router.post("/auth/refresh")
async def refresh(request: Request) -> dict:
    token = parse_refresh(await read_json(request, required=True))
    ip, ua = _ctx(request)
    payload = await auth_uc(request).refresh(token, ip, ua)
    return {"data": payload}


@router.post("/auth/logout")
async def logout(request: Request) -> dict:
    body = await read_json(request, required=False)
    refresh_token = body.get("refreshToken") if isinstance(body.get("refreshToken"), str) else None
    if refresh_token == "":
        refresh_token = None
    ip, ua = _ctx(request)
    payload = await auth_uc(request).logout(bearer_token(request), refresh_token, ip, ua)
    return {"data": payload}


@router.get("/admin/me")
async def me(request: Request) -> dict:
    payload = await auth_uc(request).me(require_bearer(request))
    return {"data": payload}