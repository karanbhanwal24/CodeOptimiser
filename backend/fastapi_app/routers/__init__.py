from .analysis import router as analysis_router
from .health import router as health_router
from .optimizations import router as optimizations_router

__all__ = ["analysis_router", "health_router", "optimizations_router"]
