"""
Health check endpoints for C1 Travel Agent System.
"""
from fastapi import APIRouter
import structlog

from src.api.schemas import HealthResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and version information.
    """
    logger.info("Health check requested")

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "api": "running",
            "agents": "available"
        }
    )


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/Docker.

    Checks if the service is ready to accept traffic.
    """
    # TODO: Add database connection check
    # TODO: Add MCP server connection check

    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """
    Liveness check for Kubernetes/Docker.

    Simple check that the service is alive.
    """
    return {"alive": True}
