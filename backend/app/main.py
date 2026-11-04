"""Krishi Mitra Production Backend Application.

Main entry point configuring the FastAPI application, CORS, routers, and health checks.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1 import bootstrap, plots, chat_receptor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to initialize resources."""
    # Ensure tables exist in local database
    Base.metadata.create_all(bind=engine)
    yield


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

# API v1 Routers
app.include_router(bootstrap.router, prefix=settings.API_V1_STR)
app.include_router(plots.router, prefix=settings.API_V1_STR)
app.include_router(chat_receptor.router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root_status(request: Request) -> Any:
    """Root status check or web app redirection."""
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/app/")
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/healthz", tags=["Health"])
def healthz() -> dict[str, str]:
    """Kubernetes liveness and readiness probe."""
    return {"status": "ok"}


# Mount static frontend application
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


