"""ASGI entry point with startup/shutdown resource management."""

import sys
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.concurrency import run_in_threadpool

from app import __version__
from app.api.v1.router import api_v1_router
from app.config import Settings, get_settings
from app.models.schemas import HealthResponse
from app.runtime import Runtime, build_runtime


def create_app(settings: Settings | None = None, runtime: Runtime | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            logger.remove(0)
        except ValueError:
            pass
        sink = logger.add(
            sys.stderr, serialize=True, enqueue=True, level="INFO", backtrace=False, diagnose=False
        )
        try:
            application.state.runtime = runtime or await run_in_threadpool(build_runtime, settings)
            yield
        finally:
            if hasattr(application.state, "runtime"):
                await run_in_threadpool(application.state.runtime.close)
            await logger.complete()
            logger.remove(sink)

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        description=(
            "Privacy-aware telecom support workflow. Synthetic DemoTel data; no account access."
        ),
    )
    application.state.settings = settings
    application.include_router(api_v1_router)
    application.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

    @application.middleware("http")
    async def correlation_and_errors(request: Request, call_next):
        request_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception as exc:
            # Exception strings may contain prompts, credentials or connection URLs.
            logger.bind(request_id=request_id, error_type=type(exc).__name__).error(
                "request_failed"
            )
            response = JSONResponse(
                status_code=503,
                content={
                    "detail": "Destek servisi geçici olarak kullanılamıyor.",
                    "request_id": request_id,
                },
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        # Pydantic normally echoes `input` in 422 responses; omit potentially raw PII.
        return JSONResponse(
            status_code=422,
            content={
                "detail": (
                    "İstek biçimi geçersiz. Mesaj 1–2000 karakter olmalı "
                    "ve oturum kimliği UUID olmalıdır."
                )
            },
        )

    @application.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        return HealthResponse(service=settings.app_name, version=__version__)

    @application.get("/ready", tags=["operations"])
    def ready(request: Request):
        checks = request.app.state.runtime.readiness()
        healthy = all(checks.values())
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={"status": "ready" if healthy else "unavailable", "checks": checks},
        )

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(settings.static_dir / "index.html")

    return application


app = create_app()
