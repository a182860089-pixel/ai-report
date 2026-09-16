from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Any

import jwt
from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.application.auth import ACCESS_TTL_SECONDS
from app.config import Settings
from app.domain.exceptions import AppError
from app.domain.interfaces import Clock


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = Argon2Hasher()
        self._dummy = self._hasher.hash("__ai-report-dummy-password__")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return bool(self._hasher.verify(password_hash, password))
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def dummy_hash(self) -> str:
        return self._dummy


class JwtTokenService:
    def __init__(self, settings: Settings, clock: Clock) -> None:
        self.settings = settings
        self.clock = clock
        self.alg = settings.jwt_mode
        if self.alg == "HS256":
            self._private: Any = settings.jwt_secret
            self._public: Any = settings.jwt_secret
        else:
            self._private = Path(settings.jwt_private_key_path or "").read_bytes()
            self._public = Path(settings.jwt_public_key_path or "").read_bytes()

    def issue_access(self, admin_id: int, email: str) -> str:
        now = self.clock.now()
        payload = {
            "sub": str(admin_id),
            "email": email,
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ACCESS_TTL_SECONDS)).timestamp()),
            "jti": secrets.token_urlsafe(16),
        }
        return jwt.encode(payload, self._private, algorithm=self.alg)

    def parse_access(self, token: str) -> tuple[int, str]:
        try:
            payload = jwt.decode(
                token,
                self._public,
                algorithms=[self.alg],
                leeway=30,
                options={"require": ["exp", "iat", "sub", "typ"]},
            )
        except jwt.PyJWTError as exc:
            raise AppError(401, "UNAUTHORIZED", "Invalid access token.") from exc
        if payload.get("typ") != "access":
            raise AppError(401, "UNAUTHORIZED", "Invalid access token.")
        try:
            admin_id = int(payload["sub"])
        except (TypeError, ValueError) as exc:
            raise AppError(401, "UNAUTHORIZED", "Invalid access token.") from exc
        email = str(payload.get("email") or "")
        return admin_id, email

    def new_refresh(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_refresh(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
