"""Analytics request/response schemas."""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class HoldingPnL(BaseModel):
    """Cost basis vs. current value for a single position."""

    stock_id: int
    symbol: str
    short_name: Optional[str] = None
    quantity: Decimal
    avg_buy_price: Decimal
    price_live: Decimal
    cost_basis: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: float

    class Config:
        from_attributes = True


class PortfolioPerformance(BaseModel):
    """Portfolio-wide value and P&L summary."""

    portfolio_id: int
    total_market_value: Decimal
    total_cost_basis: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_pct: float
    day_change: Decimal
    day_change_pct: float
    holdings_count: int


class TopMovers(BaseModel):
    """Best and worst performing holdings by unrealized P&L %."""

    top_gainers: list[HoldingPnL]
    top_losers: list[HoldingPnL]


class ReturnMetrics(BaseModel):
    """Cash-flow-aware return metrics for a portfolio."""

    portfolio_id: int
    time_weighted_return: float
    money_weighted_return: Optional[float] = None
    as_of: str


class ValuePoint(BaseModel):
    date: str
    portfolio_value: float
    benchmark_value: float


class BenchmarkComparison(BaseModel):
    """Portfolio cumulative return vs. a benchmark symbol, rebased to 100."""

    portfolio_id: int
    benchmark_symbol: str
    portfolio_total_return: float
    benchmark_total_return: float
    alpha: float
    series: list[ValuePoint]
