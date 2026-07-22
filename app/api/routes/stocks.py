"""Registers stock resource routes."""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import with_connection
from app.repositories.portfolio import fetch_prices, fetch_stock, fetch_stocks


def get_stock_router() -> APIRouter:
    """Builds routes for stock and price resources."""
    router = APIRouter(prefix="/api/stocks", tags=["stocks"])

    @router.get("")
    def list_stocks() -> list[dict]:
        """Returns all known stocks with their latest prices."""
        return with_connection(fetch_stocks)

    @router.get("/{stock_id}")
    def get_stock(stock_id: int) -> dict:
        """Returns an individual stock record."""
        stock = with_connection(lambda connection: fetch_stock(connection, stock_id))
        if stock is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found.")
        return stock

    @router.get("/{stock_id}/prices")
    def list_prices(stock_id: int, interval: str = "1d") -> list[dict]:
        """Returns historical prices for one stock and interval."""
        return with_connection(lambda connection: fetch_prices(connection, stock_id, interval))

    return router
