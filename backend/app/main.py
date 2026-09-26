import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.db.init_db import check_database_ready
from app.db.session import engine
from app.routers import analysis, appointments, auth, doctors, patients, reports
from app.services import analysis_service, cv_engine
from app.services.jobs import shutdown_job_runner
from app.services.storage import get_storage

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_database_ready(engine)
    get_storage()
    resubmitted = analysis_service.resubmit_incomplete_analyses()
    if resubmitted:
        logger.info("resubmitted interrupted analyses", extra={"count": resubmitted})
    yield
    shutdown_job_runner()
    cv_engine.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, json_output=settings.ENVIRONMENT == "production")
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="2.0.0",
        lifespan=lifespan,
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=None,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # bearer tokens, no cookies
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition"],
    )

    @app.middleware("http")
    async def security_headers_and_logging(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith(settings.API_PREFIX):
            response.headers.setdefault("Cache-Control", "no-store")
        # Path only: query strings may contain search terms or coordinates.
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500, content={"detail": "An unexpected error occurred.", "code": "internal_error"}
        )

    @app.get(f"{settings.API_PREFIX}/health", tags=["health"])
    def health() -> dict:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "pose_model_present": settings.POSE_MODEL_PATH.is_file()}

    for router in (auth.router, patients.router, analysis.router, reports.router, doctors.router, appointments.router):
        app.include_router(router, prefix=settings.API_PREFIX)
    return app


app = create_app()
