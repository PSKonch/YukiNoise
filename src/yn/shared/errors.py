import logging
from typing import Any, Sequence
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400
    code = "app_error"
    detail = "Application error"
    headers: dict[str, str] | None = None

    def __init__(
        self,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.detail = detail or self.detail
        self.headers = headers or self.headers
        super().__init__(self.detail)


def register_exception_handlers(app: FastAPI) -> None:
    def build_error_payload(
        *,
        code: str,
        detail: str,
        errors: Sequence[Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": code, "detail": detail}
        if errors is not None:
            # ensure it's a JSON-serializable list
            payload["errors"] = list(errors)
        if request_id is not None:
            payload["request_id"] = request_id
        return payload

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(code=exc.code, detail=exc.detail),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=build_error_payload(
                code="validation_error",
                detail="Request validation failed",
                errors=exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(code="http_error", detail=detail),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        logger.exception("Unhandled server error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content=build_error_payload(
                code="internal_server_error",
                detail="Internal server error",
                request_id=request_id,
            ),
        )
