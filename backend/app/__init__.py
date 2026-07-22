"""Application factory and router registration."""
from app.routers import portfolios, stocks, users, holdings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Quantitative Portfolio Management System (QPMS) API",
        version="1.0.0",
        description="REST API for the Quantitative Portfolio Management System.",
    )

    # CORS — allow the Streamlit frontend to call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers here. Add new modules (transactions, analytics, ...) below.
    app.include_router(users.router, prefix=API_PREFIX)
    app.include_router(stocks.router, prefix=API_PREFIX)
    app.include_router(portfolios.router, prefix=API_PREFIX)
    app.include_router(holdings.router, prefix=API_PREFIX)

    @app.get("/health", tags=["Meta"])
    def health() -> dict:
        return {"status": "ok"}

    return app
