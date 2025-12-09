"""API Routes Package."""
from .chat import router as chat_router
from .health import router as health_router
from .auth import router as auth_router
from .user import router as user_router

__all__ = ["chat_router", "health_router", "auth_router", "user_router"]
