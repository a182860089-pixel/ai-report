from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.adapters.api.errors import error_response
from app.adapters.api.rate_limit import InProcessRateLimiter, limit_for
from app.adapters.api.validate import REQUEST_ID_RE
from app.config import Settings
from app.domain.exceptions import AppError

log = logging.getLogger("ai_report")


def client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id", "")
        if not REQUEST_ID_RE.fullmatch(request_id):
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Request-ID"] = request_id
        path = request.url.path
        if path.startswith("/api/v1/auth") or path.startswith("/api/v1/admin") or path == "/api/v1/search":
            response.headers["Cache-Control"] = "no-store"
        elif request.method == "GET" and path.startswith("/api/v1/"):
            response.headers.setdefault("Cache-Control", "public, max-age=30")
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        https = request.url.scheme == "https" or (
            self.settings.trust_proxy and forwarded_proto.lower() == "https"
        )
        if https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        duration_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%s ip=%s",
            request_id,
            request.method,
            path,
            response.status_code,
            duration_ms,
            client_ip(request, self.settings.trust_proxy),
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings, limiter: InProcessRateLimiter) -> None:
        super().__init__(app)
        self.settings = settings
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        spec = limit_for(request.method, request.url.path)
        if spec is not None:
            bucket, limit = spec
            ip = client_ip(request, self.settings.trust_proxy)
            try:
                self.limiter.check(bucket, ip, limit)
            except AppError as exc:
                return error_response(exc.status, exc.code, exc.message, exc.retry_after)
        return await call_next(request)