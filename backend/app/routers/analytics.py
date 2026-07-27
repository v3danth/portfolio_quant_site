"""Analytics API routes (portfolio performance and risk)."""
from datetime import datetime
from typing import Annotated, Optional

import pandas as pd
from app.models import portfolio as portfolio_model
from app.models import stock as stock_model
from app.models import transaction as transaction_model
from app.schemas.analytics import PerformanceSeries, PortfolioAnalytics
from app.services import analytics
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/portfolios/{portfolio_id}/analytics", tags=["Analytics"])
performance_router = APIRouter(prefix="/portfolios/{portfolio_id}/performance", tags=["Analytics"])


def _require_portfolio(portfolio_id: int) -> None:
    """Raise 404 if the portfolio does not exist."""
    if portfolio_model.get_portfolio_by_id(portfolio_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


def _value_and_trades(
    portfolio_id: int,
    interval: str,
    start: Optional[datetime],
    end: Optional[datetime],
) -> tuple[pd.Series, list[dict]]:
    """Build the point-in-time portfolio value Series plus its trade ledger.

    Quantities held on each date are reconstructed from the BUY/SELL
    transaction log, so the series reflects what was actually owned over time
    (including stocks since sold), not just the current basket. The trades are
    returned too, for cash-flow-adjusted (TWR) and money-weighted (XIRR) returns.
    """
    trades = transaction_model.get_stock_trades(portfolio_id)
    if not trades:
        return pd.Series(dtype="float64", name="value"), []

    # Every stock ever traded needs price history for historical valuation.
    stock_ids = {trade["stock_id"] for trade in trades}
    price_series_by_stock = {
        stock_id: stock_model.get_close_series(
            stock_id, interval=interval, start=start, end=end
        )
        for stock_id in stock_ids
    }
    value = analytics.portfolio_value_series(price_series_by_stock, trades)
    return value, trades


@performance_router.get(
    "",
    response_model=PerformanceSeries,
    summary="Portfolio value over time (for charts)",
)
def get_portfolio_performance(
    portfolio_id: int,
    interval: Annotated[str, Query(description="Candle interval (1d, 1wk, 1mo).")] = "1d",
    start: Annotated[Optional[datetime], Query()] = None,
    end: Annotated[Optional[datetime], Query()] = None,
):
    """Return the portfolio value time series and its (time-weighted) wealth index."""
    _require_portfolio(portfolio_id)

    value, trades = _value_and_trades(portfolio_id, interval, start, end)
    if value.empty:
        return PerformanceSeries(timestamps=[], values=[], wealth_index=[])

    cash_flows = analytics.cash_flow_series(trades, value.index)
    returns = analytics.time_weighted_returns(value, cash_flows)
    wi = analytics.wealth_index(returns)
    return PerformanceSeries(
        timestamps=value.index.to_pydatetime().tolist(),
        values=value.tolist(),
        wealth_index=wi.tolist(),
    )


@router.get(
    "",
    response_model=PortfolioAnalytics,
    summary="Risk & performance analytics",
)
def get_portfolio_analytics(
    portfolio_id: int,
    risk_free_rate: Annotated[float, Query(alias="riskFreeRate", description="Annualized risk-free rate (decimal).")] = 0.0,
    interval: Annotated[str, Query(description="Candle interval (1d, 1wk, 1mo).")] = "1d",
    start: Annotated[Optional[datetime], Query()] = None,
    end: Annotated[Optional[datetime], Query()] = None,
):
    """Return returns, volatility, Sharpe, drawdown and the wealth index."""
    _require_portfolio(portfolio_id)

    value, trades = _value_and_trades(portfolio_id, interval, start, end)
    cash_flows = analytics.cash_flow_series(trades, value.index) if not value.empty else None
    bundle = analytics.analyze_prices(
        value, interval=interval, risk_free_rate=risk_free_rate, cash_flows=cash_flows
    )

    # Money-weighted (XIRR) return from the ledger + terminal market value.
    money_weighted = None
    if not value.empty:
        money_weighted = analytics.portfolio_xirr(trades, float(value.iloc[-1]), value.index[-1])

    bundle["time_weighted_return"] = bundle["total_return"]
    bundle["money_weighted_return"] = money_weighted
    return PortfolioAnalytics(**bundle)
