"""Registers application health routes."""

from fastapi import APIRouter

from app.api.dependencies import get_backend


def get_health_router() -> APIRouter:
    """Builds routes for application health checks."""
    router = APIRouter()

    @router.get("/health")
    def health_check() -> dict:
        """Returns the API health status."""
        return {"status": "ok", "database": get_backend()}

    return router
