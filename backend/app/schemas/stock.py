"""Stock request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class StockSummary(BaseModel):
    """Lightweight stock listing entry."""

    stock_id: int
    symbol: str
    short_name: Optional[str] = None
    sector: Optional[str] = None

    class Config:
        from_attributes = True


class Stock(StockSummary):
    """Full stock detail."""

    exchange: Optional[str] = None
    quote_type: Optional[str] = None
    long_name: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    business_summary: Optional[str] = None
    market_cap: Optional[int] = None
    shares_outstanding: Optional[int] = None
    first_seen_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PriceCandle(BaseModel):
    """A single OHLC candle."""

    ts: datetime
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Optional[Decimal] = None
    volume: Optional[int] = None
    dividend: Optional[Decimal] = None
    stock_split: Optional[Decimal] = None

    class Config:
        from_attributes = True


class Quote(BaseModel):
    """Latest live price for a stock."""

    stock_id: int
    symbol: str
    price: Decimal
    ts: datetime

    class Config:
        from_attributes = True
