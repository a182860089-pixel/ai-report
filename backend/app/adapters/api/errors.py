from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import AppError

log = logging.getLogger("ai_report")


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def error_response(status: int, code: str, message: str, retry_after: int | None = None) -> JSONResponse:
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(int(retry_after))
    return JSONResponse(error_body(code, message), status_code=status, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        if exc.status == 401 and exc.message == "Invalid credentials.":
            log.warning("login_failed")
        return error_response(exc.status, exc.code, exc.message, exc.retry_after)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "VALIDATION_ERROR", "Invalid request.")

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error_response(404, "NOT_FOUND", "Not found.")
        if exc.status_code == 405:
            return error_response(405, "BAD_REQUEST", "Method not allowed.")
        return error_response(exc.status_code, "BAD_REQUEST", "Bad request.")

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error")
        return error_response(500, "INTERNAL_ERROR", "Unexpected error.")
