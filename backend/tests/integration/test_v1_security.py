from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, JWT_SECRET, make_client


def _b64url(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def test_search_injection_does_not_500(client):
    for query in ["' OR 1=1", "' OR 1=1 --", "&!|", "foo & bar | baz"]:
        response = client.get("/api/v1/search", params={"q": query})
        assert response.status_code == 200
        assert "error" not in response.json()
        assert isinstance(response.json()["data"]["items"], list)
    slug = client.get("/api/v1/stories/' OR 1=1")
    assert slug.status_code == 422
    assert slug.json()["error"]["message"] == "Invalid slug."


def test_path_traversal_slug_is_422(client):
    # httpx/Starlette collapse /stories/../etc/passwd to /etc/passwd before routing.
    collapsed = client.get("/api/v1/stories/../etc/passwd")
    assert collapsed.status_code in {404, 422}
    assert "traceback" not in collapsed.text.lower()
    response = client.get("/api/v1/stories/..-etc-passwd")
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Invalid slug."}}


def test_q_101_chars_is_422(client):
    response = client.get("/api/v1/search", params={"q": "c" * 101})
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "VALIDATION_ERROR", "message": "Invalid query."}}


def test_empty_query_is_empty_list(client):
    response = client.get("/api/v1/search", params={"q": "   "})
    assert response.status_code == 200
    assert response.json() == {"data": {"query": "", "items": []}}


def test_login_does_not_enumerate_users(client):
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "wrong-password-12"},
    )
    missing = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong-password-12"},
    )
    expected = {"error": {"code": "UNAUTHORIZED", "message": "Invalid credentials."}}
    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert wrong.json() == missing.json() == expected
    assert wrong.content == missing.content


def test_disabled_account_login_401_me_403(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    access = login.json()["data"]["accessToken"]
    identity = client.app.state.identity
    admin_id = next(iter(identity.admins))
    identity.set_active(admin_id, False)
    again = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert again.status_code == 401
    assert again.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid credentials."}}
    me = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 403
    assert me.json() == {"error": {"code": "FORBIDDEN", "message": "Account disabled."}}


def test_login_rate_limit_sixth_is_429(client):
    body = {"email": ADMIN_EMAIL, "password": "wrong-password-12"}
    statuses = [client.post("/api/v1/auth/login", json=body).status_code for _ in range(6)]
    assert statuses[:5] == [401] * 5
    sixth = client.post("/api/v1/auth/login", json=body)
    assert sixth.status_code == 429
    assert sixth.json() == {"error": {"code": "RATE_LIMITED", "message": "Too many requests."}}
    assert sixth.headers.get("Retry-After")
    assert int(sixth.headers["Retry-After"]) >= 1


def test_search_rate_limit_eleventh_is_429(client):
    statuses = [client.get("/api/v1/search", params={"q": "Claude"}).status_code for _ in range(10)]
    assert statuses == [200] * 10
    eleventh = client.get("/api/v1/search", params={"q": "Claude"})
    assert eleventh.status_code == 429
    assert eleventh.json()["error"]["code"] == "RATE_LIMITED"
    assert eleventh.headers.get("Retry-After")


def test_admin_me_requires_token(client):
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid access token."}}


def test_expired_access_token_is_401(client):
    now = datetime.now(timezone.utc) - timedelta(minutes=10)
    token = jwt.encode(
        {
            "sub": "1",
            "email": ADMIN_EMAIL,
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=1)).timestamp()),
            "jti": "expired",
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid access token."


def test_alg_none_is_401(client):
    token = (
        _b64url({"alg": "none", "typ": "JWT"})
        + "."
        + _b64url(
            {
                "sub": "1",
                "email": ADMIN_EMAIL,
                "typ": "access",
                "iat": 1,
                "exp": 9999999999,
            }
        )
        + "."
    )
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid access token."


def test_hs256_token_rejected_by_rs256_app(tmp_path: Path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path = tmp_path / "jwt_private.pem"
    public_path = tmp_path / "jwt_public.pem"
    private_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    hs_token = jwt.encode(
        {
            "sub": "1",
            "email": ADMIN_EMAIL,
            "typ": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
            "jti": "hs",
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    with make_client(
        jwt_secret=None,
        jwt_private_key_path=str(private_path),
        jwt_public_key_path=str(public_path),
    ) as rs_client:
        response = rs_client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {hs_token}"})
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Invalid access token."


def test_refresh_rotation_old_token_is_401_not_409(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    payload = login.json()["data"]
    assert payload["expiresIn"] == 900
    assert payload["tokenType"] == "Bearer"
    old_refresh = payload["refreshToken"]
    rotated = client.post("/api/v1/auth/refresh", json={"refreshToken": old_refresh})
    assert rotated.status_code == 200
    replay = client.post("/api/v1/auth/refresh", json={"refreshToken": old_refresh})
    assert replay.status_code == 401
    assert replay.status_code != 409
    assert replay.json() == {"error": {"code": "UNAUTHORIZED", "message": "Invalid refresh token."}}


def test_public_get_ignores_bad_bearer(client):
    response = client.get("/api/v1/meta", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 200
    assert response.json()["data"]["currentDate"] == "2026-09-14"


def test_security_headers(client):
    response = client.get("/api/v1/meta")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers.get("X-Request-ID")


def test_cors_allowlist(client):
    allowed = client.options(
        "/api/v1/meta",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.status_code in {200, 204}
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    denied = client.options(
        "/api/v1/meta",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert denied.headers.get("access-control-allow-origin") != "http://evil.example"


def test_public_json_has_no_secrets_or_internal_ids(client):
    bodies = [
        client.get("/api/v1/briefings/today").json(),
        client.get("/api/v1/sources").json(),
        client.get("/api/v1/topics").json(),
        client.get("/api/v1/stories/claude-memory").json(),
    ]
    login = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    bodies.append(login.json())
    me = client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {login.json()['data']['accessToken']}"},
    )
    bodies.append(me.json())
    dumped = json.dumps(bodies)
    assert "password_hash" not in dumped
    assert "token_hash" not in dumped
    for key, value in _walk(bodies[1]["data"]["items"]):
        if key == "id":
            assert isinstance(value, str)
            assert not str(value).isdigit()


def test_500_has_no_traceback_or_sql(client):
    async def boom(*_args, **_kwargs):
        raise RuntimeError("SELECT * FROM stories WHERE 1=1")

    client.app.state.public_reads.today = boom
    response = client.get("/api/v1/briefings/today")
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "Unexpected error."}}
    text = response.text.lower()
    assert "traceback" not in text
    assert "select" not in text
    assert "runtimeerror" not in text
    assert "stories" not in text


def test_login_success_and_me(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    data = login.json()["data"]
    me = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {data['accessToken']}"})
    assert me.status_code == 200
    assert me.json() == {"data": {"email": ADMIN_EMAIL}}
    assert "id" not in me.json()["data"]