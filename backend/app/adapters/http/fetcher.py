from __future__ import annotations

from app.domain.entities import HttpFetchResult
from app.domain.interfaces import HttpFetcher


class DisabledHttpFetcher(HttpFetcher):
    async def fetch(self, url: str) -> HttpFetchResult:
        return HttpFetchResult(
            url=url,
            status="blocked",
            http_status=None,
            body=b"",
            content_type=None,
            error_code="NETWORK_DISABLED",
            error_message="Network disabled.",
            bytes_read=0,
            truncated=False,
        )


class FakeHttpFetcher(HttpFetcher):
    def __init__(self, responses: dict[str, HttpFetchResult] | None = None) -> None:
        self.responses = dict(responses or {})
        self.calls: list[str] = []

    def add(self, url: str, result: HttpFetchResult) -> None:
        self.responses[url] = result

    async def fetch(self, url: str) -> HttpFetchResult:
        self.calls.append(url)
        found = self.responses.get(url)
        if found is not None:
            return found
        return HttpFetchResult(
            url=url,
            status="error",
            http_status=None,
            body=b"",
            content_type=None,
            error_code="HTTP_ERROR",
            error_message="No fake response.",
            bytes_read=0,
            truncated=False,
        )
