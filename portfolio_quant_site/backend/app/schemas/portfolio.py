"""Portfolio request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Portfolio(BaseModel):
    """Portfolio response model."""

    portfolio_id: int
    user_id: int
    name: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortfolioCreate(BaseModel):
    """Payload to create a portfolio."""

    user_id: int
    name: str = Field(default="My Portfolio")
