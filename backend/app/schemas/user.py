"""User request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User response model (name + cash balance)."""

    user_id: int
    user_name: str
    email: Optional[EmailStr] = None
    acct_balance: Decimal = Field(..., description="Cash balance, NUMERIC(18,2).")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
