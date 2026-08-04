"""Transaction request/response schemas."""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TransType(str, Enum):
    """Transaction types."""

    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    DIVIDEND = "DIVIDEND"


class Transaction(BaseModel):
    """An immutable transaction record."""

    trans_id: int
    portfolio_id: int
    stock_id: Optional[int] = None
    trans_type: TransType
    quantity: Optional[Decimal] = Decimal("0.0")
    price: Optional[Decimal] = Decimal("0.0")
    amount: Optional[Decimal] = Decimal("0.0")
    trans_details: Optional[str] = None
    ts: datetime

    class Config:
        from_attributes = True


class TransactionRangeResponse(BaseModel):
    """Transaction history for a selected time interval."""

    portfolio_id: int
    range_label: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_count: int
    total_amount: Decimal
    transactions: list[Transaction]
