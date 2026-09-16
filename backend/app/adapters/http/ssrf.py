from __future__ import annotations

import asyncio
import ipaddress
import socket
import ssl
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

from app.domain.entities import HttpFetchResult
from app.domain.interfaces import HttpFetcher

MAX_BYTES = 1_048_576
TIMEOUT = 5.0
MAX_REDIRECTS = 3
USER_AGENT = "ai-report-fetcher/1.0"
CGNAT = ipaddress.ip_network("100.64.0.0/10")
METADATA_V4 = ipaddress.ip_address("169.254.169.254")
METADATA_V6 = ipaddress.ip_address("fd00:ec2::254")

Resolver = Callable[..., list]
Opener = Callable[[str, str, str, float], tuple[int, dict[str, str], bytes, bool]]


def blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        if blocked_ip(ip.ipv4_mapped):
            return True
    if ip in {METADATA_V4, METADATA_V6}:
        return True
    if isinstance(ip, ipaddress.IPv4Address) and ip in CGNAT:
        return True
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


def _result(
    *,
    url: str,
    status: str,
    http_status: int | None = None,
    body: bytes = b"",
    content_type: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    bytes_read: int = 0,
    truncated: bool = False,
) -> HttpFetchResult:
    return HttpFetchResult(
        url=url,
        status=status,
        http_status=http_status,
        body=body,
        content_type=content_type,
        error_code=error_code,
        error_message=error_message,
        bytes_read=bytes_read,
        truncated=truncated,
    )


class SsrfHttpClient(HttpFetcher):
    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        opener: Opener | None = None,
        timeout: float = TIMEOUT,
        max_bytes: int = MAX_BYTES,
        max_redirects: int = MAX_REDIRECTS,
    ) -> None:
        self.resolver = resolver or socket.getaddrinfo
        self.opener = opener
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects

    async def fetch(self, url: str) -> HttpFetchResult:
        return await asyncio.to_thread(self._fetch_sync, url)

    def _fetch_sync(self, url: str) -> HttpFetchResult:
        current = url
        hops = 0
        seen: set[str] = set()
        while True:
            parsed = self._validate_url(current)
            if isinstance(parsed, HttpFetchResult):
                return parsed
            host, path = parsed
            if current in seen:
                return _result(
                    url=current,
                    status="blocked",
                    error_code="SSRF_BLOCKED",
                    error_message="Redirect loop.",
                )
            seen.add(current)
            try:
                addrs = self._resolve(host)
            except TimeoutError:
                return _result(url=current, status="error", error_code="TIMEOUT", error_message="Timed out.")
            except OSError as exc:
                return _result(
                    url=current,
                    status="error",
                    error_code="NETWORK_ERROR",
                    error_message=str(exc)[:200],
                )
            except Exception as exc:
                return _result(
                    url=current,
                    status="error",
                    error_code="NETWORK_ERROR",
                    error_message=str(exc)[:200],
                )
            if not addrs or any(blocked_ip(item) for item in addrs):
                return _result(
                    url=current,
                    status="blocked",
                    error_code="SSRF_BLOCKED",
                    error_message="Blocked address.",
                )
            ip = str(addrs[0])
            try:
                status, headers, body, truncated = self._open(host, ip, path)
            except TimeoutError:
                return _result(url=current, status="error", error_code="TIMEOUT", error_message="Timed out.")
            except ssl.SSLError as exc:
                return _result(
                    url=current,
                    status="error",
                    error_code="TLS_ERROR",
                    error_message=str(exc)[:200],
                )
            except OSError as exc:
                if isinstance(exc, TimeoutError) or exc.__class__.__name__ == "timeout":
                    return _result(url=current, status="error", error_code="TIMEOUT", error_message="Timed out.")
                return _result(
                    url=current,
                    status="error",
                    error_code="NETWORK_ERROR",
                    error_message=str(exc)[:200],
                )
            except Exception as exc:
                return _result(
                    url=current,
                    status="error",
                    error_code="NETWORK_ERROR",
                    error_message=str(exc)[:200],
                )
            header_map = {str(key).lower(): value for key, value in headers.items()}
            if status in {301, 302, 303, 307, 308}:
                location = header_map.get("location")
                if not location:
                    return _result(
                        url=current,
                        status="error",
                        http_status=status,
                        error_code="HTTP_ERROR",
                        error_message="Missing Location.",
                        bytes_read=len(body),
                        truncated=truncated,
                    )
                hops += 1
                if hops > self.max_redirects:
                    return _result(
                        url=current,
                        status="error",
                        http_status=status,
                        error_code="REDIRECT_LIMIT",
                        error_message="Too many redirects.",
                    )
                current = urljoin(current, location)
                continue
            content_type = header_map.get("content-type")
            bytes_read = min(len(body), self.max_bytes)
            clipped = body[: self.max_bytes]
            if status < 200 or status >= 300:
                return _result(
                    url=current,
                    status="error",
                    http_status=status,
                    body=clipped,
                    content_type=content_type,
                    error_code="HTTP_ERROR",
                    error_message=f"HTTP {status}.",
                    bytes_read=bytes_read,
                    truncated=truncated,
                )
            return _result(
                url=current,
                status="ok",
                http_status=status,
                body=clipped,
                content_type=content_type,
                bytes_read=bytes_read,
                truncated=truncated,
            )

    def _validate_url(self, url: str) -> tuple[str, str] | HttpFetchResult:
        try:
            parsed = urlparse(url)
        except Exception:
            return _result(url=url, status="blocked", error_code="SSRF_BLOCKED", error_message="Invalid URL.")
        if parsed.scheme.lower() != "https":
            return _result(url=url, status="blocked", error_code="SSRF_BLOCKED", error_message="HTTPS only.")
        if parsed.username is not None or parsed.password is not None:
            return _result(url=url, status="blocked", error_code="SSRF_BLOCKED", error_message="Userinfo blocked.")
        if parsed.port not in (None, 443):
            return _result(url=url, status="blocked", error_code="SSRF_BLOCKED", error_message="Port blocked.")
        host = parsed.hostname
        if not host:
            return _result(url=url, status="blocked", error_code="SSRF_BLOCKED", error_message="Missing host.")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            return _result(url=url, status="blocked", error_code="SSRF_BLOCKED", error_message="IP literal blocked.")
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return host, path

    def _resolve(self, host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        infos = self.resolver(host, 443, type=socket.SOCK_STREAM)
        addrs: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        for info in infos:
            sockaddr = info[4]
            addrs.append(ipaddress.ip_address(sockaddr[0]))
        return addrs

    def _open(self, host: str, ip: str, path: str) -> tuple[int, dict[str, str], bytes, bool]:
        if self.opener is not None:
            return self.opener(host, ip, path, self.timeout)
        return self._default_open(host, ip, path)

    def _default_open(self, host: str, ip: str, path: str) -> tuple[int, dict[str, str], bytes, bool]:
        import http.client

        context = ssl.create_default_context()
        sock = socket.create_connection((ip, 443), timeout=self.timeout)
        tls = context.wrap_socket(sock, server_hostname=host)
        conn = http.client.HTTPSConnection(host, 443, timeout=self.timeout, context=context)
        try:
            conn.sock = tls
            conn.request(
                "GET",
                path,
                headers={
                    "Host": host,
                    "User-Agent": USER_AGENT,
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
                },
            )
            resp = conn.getresponse()
            raw = resp.read(self.max_bytes + 1)
            truncated = len(raw) > self.max_bytes
            body = raw[: self.max_bytes]
            headers = {key.lower(): value for key, value in resp.getheaders()}
            return resp.status, headers, body, truncated
        finally:
            conn.close()
