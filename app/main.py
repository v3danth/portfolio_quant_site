"""Creates the Portfolio Management REST API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import get_health_router
from app.api.routes.portfolios import get_portfolio_router
from app.api.routes.stocks import get_stock_router
from app.database.connection import initialize_database


def create_app() -> FastAPI:
    """Creates the configured FastAPI application."""
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database()
        yield

    app = FastAPI(title="Portfolio Management API", version="1.0.0", lifespan=lifespan)
    app.include_router(get_health_router())
    app.include_router(get_stock_router())
    app.include_router(get_portfolio_router())

    return app


app = create_app()
