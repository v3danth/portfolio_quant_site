"""Registers user and portfolio resource routes."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Response, status

from app.api.dependencies import get_backend, with_connection
from app.api.validation import (get_integer, get_optional_text,
                                get_positive_number, get_required_text)
from app.repository import (create_holding, create_portfolio, create_user,
                            delete_holding, fetch_holdings, fetch_performance,
                            fetch_portfolio, fetch_transactions)


def create_portfolio_resource(connection, backend: str, user_id: int, name: str) -> dict:
    """Creates a portfolio and maps absent users to an HTTP error."""
    try:
        return create_portfolio(connection, backend, user_id, name)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


def create_holding_resource(connection, backend: str, portfolio_id: int, symbol: str, quantity: float, price: float) -> dict:
    """Creates a holding and maps absent portfolios to an HTTP error."""
    try:
        return create_holding(connection, backend, portfolio_id, symbol, quantity, price)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


def get_portfolio_router() -> APIRouter:
    """Builds routes for users, portfolios, and holdings."""
    router = APIRouter(tags=["portfolios"])

    @router.post("/api/users", status_code=status.HTTP_201_CREATED)
    def post_user(payload: Annotated[dict, Body()]) -> dict:
        """Creates a user for portfolio ownership."""
        user_name = get_required_text(payload, "user_name")
        email = get_optional_text(payload, "email")
        return with_connection(lambda connection: create_user(connection, get_backend(), user_name, email))

    @router.post("/api/portfolios", status_code=status.HTTP_201_CREATED)
    def post_portfolio(payload: Annotated[dict, Body()]) -> dict:
        """Creates a named portfolio for a user."""
        user_id = get_integer(payload, "user_id")
        name = payload.get("name", "My Portfolio")
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="name must be a non-empty string.")
        return with_connection(lambda connection: create_portfolio_resource(connection, get_backend(), user_id, name.strip()))

    @router.get("/api/portfolios/{portfolio_id}/holdings")
    def list_holdings(portfolio_id: int) -> list[dict]:
        """Returns the current holdings of a portfolio."""
        portfolio = with_connection(lambda connection: fetch_portfolio(connection, portfolio_id))
        if portfolio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found.")
        return with_connection(lambda connection: fetch_holdings(connection, portfolio_id))

    @router.post("/api/portfolios/{portfolio_id}/holdings", status_code=status.HTTP_201_CREATED)
    def post_holding(portfolio_id: int, payload: Annotated[dict, Body()]) -> dict:
        """Buys a holding and persists its transaction."""
        symbol = get_required_text(payload, "symbol")
        quantity = get_positive_number(payload, "quantity")
        price = get_positive_number(payload, "price")
        return with_connection(lambda connection: create_holding_resource(connection, get_backend(), portfolio_id, symbol, quantity, price))

    @router.delete("/api/portfolios/{portfolio_id}/holdings/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_holding(portfolio_id: int, stock_id: int) -> Response:
        """Sells and removes a portfolio holding."""
        removed = with_connection(lambda connection: delete_holding(connection, get_backend(), portfolio_id, stock_id))
        if not removed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/api/portfolios/{portfolio_id}/transactions")
    def list_transactions(portfolio_id: int) -> list[dict]:
        """Returns portfolio transaction history."""
        return with_connection(lambda connection: fetch_transactions(connection, portfolio_id))

    @router.get("/api/portfolios/{portfolio_id}/performance")
    def get_performance(portfolio_id: int) -> list[dict]:
        """Returns daily historical market values for the portfolio."""
        return with_connection(lambda connection: fetch_performance(connection, portfolio_id))

    return router
