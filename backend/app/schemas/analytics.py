"""P&L analytics request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class StockPnl(BaseModel):
    """Profit & loss detail for a stock position (or aggregated across portfolios)."""

    stock_id: int
    symbol: str
    short_name: Optional[str] = None
    portfolio_id: Optional[int] = None
    quantity: Decimal
    avg_buy_price: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    cost_basis: Decimal
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_pct: Optional[float] = None
    realized_pnl: Decimal
    invested: Decimal
    total_pnl: Optional[Decimal] = None
    total_pnl_pct: Optional[float] = None


class PortfolioPnl(BaseModel):
    """Portfolio-wide P&L summary with a per-holding breakdown."""

    portfolio_id: int
    holdings_count: int
    total_cost_basis: Decimal
    total_market_value: Optional[Decimal] = None
    total_unrealized_pnl: Optional[Decimal] = None
    total_unrealized_pnl_pct: Optional[float] = None
    total_realized_pnl: Decimal
    total_pnl: Optional[Decimal] = None
    total_pnl_pct: Optional[float] = None
    total_invested: Decimal
    holdings: list[StockPnl]


class AllocationGroup(BaseModel):
    """A single pie-chart slice: holdings count per sector / quote_type."""

    label: str
    holdings_count: int
    weight: float


class AllocationInsight(BaseModel):
    """Portfolio allocation by a stock attribute, for pie charts."""

    portfolio_id: int
    grouping: str
    total_holdings: int
    groups: list[AllocationGroup]


class PortfolioPerformers(BaseModel):
    """Top and worst current holding of a portfolio, ranked by a P&L metric."""

    portfolio_id: int
    name: Optional[str] = None
    holdings_count: int
    metric: str
    top_performer: Optional[StockPnl] = None
    worst_performer: Optional[StockPnl] = None


class PerformersResponse(BaseModel):
    """Top / worst performers across a user's portfolios."""

    portfolios: list[PortfolioPerformers]


class RiskMetrics(BaseModel):
    """Statistical risk metrics for a return series (percent values are decimals, e.g. 0.2 = 20%)."""

    annualized_return: Optional[float] = None
    annualized_volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    value_at_risk_95: Optional[float] = None
    value_at_risk_99: Optional[float] = None
    beta: Optional[float] = None


class PortfolioRisk(BaseModel):
    """Risk evaluation for a portfolio's current holdings, weighted by market value."""

    portfolio_id: int
    name: Optional[str] = None
    weights_count: int
    observations: int
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    risk_free_rate: float
    benchmark: Optional[str] = None
    metrics: RiskMetrics
    benchmark_metrics: Optional[RiskMetrics] = None


class PortfoliosRiskResponse(BaseModel):
    """Risk evaluation across a user's portfolios."""

    portfolios: list[PortfolioRisk]
