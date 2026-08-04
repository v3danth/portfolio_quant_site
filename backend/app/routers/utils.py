"""Common route utilities and validators."""
from functools import wraps
from inspect import signature

from app.models import portfolio as portfolio_model
from fastapi import HTTPException, status


def require_portfolio_exists(func):
    """Decorator that validates portfolio_id exists before executing the route."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        portfolio_id = kwargs.get("portfolio_id") or (
            args[0] if args and "portfolio_id" in signature(func).parameters else None
        )
        if portfolio_id is not None:
            if portfolio_model.get_portfolio_by_id(portfolio_id) is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Portfolio {portfolio_id} not found",
                )
        return func(*args, **kwargs)
    return wrapper


def require_portfolio(portfolio_id: int) -> None:
    """Raise 404 if the portfolio does not exist."""
    if portfolio_model.get_portfolio_by_id(portfolio_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
