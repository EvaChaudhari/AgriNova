"""Krishi Mitra / AgriNova Production Backend Application.

Main entry point configuring FastAPI, structured JSON logging,
request correlation tracking, centralized RFC 7807 error handling, and health probes.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    auth,
    bootstrap,
    chat_receptor,
    consent,
    crop_knowledge,
    evaluation,
    farms,
    governed_data,
    notifications,
    observations,
    planner,
    plots,
    roadmap,
    soil,
    sync,
)
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.exceptions import (
    AgriNovaException,
    build_problem_details_response,
)
from app.core.logging import (
    get_correlation_id,
    set_correlation_id,
    setup_logging,
)

# Initialize structured JSON logging
setup_logging(log_level="INFO")
logger = logging.getLogger("agrinova.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to initialize resources."""
    logger.info("Initializing AgriNova Backend Engine...")
    # Ensure tables exist in local database
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")

    # Seed baseline agronomic crop knowledge and ICAR guidance idempotently
    try:
        from app.core.database import SessionLocal
        from app.services.crop_seed_service import seed_crops_if_empty
        from app.services.retrieval_service import AgronomicRetrievalService

        with SessionLocal() as db:
            crop_count = seed_crops_if_empty(db)
            guide_count = AgronomicRetrievalService.seed_guides_if_empty(db)
            logger.info("Agronomic knowledge baseline loaded: %d crops, %d ICAR guides active.", crop_count, guide_count)
    except Exception as exc:
        logger.warning("Could not auto-seed agronomic knowledge on startup: %s", str(exc))

    yield
    logger.info("Shutting down AgriNova Backend Engine.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Deterministic hydrological and hazard intelligence platform for smallholder agriculture in India.",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) for Mobile & Web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Middlewares: Correlation ID Tracking & Request Logging
# ============================================================================

@app.middleware("http")
async def correlation_and_logging_middleware(request: Request, call_next: Any) -> Any:
    """Track request correlation ID, profile response duration, and log structured metrics."""
    incoming_cid = request.headers.get("X-Correlation-ID")
    cid = incoming_cid.strip() if incoming_cid and incoming_cid.strip() else uuid.uuid4().hex
    set_correlation_id(cid)

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        logger.error(
            "Unhandled exception occurred while processing request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
                "correlation_id": cid,
            },
            exc_info=True,
        )
        raise exc

    duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
    response.headers["X-Correlation-ID"] = cid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Emit structured request log entry without leaking private body data
    log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(
        log_level,
        f"{request.method} {request.url.path} HTTP/{request.scope.get('http_version', '1.1')} {response.status_code} [{duration_ms}ms]",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "correlation_id": cid,
        },
    )

    return response


# ============================================================================
# Centralized RFC 7807 Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI / Pydantic validation errors with RFC 7807 problem details."""
    cid = get_correlation_id() or uuid.uuid4().hex
    invalid_params: list[dict[str, Any]] = []
    for err in exc.errors():
        loc_str = " -> ".join(str(loc) for loc in err.get("loc", []))
        invalid_params.append({
            "name": loc_str,
            "reason": err.get("msg", "Validation constraint failed"),
            "type": err.get("type", "validation_error"),
        })

    logger.warning(
        "Request validation error on %s %s: %s",
        request.method,
        request.url.path,
        invalid_params,
        extra={"correlation_id": cid},
    )

    return build_problem_details_response(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        title="Request Validation Failed",
        detail="The request payload or parameters failed validation constraints.",
        error_code="VALIDATION_ERROR",
        instance=request.url.path,
        correlation_id=cid,
        invalid_params=invalid_params,
    )


