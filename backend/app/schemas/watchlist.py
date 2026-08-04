"""Watchlist request/response schemas."""

from pydantic import BaseModel

from app.schemas.stock import StockSummary


class WatchlistItem(StockSummary):
    """A stock entry returned from the single watchlist."""

    class Config:
        from_attributes = True


class WatchlistAddRequest(BaseModel):
    """Payload for adding a stock by symbol to the watchlist."""

    symbol: str
