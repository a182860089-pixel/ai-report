from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.domain.entities import AdminUser
from app.domain.exceptions import AppError
from app.domain.interfaces import Clock, IdentityRepository, PasswordHasher, TokenService

ACCESS_TTL_SECONDS = 900
REFRESH_TTL_DAYS = 7


class AuthUseCases:
    def __init__(
        self,
        identity: IdentityRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Clock,
    ) -> None:
        self.identity = identity
        self.hasher = hasher
        self.tokens = tokens
        self.clock = clock

    async def login(
        self,
        email: str,
        password: str,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        normalized = email.strip().lower()
        admin = await self.identity.get_admin_by_email(normalized)
        if admin is None:
            self.hasher.verify(password, self.hasher.dummy_hash())
            await self.identity.insert_audit(
                None, "login_failed", "auth", ip, user_agent, {"email": normalized}
            )
            raise AppError(401, "UNAUTHORIZED", "Invalid credentials.")
        matched = self.hasher.verify(password, admin.password_hash)
        if not admin.is_active or not matched:
            await self.identity.insert_audit(
                admin.id, "login_failed", "auth", ip, user_agent, {"email": normalized}
            )
            raise AppError(401, "UNAUTHORIZED", "Invalid credentials.")
        now = self.clock.now()
        await self.identity.update_last_login(admin.id, now)
        refresh = self.tokens.new_refresh()
        await self.identity.insert_refresh(
            admin.id,
            self.tokens.hash_refresh(refresh),
            now + timedelta(days=REFRESH_TTL_DAYS),
            ip,
            _clip_ua(user_agent),
        )
        await self.identity.insert_audit(
            admin.id, "login", "auth", ip, user_agent, {"email": admin.email}
        )
        return _token_payload(self.tokens.issue_access(admin.id, admin.email), refresh, admin.email)

    async def refresh(self, refresh_token: str, ip: str | None, user_agent: str | None) -> dict[str, Any]:
        now = self.clock.now()
        token_hash = self.tokens.hash_refresh(refresh_token)
        record = await self.identity.get_refresh_by_hash(token_hash)
        if record is None:
            raise AppError(401, "UNAUTHORIZED", "Invalid refresh token.")
        if record.revoked_at is not None or record.expires_at <= now:
            await self.identity.revoke_all_refresh(record.admin_user_id, now)
            await self.identity.insert_audit(
                record.admin_user_id, "refresh_replay", "auth", ip, user_agent, {}
            )
            raise AppError(401, "UNAUTHORIZED", "Invalid refresh token.")
        admin = await self.identity.get_admin_by_id(record.admin_user_id)
        if admin is None or not admin.is_active:
            raise AppError(401, "UNAUTHORIZED", "Invalid refresh token.")
        await self.identity.revoke_refresh(token_hash, now)
        new_refresh = self.tokens.new_refresh()
        await self.identity.insert_refresh(
            admin.id,
            self.tokens.hash_refresh(new_refresh),
            now + timedelta(days=REFRESH_TTL_DAYS),
            ip,
            _clip_ua(user_agent),
        )
        await self.identity.insert_audit(admin.id, "refresh", "auth", ip, user_agent, {"email": admin.email})
        return _token_payload(self.tokens.issue_access(admin.id, admin.email), new_refresh, admin.email)

    async def logout(
        self,
        access_token: str | None,
        refresh_token: str | None,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, bool]:
        if not access_token and not refresh_token:
            raise AppError(422, "VALIDATION_ERROR", "Missing access or refresh token.")
        now = self.clock.now()
        admin_id: int | None = None
        access_ok = False
        if access_token:
            try:
                admin_id, _email = self.tokens.parse_access(access_token)
                access_ok = True
            except AppError:
                access_ok = False
        refresh_ok = False
        if refresh_token:
            record = await self.identity.get_refresh_by_hash(self.tokens.hash_refresh(refresh_token))
            if record is not None and record.revoked_at is None and record.expires_at > now:
                refresh_ok = True
                admin_id = record.admin_user_id
                await self.identity.revoke_refresh(record.token_hash, now)
        if not access_ok and not refresh_ok:
            raise AppError(401, "UNAUTHORIZED", "Invalid access token.")
        if access_ok and not refresh_token and admin_id is not None:
            await self.identity.revoke_all_refresh(admin_id, now)
        await self.identity.insert_audit(admin_id, "logout", "auth", ip, user_agent, {})
        return {"ok": True}

    async def require_admin(self, access_token: str) -> AdminUser:
        admin_id, _email = self.tokens.parse_access(access_token)
        admin = await self.identity.get_admin_by_id(admin_id)
        if admin is None:
            raise AppError(401, "UNAUTHORIZED", "Invalid access token.")
        if not admin.is_active:
            raise AppError(403, "FORBIDDEN", "Account disabled.")
        return admin

    async def me(self, access_token: str) -> dict[str, str]:
        admin = await self.require_admin(access_token)
        return {"email": admin.email}


def _token_payload(access: str, refresh: str, email: str) -> dict[str, Any]:
    return {
        "accessToken": access,
        "refreshToken": refresh,
        "tokenType": "Bearer",
        "expiresIn": ACCESS_TTL_SECONDS,
        "admin": {"email": email},
    }


def _clip_ua(user_agent: str | None) -> str | None:
    if user_agent is None:
        return None
    return user_agent[:300]