@app.exception_handler(AgriNovaException)
async def agrinova_exception_handler(request: Request, exc: AgriNovaException) -> JSONResponse:
    """Handle domain-specific agricultural platform exceptions."""
    cid = get_correlation_id() or uuid.uuid4().hex
    logger.warning(
        "Agricultural domain exception on %s %s: [%s] %s",
        request.method,
        request.url.path,
        exc.error_code,
        exc.detail,
        extra={"correlation_id": cid},
    )

    headers = {}
    if hasattr(exc, "retry_after"):
        headers["Retry-After"] = str(exc.retry_after)

    return build_problem_details_response(
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        error_code=exc.error_code,
        instance=request.url.path,
        correlation_id=cid,
        invalid_params=exc.invalid_params,
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions with RFC 7807 formatting."""
    cid = get_correlation_id() or uuid.uuid4().hex
    return build_problem_details_response(
        status_code=exc.status_code,
        title="HTTP Error",
        detail=str(exc.detail),
        error_code=f"HTTP_{exc.status_code}",
        instance=request.url.path,
        correlation_id=cid,
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors safely without exposing SQL queries or credentials."""
    cid = get_correlation_id() or uuid.uuid4().hex
    logger.error(
        "Database exception during %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        extra={"correlation_id": cid},
        exc_info=True,
    )

    return build_problem_details_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Database Operation Error",
        detail="A database error occurred while processing your request. Please quote the correlation ID when contacting support.",
        error_code="DATABASE_ERROR",
        instance=request.url.path,
        correlation_id=cid,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all uncaught exceptions safely without exposing internal stack traces."""
    cid = get_correlation_id() or uuid.uuid4().hex
    logger.error(
        "Uncaught internal server exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        extra={"correlation_id": cid},
        exc_info=True,
    )

    return build_problem_details_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Internal Server Error",
        detail="An unexpected internal server error occurred. Please quote the correlation ID when contacting support.",
        error_code="INTERNAL_SERVER_ERROR",
        instance=request.url.path,
        correlation_id=cid,
    )


# ============================================================================
# API Routers
# ============================================================================

app.include_router(bootstrap.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(consent.router, prefix=settings.API_V1_STR)
app.include_router(farms.router, prefix=settings.API_V1_STR)
app.include_router(plots.router, prefix=settings.API_V1_STR)
app.include_router(observations.router, prefix=settings.API_V1_STR)
app.include_router(crop_knowledge.router, prefix=settings.API_V1_STR)
app.include_router(soil.router, prefix=settings.API_V1_STR)
app.include_router(planner.router, prefix=settings.API_V1_STR)
app.include_router(roadmap.router, prefix=settings.API_V1_STR)
app.include_router(sync.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(evaluation.router, prefix=settings.API_V1_STR)
app.include_router(governed_data.router, prefix=settings.API_V1_STR)
app.include_router(chat_receptor.router, prefix=settings.API_V1_STR)


# ============================================================================
# Health, Liveness & Readiness Probes
# ============================================================================

@app.get("/health", tags=["Health"])
def liveness_check() -> dict[str, Any]:
    """Process liveness probe.

    Confirms that the FastAPI process is alive and responsive.
    MUST NOT depend on database availability.
    """
    return {
        "status": "pass",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Health"])
def readiness_check(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Subsystem readiness probe.

    Executes a real database connectivity ping (SELECT 1) and verifies that
    the storage backend is accessible and writable.
    Returns HTTP 200 when ready, or HTTP 503 if any required subsystem is degraded.
    Never exposes internal credentials, connection strings, or paths.
    """
    cid = get_correlation_id() or uuid.uuid4().hex
    checks: dict[str, str] = {"database": "pass", "storage": "pass"}
    is_ready = True

    # 1. Real database connectivity check
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Readiness check: Database connection failed: %s", str(exc), extra={"correlation_id": cid})
        checks["database"] = "fail"
        is_ready = False

    # 2. Configured storage backend check
    try:
        storage_dir = settings.STORAGE_DIR
        storage_dir.mkdir(parents=True, exist_ok=True)
        canary = storage_dir / ".ready_canary"
        canary.touch()
        canary.unlink(missing_ok=True)
    except Exception as exc:
        logger.error("Readiness check: Storage check failed: %s", str(exc), extra={"correlation_id": cid})
        checks["storage"] = "fail"
        is_ready = False

    content: dict[str, Any] = {
        "status": "pass" if is_ready else "fail",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    if not is_ready:
        content["detail"] = "One or more required subsystem readiness checks failed."
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=content,
            headers={"X-Correlation-ID": cid},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=content,
        headers={"X-Correlation-ID": cid},
    )


@app.get("/", tags=["Health"])
def root_status() -> dict[str, str]:
    """Root metadata status check."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/healthz", tags=["Health"])
def healthz() -> dict[str, str]:
    """Legacy Kubernetes liveness and readiness probe for backward compatibility."""
    return {"status": "ok"}
