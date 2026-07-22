"""Stocks API routes."""
from datetime import datetime
from typing import Annotated, Optional

from app.models import stock as stock_model
from app.schemas.stock import PriceCandle, Quote, Stock, StockSummary
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get("", response_model=list[StockSummary], summary="List known stocks (name and/or symbol)")
def list_stocks(
    search: Annotated[Optional[str], Query(description="Filter by symbol or name substring.")] = None,
    sector: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Return a filtered, paged list of stocks."""
    return stock_model.get_stocks(search=search, sector=sector, limit=limit, offset=offset)


@router.get("/{stock_id}", response_model=Stock, summary="Get full stock detail")
def get_stock(stock_id: int):
    """Return full stock detail by id."""
    row = stock_model.get_stock_by_id(stock_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {stock_id} not found",
        )
    return row


@router.get(
    "/{stock_id}/prices",
    response_model=list[PriceCandle],
    summary="Price history (OHLC candles) for a stock",
)
def get_stock_prices(
    stock_id: int,
    interval: Annotated[str, Query(description="Candle interval (1d, 1h, 5m, ...).")] = "1d",
    start: Annotated[Optional[datetime], Query(description="Inclusive start timestamp.")] = None,
    end: Annotated[Optional[datetime], Query(description="Inclusive end timestamp.")] = None,
):
    """Return candles for the requested interval and time frame."""
    return stock_model.get_stock_prices(stock_id, interval=interval, start=start, end=end)


@router.get("/{stock_id}/quote", response_model=Quote, summary="Latest live price for a stock")
def get_stock_quote(stock_id: int):
    """Return the most recent price row as a quote."""
    row = stock_model.get_latest_quote(stock_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data for stock {stock_id}",
        )
    return row
