from contextlib import asynccontextmanager
import logging
from typing import Any
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from api.v1.router import api_v1_router
from schemas.common import HealthResponse
from storage.database import check_db_connection, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("job_agent_server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database schema and connections on application startup."""
    logger.info("Initializing Job Agent backend and verifying PostgreSQL connection...")
    success = init_db()
    if success:
        logger.info("Database initialized successfully.")
    else:
        logger.error("Failed to connect to PostgreSQL during startup.")
    yield
    logger.info("Shutting down Job Agent server.")


app = FastAPI(
    title="Job Agent API",
    version="1.0.0",
    description="Production-ready REST API for Job Discovery Engine, multi-source deduplication, and application tracking.",
    lifespan=lifespan,
)

# CORS middleware for local frontend development (Next.js / Vite / Vue / React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_v1_router, prefix="/api")


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    tags=["Health"],
)
def health_check() -> HealthResponse:
    """Verifies service health and connectivity."""
    db_ok = check_db_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "disconnected",
        version="1.0.0",
    )


@app.get(
    "/",
    summary="Root Service Information",
    tags=["Root"],
)
def root_info() -> dict[str, Any]:
    """Returns basic service metadata and links to OpenAPI documentation."""
    return {
        "name": "Job Agent API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "endpoints": {
            "jobs": "/api/v1/jobs",
            "companies": "/api/v1/companies",
            "applications": "/api/v1/applications",
            "dashboard": "/api/v1/dashboard/summary",
            "discovery": "/api/v1/discovery/status",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
