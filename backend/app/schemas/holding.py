"""Holding and transaction request/response schemas."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransType(str, Enum):
    """Transaction types."""

    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    DIVIDEND = "DIVIDEND"


class Holding(BaseModel):
    """A current position with optional live valuation."""

    portfolio_id: int
    stock_id: int
    symbol: str
    short_name: Optional[str] = None
    quantity: Decimal
    avg_buy_price: Optional[Decimal] = None
    price_live: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HoldingBuy(BaseModel):
    """Payload to buy / add a stock to a portfolio."""

    symbol: str
    quantity: Decimal = Field(..., gt=0)
    price: Optional[Decimal] = Field(
        default=None,
        description="Buy price per unit. Defaults to latest live price if omitted.",
    )


class Transaction(BaseModel):
    """An immutable transaction record."""

    trans_id: int
    portfolio_id: int
    stock_id: Optional[int] = None
    trans_type: TransType
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    trans_details: Optional[str] = None
    ts: datetime

    class Config:
        from_attributes = True
