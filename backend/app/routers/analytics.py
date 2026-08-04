"""Portfolio analytics API routes: performance, P&L, returns, benchmarking."""
from datetime import date
from typing import Annotated

from app.models import analytics as analytics_model
from app.models import portfolio as portfolio_model
from app.models import stock as stock_model
from app.schemas.analytics import (
    BenchmarkComparison,
    HoldingPnL,
    PortfolioPerformance,
    ReturnMetrics,
    TopMovers,
    ValuePoint,
)
from app.services import analytics as analytics_service
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/portfolios/{portfolio_id}/analytics", tags=["Analytics"])


def _require_portfolio(portfolio_id: int) -> None:
    if portfolio_model.get_portfolio_by_id(portfolio_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )


@router.get(
    "/performance",
    response_model=PortfolioPerformance,
    summary="Total portfolio value, day change and total P&L",
)
def get_performance(portfolio_id: int):
    _require_portfolio(portfolio_id)
    return analytics_model.get_portfolio_performance(portfolio_id)


@router.get(
    "/holdings-pnl",
    response_model=list[HoldingPnL],
    summary="Per-holding cost basis, market value and unrealized P&L",
)
def get_holdings_pnl(portfolio_id: int):
    _require_portfolio(portfolio_id)
    return analytics_model.get_holdings_pnl(portfolio_id)


@router.get(
    "/top-movers",
    response_model=TopMovers,
    summary="Best / worst performing holdings by unrealized P&L %",
)
def get_top_movers(
    portfolio_id: int,
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
):
    _require_portfolio(portfolio_id)
    return analytics_model.get_top_movers(portfolio_id, limit)


@router.get(
    "/returns",
    response_model=ReturnMetrics,
    summary="Time-weighted (TWR) and money-weighted (XIRR) returns",
)
def get_returns(portfolio_id: int):
    _require_portfolio(portfolio_id)

    history = analytics_model.get_portfolio_value_history(portfolio_id)
    if history.empty:
        twr = 0.0
    else:
        contributions = -history["cash_flow"]
        twr = analytics_service.time_weighted_return(history["value"], contributions)

    cashflows = analytics_model.get_portfolio_cashflows(portfolio_id)
    performance = analytics_model.get_portfolio_performance(portfolio_id)
    terminal_value = float(performance["total_market_value"])
    if terminal_value > 0:
        cashflows = cashflows + [(date.today(), terminal_value)]
    mwr = analytics_service.xirr(cashflows) if cashflows else None

    return {
        "portfolio_id": portfolio_id,
        "time_weighted_return": twr,
        "money_weighted_return": mwr,
        "as_of": date.today().isoformat(),
    }


@router.get(
    "/benchmark",
    response_model=BenchmarkComparison,
    summary="Portfolio cumulative return vs. a benchmark symbol (e.g. SPY)",
)
def get_benchmark_comparison(
    portfolio_id: int,
    symbol: Annotated[str, Query(description="Benchmark ticker, e.g. SPY")] = "SPY",
):
    _require_portfolio(portfolio_id)

    benchmark_stock = stock_model.get_stock_by_symbol(symbol)
    if benchmark_stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark symbol '{symbol}' not found. Seed it via the stock loader first.",
        )

    history = analytics_model.get_portfolio_value_history(portfolio_id)
    if history.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio has no trade history to compare against a benchmark",
        )

    benchmark_close = stock_model.get_close_series(benchmark_stock["stock_id"])
    if benchmark_close.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No price history available for benchmark '{symbol}'",
        )
    benchmark_close.index = benchmark_close.index.normalize()

    aligned = history.join(benchmark_close.rename("benchmark_close"), how="inner")
    aligned = aligned[aligned["value"] > 0].dropna(subset=["benchmark_close"])
    if aligned.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No overlapping dates between portfolio history and benchmark prices",
        )

    portfolio_rebased = aligned["value"] / aligned["value"].iloc[0] * 100
    benchmark_rebased = aligned["benchmark_close"] / aligned["benchmark_close"].iloc[0] * 100

    portfolio_total_return = float(portfolio_rebased.iloc[-1] / 100 - 1)
    benchmark_total_return = float(benchmark_rebased.iloc[-1] / 100 - 1)

    series = [
        ValuePoint(
            date=idx.date().isoformat(),
            portfolio_value=float(p),
            benchmark_value=float(b),
        )
        for idx, p, b in zip(aligned.index, portfolio_rebased, benchmark_rebased)
    ]

    return {
        "portfolio_id": portfolio_id,
        "benchmark_symbol": symbol.upper(),
        "portfolio_total_return": portfolio_total_return,
        "benchmark_total_return": benchmark_total_return,
        "alpha": portfolio_total_return - benchmark_total_return,
        "series": series,
    }
