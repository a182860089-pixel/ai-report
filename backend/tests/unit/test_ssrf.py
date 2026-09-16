from __future__ import annotations

import asyncio
import ipaddress
import socket

from app.adapters.http.ssrf import SsrfHttpClient, blocked_ip


def _fetch(client: SsrfHttpClient, url: str):
    return asyncio.run(client.fetch(url))


def _resolver(mapping: dict[str, str]):
    def resolver(host, port, *args, **kwargs):
        ip = mapping[host]
        version = ipaddress.ip_address(ip)
        family = socket.AF_INET6 if version.version == 6 else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 0, "", (ip, port))]

    return resolver


def test_blocked_ip_covers_private_cgnat_metadata():
    assert blocked_ip(ipaddress.ip_address("10.0.0.1"))
    assert blocked_ip(ipaddress.ip_address("127.0.0.1"))
    assert blocked_ip(ipaddress.ip_address("192.168.1.1"))
    assert blocked_ip(ipaddress.ip_address("169.254.169.254"))
    assert blocked_ip(ipaddress.ip_address("100.64.0.1"))
    assert blocked_ip(ipaddress.ip_address("fd00:ec2::254"))
    assert blocked_ip(ipaddress.ip_address("::ffff:10.1.2.3"))
    assert not blocked_ip(ipaddress.ip_address("1.1.1.1"))


def test_https_only_userinfo_port_and_ip_literal_never_open():
    opened: list[tuple[str, str, str]] = []

    def opener(host, ip, path, timeout):
        opened.append((host, ip, path))
        raise AssertionError("opener must not run")

    client = SsrfHttpClient(resolver=_resolver({}), opener=opener)
    urls = (
        "http://example.com/feed",
        "https://user:pass@example.com/feed",
        "https://example.com:8443/feed",
        "https://8.8.8.8/feed",
        "https://169.254.169.254/latest",
    )
    for url in urls:
        result = _fetch(client, url)
        assert result.status == "blocked"
        assert result.error_code == "SSRF_BLOCKED"
    assert opened == []


def test_private_and_cgnat_dns_blocked_before_open():
    opened: list[str] = []

    def opener(host, ip, path, timeout):
        opened.append(ip)
        raise AssertionError("must not connect")

    private = SsrfHttpClient(resolver=_resolver({"evil.example": "10.0.0.8"}), opener=opener)
    private_result = _fetch(private, "https://evil.example/rss.xml")
    assert private_result.status == "blocked"
    assert private_result.error_code == "SSRF_BLOCKED"

    cgnat = SsrfHttpClient(resolver=_resolver({"cgnat.example": "100.64.1.2"}), opener=opener)
    cgnat_result = _fetch(cgnat, "https://cgnat.example/rss")
    assert cgnat_result.status == "blocked"
    assert cgnat_result.error_code == "SSRF_BLOCKED"
    assert opened == []


def test_redirect_to_private_is_blocked():
    opened: list[str] = []

    def opener(host, ip, path, timeout):
        opened.append(host)
        if host == "good.example":
            return 302, {"Location": "https://evil.example/secret"}, b"", False
        raise AssertionError("must not open private hop")

    client = SsrfHttpClient(
        resolver=_resolver({"good.example": "1.2.3.4", "evil.example": "10.0.0.1"}),
        opener=opener,
    )
    result = _fetch(client, "https://good.example/feed")
    assert result.status == "blocked"
    assert result.error_code == "SSRF_BLOCKED"
    assert opened == ["good.example"]


def test_redirect_limit():
    def opener(host, ip, path, timeout):
        n = int(path.strip("/").replace("r", "") or "0")
        return 302, {"location": f"https://good.example/r{n + 1}"}, b"", False

    client = SsrfHttpClient(resolver=_resolver({"good.example": "1.2.3.4"}), opener=opener)
    result = _fetch(client, "https://good.example/r0")
    assert result.status == "error"
    assert result.error_code == "REDIRECT_LIMIT"


def test_ok_fetch_uses_resolved_ip_and_injected_opener():
    opened: list[tuple[str, str, str, float]] = []

    def opener(host, ip, path, timeout):
        opened.append((host, ip, path, timeout))
        body = b"<rss><channel></channel></rss>"
        return 200, {"content-type": "application/rss+xml"}, body, False

    client = SsrfHttpClient(resolver=_resolver({"feeds.example": "9.9.9.9"}), opener=opener)
    result = _fetch(client, "https://feeds.example/rss.xml")
    assert result.status == "ok"
    assert result.http_status == 200
    assert result.body.startswith(b"<rss")
    assert opened == [("feeds.example", "9.9.9.9", "/rss.xml", 5.0)]


def test_http_error_from_opener():
    def opener(host, ip, path, timeout):
        return 404, {"content-type": "text/plain"}, b"nope", False

    client = SsrfHttpClient(resolver=_resolver({"feeds.example": "9.9.9.9"}), opener=opener)
    result = _fetch(client, "https://feeds.example/missing")
    assert result.status == "error"
    assert result.error_code == "HTTP_ERROR"
    assert result.http_status == 404