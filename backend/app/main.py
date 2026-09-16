from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.api.errors import install_error_handlers
from app.adapters.api.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.adapters.api.rate_limit import InProcessRateLimiter
from app.adapters.api.routers import admin as admin_router
from app.adapters.api.routers import auth as auth_router
from app.adapters.api.routers import catalog as catalog_router
from app.adapters.api.routers import editorial as editorial_router
from app.adapters.api.routers import health as health_router
from app.adapters.api.routers import pipeline as pipeline_router
from app.adapters.api.security import Argon2PasswordHasher, JwtTokenService
from app.application.admin import AdminUseCases
from app.application.auth import AuthUseCases
from app.application.pipeline import PipelineUseCases
from app.application.timefmt import SystemClock
from app.application.use_cases import PublicReads
from app.config import Settings


def build_container(settings: Settings, http_fetcher=None) -> SimpleNamespace:
    clock = SystemClock()
    hasher = Argon2PasswordHasher()
    tokens = JwtTokenService(settings, clock)
    limiter = InProcessRateLimiter()
    engine = None
    world = None
    identity: object
    from app.adapters.http.parser import XmlFeedParser
    from app.adapters.pipeline.template_writer import TemplateStoryWriter

    parser = XmlFeedParser()
    writer = TemplateStoryWriter()
    if settings.repository == "memory":
        from app.adapters.http.fetcher import DisabledHttpFetcher
        from app.adapters.memory.repositories import (
            MemoryAdminCatalogRepository,
            MemoryAdminEditorialRepository,
            MemoryCatalogRepository,
            MemoryEditorialRepository,
            MemoryHealthRepository,
            MemoryIdentityRepository,
            MemoryPipelineRepository,
            MemoryWorld,
        )

        world = MemoryWorld()
        editorial = MemoryEditorialRepository(world)
        catalog = MemoryCatalogRepository(world)
        identity = MemoryIdentityRepository()
        admin_catalog = MemoryAdminCatalogRepository(world)
        admin_editorial = MemoryAdminEditorialRepository(world)
        pipeline_repo = MemoryPipelineRepository(world, identity)
        fetcher = http_fetcher or DisabledHttpFetcher()
        if settings.admin_password:
            identity.add_admin(
                settings.admin_email.strip().lower(),
                hasher.hash(settings.admin_password),
                True,
            )
        health = MemoryHealthRepository()
    else:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.adapters.db.admin_repositories import PgAdminCatalogRepository, PgAdminEditorialRepository
        from app.adapters.db.pipeline_repositories import PgPipelineRepository
        from app.adapters.db.repositories import (
            PgCatalogRepository,
            PgEditorialRepository,
            PgHealthRepository,
            PgIdentityRepository,
        )
        from app.adapters.http.ssrf import SsrfHttpClient

        engine = create_async_engine(settings.async_database_url(), pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        editorial = PgEditorialRepository(session_factory)
        catalog = PgCatalogRepository(session_factory)
        identity = PgIdentityRepository(session_factory)
        health = PgHealthRepository(session_factory)
        admin_catalog = PgAdminCatalogRepository(session_factory)
        admin_editorial = PgAdminEditorialRepository(session_factory)
        pipeline_repo = PgPipelineRepository(session_factory)
        fetcher = http_fetcher or SsrfHttpClient()

    public_reads = PublicReads(editorial, catalog, health)
    auth = AuthUseCases(identity, hasher, tokens, clock)
    admin = AdminUseCases(admin_catalog, admin_editorial, identity)
    pipeline = PipelineUseCases(
        admin_catalog,
        admin_editorial,
        pipeline_repo,
        fetcher,
        parser,
        writer,
        clock,
        identity,
    )
    return SimpleNamespace(
        settings=settings,
        clock=clock,
        hasher=hasher,
        tokens=tokens,
        limiter=limiter,
        engine=engine,
        world=world,
        identity=identity,
        public_reads=public_reads,
        auth=auth,
        admin=admin,
        pipeline=pipeline,
    )


def create_app(settings: Settings | None = None, *, http_fetcher=None) -> FastAPI:
    settings = settings or Settings()
    container = build_container(settings, http_fetcher=http_fetcher)
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)

    from app.adapters.scheduler import PipelineScheduler

    scheduler = PipelineScheduler(
        pipeline=container.pipeline,
        identity=container.identity,
        settings=settings,
        clock=container.clock,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await scheduler.start()
        try:
            yield
        finally:
            await scheduler.stop()
            if container.engine is not None:
                await container.engine.dispose()

    app = FastAPI(
        title="AI Report API",
        version="v1",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
        redirect_slashes=False,
    )
    app.state.settings = container.settings
    app.state.public_reads = container.public_reads
    app.state.auth = container.auth
    app.state.admin = container.admin
    app.state.pipeline = container.pipeline
    app.state.limiter = container.limiter
    app.state.identity = container.identity
    app.state.world = container.world
    app.state.hasher = container.hasher
    app.state.tokens = container.tokens
    app.state.engine = container.engine
    app.state.scheduler = scheduler

    install_error_handlers(app)
    app.include_router(health_router.router)
    app.include_router(editorial_router.router, prefix="/api/v1")
    app.include_router(catalog_router.router, prefix="/api/v1")
    app.include_router(auth_router.router, prefix="/api/v1")
    app.include_router(admin_router.router, prefix="/api/v1")
    app.include_router(pipeline_router.router, prefix="/api/v1")

    app.add_middleware(RateLimitMiddleware, settings=settings, limiter=container.limiter)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    return app