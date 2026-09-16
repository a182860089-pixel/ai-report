from __future__ import annotations

import json
import re
from datetime import date

from starlette.requests import Request

from app.domain.exceptions import AppError

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CTRL_RE = re.compile(r"[\x00-\x1F\x7F]")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
MAX_BODY = 8192
ADMIN_MAX_BODY = 65536


def parse_date(value: str) -> date:
    if not DATE_RE.fullmatch(value):
        raise AppError(422, "VALIDATION_ERROR", "Invalid date. Use YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise AppError(422, "VALIDATION_ERROR", "Invalid date. Use YYYY-MM-DD.") from exc


def parse_date_range(start: str | None, end: str | None) -> tuple[date, date]:
    if not start or not end:
        raise AppError(422, "VALIDATION_ERROR", "Invalid date range.")
    try:
        left = parse_date(start)
        right = parse_date(end)
    except AppError as exc:
        raise AppError(422, "VALIDATION_ERROR", "Invalid date range.") from exc
    if left > right or (right - left).days + 1 > 62:
        raise AppError(422, "VALIDATION_ERROR", "Invalid date range.")
    return left, right


def parse_slug(value: str, *, max_len: int = 80) -> str:
    if not value or len(value) > max_len or not SLUG_RE.fullmatch(value):
        raise AppError(422, "VALIDATION_ERROR", "Invalid slug.")
    return value


def parse_search_query(raw: str | None, *, present: bool) -> str | None:
    if not present:
        raise AppError(422, "VALIDATION_ERROR", "Invalid query.")
    cleaned = CTRL_RE.sub("", raw or "").strip()
    if len(cleaned) > 100:
        raise AppError(422, "VALIDATION_ERROR", "Invalid query.")
    return cleaned or None


def parse_login(payload: dict) -> tuple[str, str]:
    email = payload.get("email")
    password = payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        raise AppError(422, "VALIDATION_ERROR", "Invalid login payload.")
    email = email.strip()
    if not (3 <= len(email) <= 254) or email.count("@") != 1:
        raise AppError(422, "VALIDATION_ERROR", "Invalid login payload.")
    if not (1 <= len(password) <= 256):
        raise AppError(422, "VALIDATION_ERROR", "Invalid login payload.")
    return email, password


def parse_refresh(payload: dict) -> str:
    token = payload.get("refreshToken")
    if not isinstance(token, str) or not token or len(token) > 512:
        raise AppError(422, "VALIDATION_ERROR", "Invalid refresh payload.")
    return token


def parse_optional_date_pair(start: str | None, end: str | None) -> tuple[date | None, date | None]:
    left_missing = start is None or start == ""
    right_missing = end is None or end == ""
    if left_missing and right_missing:
        return None, None
    if left_missing or right_missing:
        raise AppError(422, "VALIDATION_ERROR", "Invalid date range.")
    left = parse_date(start)
    right = parse_date(end)
    if left > right:
        raise AppError(422, "VALIDATION_ERROR", "Invalid date range.")
    return left, right


def parse_audit_limit(raw: str | None) -> int:
    if raw is None or raw == "":
        return 50
    if not raw.isdigit():
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    value = int(raw)
    if value < 1 or value > 200:
        raise AppError(422, "VALIDATION_ERROR", "Invalid payload.")
    return value


async def read_json(request: Request, *, required: bool, max_bytes: int = MAX_BODY) -> dict:
    body = await request.body()
    if len(body) > max_bytes:
        raise AppError(400, "BAD_REQUEST", "Request body too large.")
    if not body:
        if required:
            raise AppError(400, "BAD_REQUEST", "Malformed JSON.")
        return {}
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise AppError(415, "BAD_REQUEST", "Unsupported media type.")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AppError(400, "BAD_REQUEST", "Malformed JSON.") from exc
    if not isinstance(payload, dict):
        raise AppError(400, "BAD_REQUEST", "Malformed JSON.")
    return payload


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def require_bearer(request: Request) -> str:
    token = bearer_token(request)
    if not token:
        raise AppError(401, "UNAUTHORIZED", "Invalid access token.")
    return token
