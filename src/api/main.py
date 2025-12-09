"""
FastAPI Main Application for C1 Travel Agent System.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from src.api.routes import chat_router, health_router, auth_router, user_router

# Configure logging based on environment
log_format = os.getenv("LOG_FORMAT", "console")  # "console" or "json"
log_colors = os.getenv("LOG_COLORS", "true").lower() == "true"

if log_format == "json":
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
else:
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(colors=log_colors)
    ]

structlog.configure(
    processors=processors,
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 C1 Travel Agent API starting up...")
    yield
    # Shutdown
    logger.info("👋 C1 Travel Agent API shutting down...")


# Create FastAPI application
app = FastAPI(
    title="C1 Travel Agent API",
    description="Multi-agent travel assistant API powered by LangGraph",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "C1 Travel Agent API",
        "version": "1.0.0",
        "description": "Multi-agent travel assistant",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
