from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Stock(BaseModel):
    stock_id: int
    symbol: str
    exchange: Optional[str] = None
    quote_type: Optional[str] = None
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    business_summary: Optional[str] = None
    market_cap: Optional[int] = None
    shares_outstanding: Optional[int] = None
    first_seen_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
