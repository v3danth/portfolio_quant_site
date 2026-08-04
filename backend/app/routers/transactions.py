"""Transactions API routes."""
from typing import Annotated, Optional

from app.models import portfolio as portfolio_model
from app.models import transaction as transaction_model
from app.schemas.transaction import Transaction, TransType
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/portfolios/{portfolio_id}/transactions", tags=["Transactions"])


@router.get("", response_model=list[Transaction], summary="Transaction history for a portfolio")
def list_transactions(
    portfolio_id: int,
    trans_type: Annotated[Optional[TransType], Query(alias="transType")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Return a portfolio's transactions, newest first."""
    if portfolio_model.get_portfolio_by_id(portfolio_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    type_value = trans_type.value if trans_type is not None else None
    return transaction_model.get_transactions(
        portfolio_id, trans_type=type_value, limit=limit, offset=offset
    )
