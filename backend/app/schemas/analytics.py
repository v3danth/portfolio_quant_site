"""Analytics request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PerformanceSeries(BaseModel):
    """Portfolio value over time and its wealth index (for charts)."""

    timestamps: list[datetime]
    values: list[float]
    wealth_index: list[float] = []


class PortfolioAnalytics(BaseModel):
    """Risk and performance analytics bundle for a portfolio."""

    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    time_weighted_return: float = 0.0
    money_weighted_return: Optional[float] = None
    wealth_index: list[float] = []
    drawdown: list[float] = []
    factor_loadings: Optional[dict[str, float]] = None
