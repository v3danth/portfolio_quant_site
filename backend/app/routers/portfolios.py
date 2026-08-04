"""Portfolios API routes."""
from typing import Annotated

from app.models import portfolio as portfolio_model
from app.models import user as user_model
from app.schemas.portfolio import Portfolio, PortfolioCreate
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


@router.get("", response_model=list[Portfolio], summary="List portfolios for the user")
def list_portfolios(user_id: Annotated[int, Query(alias="userId")]):
    """Return all portfolios belonging to a user."""
    return portfolio_model.get_portfolios_by_user(user_id)


@router.post(
    "",
    response_model=Portfolio,
    status_code=status.HTTP_201_CREATED,
    summary="Create a portfolio",
)
def create_portfolio(payload: PortfolioCreate):
    """Create a new portfolio for an existing user."""
    if user_model.get_user_by_id(payload.user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {payload.user_id} not found",
        )
    return portfolio_model.create_portfolio(payload.user_id, payload.name)


@router.get("/{portfolio_id}", response_model=Portfolio, summary="Get a portfolio")
def get_portfolio(portfolio_id: int):
    """Return a single portfolio by id."""
    row = portfolio_model.get_portfolio_by_id(portfolio_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    return row


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a portfolio",
)
def delete_portfolio(portfolio_id: int):
    """Delete a portfolio by id."""
    removed = portfolio_model.delete_portfolio(portfolio_id)
    if removed == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
