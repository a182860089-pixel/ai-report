from __future__ import annotations

import time
from collections import defaultdict, deque

from app.domain.exceptions import AppError


class InProcessRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def check(self, bucket: str, ip: str, limit: int, window: float = 60.0) -> None:
        now = time.monotonic()
        key = (bucket, ip)
        q = self._hits[key]
        cutoff = now - window
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= limit:
            retry_after = max(1, int(window - (now - q[0])) + 1)
            raise AppError(429, "RATE_LIMITED", "Too many requests.", retry_after=retry_after)
        q.append(now)


def limit_for(method: str, path: str) -> tuple[str, int] | None:
    if path in {"/healthz", "/readyz"}:
        return None
    if method == "OPTIONS":
        return None
    if method == "GET" and path == "/api/v1/search":
        return ("search", 10)
    if method == "POST" and path == "/api/v1/auth/login":
        return ("login", 5)
    if method == "POST" and path == "/api/v1/auth/refresh":
        return ("refresh", 20)
    if method in {"POST", "PATCH", "DELETE"} and path.startswith("/api/v1/admin/"):
        return ("admin_write", 20)
    if method == "GET" and path.startswith("/api/v1/"):
        return ("get", 60)
    if method == "POST" and path.startswith("/api/v1/"):
        return ("post", 60)
    return None
