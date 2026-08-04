"""Application factory and router registration."""
import asyncio
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import analytics, holdings, portfolios, stocks, transactions, users, watchlist
from app.services.price_refresh import refresh_all_prices
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

API_PREFIX = "/api/v1"


async def _run_periodic_refresh() -> None:
    """Background loop refreshing stock_prices every PRICE_REFRESH_INTERVAL_SECONDS."""
    while True:
        await asyncio.sleep(settings.PRICE_REFRESH_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(refresh_all_prices)
        except Exception:
            logging.exception("Periodic price refresh failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop the periodic stock_prices refresh task with the app."""
    task = asyncio.create_task(_run_periodic_refresh())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Quantitative Portfolio Management System (QPMS) API",
        version="1.0.0",
        description="REST API for the Quantitative Portfolio Management System.",
        lifespan=lifespan,
    )

    # CORS — allow the Streamlit frontend to call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers here. Add new modules (analytics, factors, ...) below.
    # analytics is registered before portfolios so the static path
    # /portfolios/performers is matched before /portfolios/{portfolio_id}.
    app.include_router(users.router, prefix=API_PREFIX)
    app.include_router(stocks.router, prefix=API_PREFIX)
    app.include_router(analytics.router, prefix=API_PREFIX)
    app.include_router(portfolios.router, prefix=API_PREFIX)
    app.include_router(holdings.router, prefix=API_PREFIX)
    app.include_router(transactions.router, prefix=API_PREFIX)
    app.include_router(analytics.router, prefix=API_PREFIX)
    app.include_router(watchlist.router, prefix=API_PREFIX)

    @app.get("/health", tags=["Meta"])
    def health() -> dict:
        return {"status": "ok"}

    return app
