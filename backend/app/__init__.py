"""Application factory and router registration."""
import mysql.connector
from app.routers import analytics, holdings, portfolios, stocks, transactions, users, watchlist
from app.services.price_refresh import lifespan_refresh
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

API_PREFIX = "/api/v1"


def _db_error_handler(_request: Request, exc: mysql.connector.Error) -> JSONResponse:
    """Return a clear 503 instead of a bare 500 when MySQL is unreachable."""
    return JSONResponse(
        status_code=503,
        content={"detail": f"Database connection failed: {exc.msg}"},
    )


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Quantitative Portfolio Management System (QPMS) API",
        version="1.0.0",
        description="REST API for the Quantitative Portfolio Management System.",
        lifespan=lifespan_refresh,
    )

    # CORS — allow the Streamlit frontend to call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Surface MySQL connection problems as a clear 503 response.
    app.add_exception_handler(mysql.connector.Error, _db_error_handler)

    # Register routers here. Add new modules (analytics, factors, ...) below.
    # analytics is registered before portfolios so the static path
    # /portfolios/performers is matched before /portfolios/{portfolio_id}.
    app.include_router(users.router, prefix=API_PREFIX)
    app.include_router(stocks.router, prefix=API_PREFIX)
    app.include_router(analytics.router, prefix=API_PREFIX)
    app.include_router(portfolios.router, prefix=API_PREFIX)
    app.include_router(holdings.router, prefix=API_PREFIX)
    app.include_router(transactions.router, prefix=API_PREFIX)
    app.include_router(watchlist.router, prefix=API_PREFIX)

    @app.get("/health", tags=["Meta"])
    def health() -> dict:
        return {"status": "ok"}

    return app
