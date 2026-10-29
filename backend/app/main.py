"""Krishi Mitra Production Backend Application.

Main entry point configuring the FastAPI application, CORS, routers, and health checks.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
def root_status() -> dict[str, str]:
    """Root status check."""
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

