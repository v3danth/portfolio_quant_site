"""Holdings API routes (browse / buy / sell)."""
from decimal import Decimal
from typing import Annotated, Optional

from app.models import holding as holding_model
from app.models import portfolio as portfolio_model
from app.models import stock as stock_model
from app.schemas.holding import Holding, HoldingBuy, Transaction
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/portfolios/{portfolio_id}/holdings", tags=["Holdings"])


def _require_portfolio(portfolio_id: int) -> None:
    """Raise 404 if the portfolio does not exist."""
    if portfolio_model.get_portfolio_by_id(portfolio_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


def _latest_price(stock_id: int) -> Optional[Decimal]:
    """Return the latest live price for a stock, or None."""
    quote = stock_model.get_latest_quote(stock_id)
    return Decimal(quote["price"]) if quote else None


@router.get("", response_model=list[Holding], summary="Browse portfolio holdings (with live value)")
def list_holdings(portfolio_id: int):
    """Return the current positions for a portfolio."""
    _require_portfolio(portfolio_id)
    return holding_model.get_holdings(portfolio_id)


@router.post(
    "",
    response_model=Holding,
    status_code=status.HTTP_201_CREATED,
    summary="Add / buy a stock into the portfolio",
)
def add_holding(portfolio_id: int, payload: HoldingBuy):
    """Buy a stock: debit cash, upsert holding, record a BUY transaction."""
    _require_portfolio(portfolio_id)

    stock = stock_model.get_stock_by_symbol(payload.symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown stock symbol '{payload.symbol}'",
        )

    price = payload.price if payload.price is not None else _latest_price(stock["stock_id"])
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No price provided and no live price available",
        )

    try:
        return holding_model.buy_stock(portfolio_id, stock["stock_id"], payload.quantity, price)
    except holding_model.InsufficientFundsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete(
    "/{stock_id}",
    response_model=Transaction,
    summary="Remove / sell a stock from the portfolio",
)
def sell_holding(
    portfolio_id: int,
    stock_id: int,
    quantity: Annotated[Optional[Decimal], Query(gt=0, description="Quantity to sell. Omit to sell all.")] = None,
    price: Annotated[Optional[Decimal], Query(gt=0, description="Sell price per unit. Defaults to live price.")] = None,
):
    """Sell part or all of a position: credit cash, record a SELL transaction."""
    _require_portfolio(portfolio_id)

    sell_price = price if price is not None else _latest_price(stock_id)
    if sell_price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No price provided and no live price available",
        )

    try:
        return holding_model.sell_stock(portfolio_id, stock_id, sell_price, quantity)
    except holding_model.InsufficientQuantityError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
