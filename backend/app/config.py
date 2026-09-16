from __future__ import annotations

from pathlib import Path

from pydantic import model_validator

from app.application.schedule import parse_schedule
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str | None = None
    alembic_database_url: str | None = None
    jwt_secret: str | None = None
    jwt_private_key_path: str | None = None
    jwt_public_key_path: str | None = None
    admin_email: str = "admin@example.com"
    admin_password: str = ""
    allowed_origins: str = "http://localhost:3000"
    trust_proxy: bool = False
    debug: bool = False
    repository: str = "postgres"
    timezone: str = "Asia/Shanghai"
    pipeline_scheduler_enabled: bool = False
    pipeline_schedule: str = "06:30,12:30,18:30"
    pipeline_auto_cluster: bool = True

    @property
    def origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.allowed_origins.split(",") if item.strip()]
        if not origins:
            return ["http://localhost:3000"]
        if "*" in origins:
            raise ValueError("ALLOWED_ORIGINS must not contain *")
        return origins

    @property
    def jwt_mode(self) -> str:
        rsa = bool(self.jwt_private_key_path) and bool(self.jwt_public_key_path)
        hs = bool(self.jwt_secret)
        if rsa and hs:
            raise ValueError("JWT RSA paths and JWT_SECRET are mutually exclusive")
        if rsa:
            return "RS256"
        if hs:
            return "HS256"
        raise ValueError("Configure JWT_SECRET or JWT_PRIVATE_KEY_PATH + JWT_PUBLIC_KEY_PATH")

    @model_validator(mode="after")
    def validate_jwt(self) -> "Settings":
        mode = self.jwt_mode
        if mode == "HS256":
            secret = self.jwt_secret or ""
            if len(secret.encode("utf-8")) < 32:
                raise ValueError("JWT_SECRET must be at least 32 bytes")
        else:
            private = Path(self.jwt_private_key_path or "")
            public = Path(self.jwt_public_key_path or "")
            if not private.is_file() or not public.is_file():
                raise ValueError("JWT RSA key files are missing")
        if self.repository not in {"postgres", "memory"}:
            raise ValueError("REPOSITORY must be postgres or memory")
        if self.repository == "postgres" and not self.database_url:
            raise ValueError("DATABASE_URL is required when REPOSITORY=postgres")
        parse_schedule(self.pipeline_schedule)
        return self

    def async_database_url(self) -> str:
        url = self.database_url or ""
        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url[len("postgresql://"):]
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url[len("postgres://"):]
        return url

    def sync_database_url(self) -> str:
        url = self.alembic_database_url or self.database_url or ""
        for prefix in ("postgresql+asyncpg://", "postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url
