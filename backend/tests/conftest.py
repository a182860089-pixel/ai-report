from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from app.adapters.api.security import Argon2PasswordHasher
from app.config import Settings
from app.main import create_app

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "change-me-now-12"
JWT_SECRET = "a" * 32

_ARGON2 = PasswordHasher()
_ADMIN_HASH = _ARGON2.hash(ADMIN_PASSWORD)
_DUMMY_HASH = _ARGON2.hash("__ai-report-dummy-password__")

_ENV_KEYS = (
    "DATABASE_URL",
    "ALEMBIC_DATABASE_URL",
    "JWT_SECRET",
    "JWT_PRIVATE_KEY_PATH",
    "JWT_PUBLIC_KEY_PATH",
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD",
    "ALLOWED_ORIGINS",
    "TRUST_PROXY",
    "DEBUG",
    "REPOSITORY",
    "PIPELINE_SCHEDULER_ENABLED",
    "PIPELINE_SCHEDULE",
    "PIPELINE_AUTO_CLUSTER",
)


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    wanted = {item.upper() for item in _ENV_KEYS}
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key in list(os.environ):
        if key.upper() in wanted:
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def cache_argon2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _init(self: Argon2PasswordHasher) -> None:
        self._hasher = _ARGON2
        self._dummy = _DUMMY_HASH

    def _hash(self: Argon2PasswordHasher, password: str) -> str:
        if password == ADMIN_PASSWORD:
            return _ADMIN_HASH
        return _ARGON2.hash(password)

    monkeypatch.setattr(Argon2PasswordHasher, "__init__", _init)
    monkeypatch.setattr(Argon2PasswordHasher, "hash", _hash)


def make_settings(**overrides) -> Settings:
    payload = {
        "repository": "memory",
        "jwt_secret": JWT_SECRET,
        "admin_email": ADMIN_EMAIL,
        "admin_password": ADMIN_PASSWORD,
        "allowed_origins": "http://localhost:3000",
        "debug": False,
        "trust_proxy": False,
        "database_url": None,
        "alembic_database_url": None,
        "jwt_private_key_path": None,
        "jwt_public_key_path": None,
        "pipeline_scheduler_enabled": False,
        "pipeline_schedule": "06:30,12:30,18:30",
        "pipeline_auto_cluster": True,
    }
    payload.update(overrides)
    return Settings(_env_file=None, **payload)


def make_client(**overrides) -> TestClient:
    http_fetcher = overrides.pop("http_fetcher", None)
    app = create_app(make_settings(**overrides), http_fetcher=http_fetcher)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def app():
    return create_app(make_settings())


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client