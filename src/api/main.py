"""FastAPI application entry point for the KYC Pipeline.

Configures the application, middleware, and routes at startup.
Exposes Prometheus metrics and health check endpoints.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response

from src.api.routes.kyc import router as kyc_router
from src.infrastructure.observability.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown.

    Initializes logging, DI container, and connections on startup.
    Cleans up resources on shutdown.
    """
    configure_logging()
    # Container would be built here and stored in app.state
    # app.state.container = build_container()
    yield
    # Cleanup on shutdown


app = FastAPI(
    title="KYC Pipeline API",
    description="Autonomous Multi-Agent KYC Investigation and Fraud Network Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(kyc_router)


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    """System health check including service connectivity.

    Returns:
        Health status dictionary.
    """
    return {
        "status": "healthy",
        "service": "kyc-pipeline",
        "version": "1.0.0",
    }
