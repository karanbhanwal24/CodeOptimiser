from .analysis import router as analysis_router
from .ai import router as ai_router
from .health import router as health_router
from .optimizations import router as optimizations_router

__all__ = ["ai_router", "analysis_router", "health_router", "optimizations_router"]
