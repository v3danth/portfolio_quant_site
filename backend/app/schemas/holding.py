"""Holding request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class Holding(BaseModel):
    """A current position with optional live valuation."""

    portfolio_id: int
    stock_id: int
    symbol: str
    short_name: Optional[str] = None
    quantity: Decimal
    avg_buy_price: Optional[Decimal] = Decimal("0.0")
    price_live: Optional[Decimal] = Decimal("0.0")
    market_value: Optional[Decimal] = Decimal("0.0")
    is_position: bool = False
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HoldingBuy(BaseModel):
    """Payload to buy / add a stock to a portfolio.

    Quantity is whole-share only: fractional shares are not supported.
    """

    symbol: str
    quantity: int = Field(..., gt=0)
    price: Optional[Decimal] = Field(default=None, gt=0, description="Price per unit. Defaults to live price.")
