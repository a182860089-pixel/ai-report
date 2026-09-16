from __future__ import annotations

from fastapi import Request

from app.application.admin import AdminUseCases
from app.application.auth import AuthUseCases
from app.adapters.scheduler import PipelineScheduler
from app.application.pipeline import PipelineUseCases
from app.application.use_cases import PublicReads
from app.config import Settings


def settings(request: Request) -> Settings:
    return request.app.state.settings


def public_reads(request: Request) -> PublicReads:
    return request.app.state.public_reads


def auth_uc(request: Request) -> AuthUseCases:
    return request.app.state.auth

def admin_uc(request: Request) -> AdminUseCases:
    return request.app.state.admin


def pipeline_uc(request: Request) -> PipelineUseCases:
    return request.app.state.pipeline


def scheduler(request: Request) -> PipelineScheduler:
    return request.app.state.scheduler
