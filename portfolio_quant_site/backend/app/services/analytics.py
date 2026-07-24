"""Portfolio analytics.

Pure-pandas/numpy implementations of the formulas in docs/MATH_SPECS.md.
All returns are simple returns in decimal form (1% = 0.01). Functions accept a
price ``pd.Series`` or a returns ``pd.Series`` as noted and are side-effect free.
"""
from typing import Optional

import numpy as np
import pandas as pd

# Trading periods per year for common intervals.
PERIODS_PER_YEAR = {
    "1d": 252,
    "1wk": 52,
    "1mo": 12,
    "1h": 252 * 6.5,
}


def periods_per_year(interval: str) -> float:
    """Return trading periods per year for an interval (defaults to daily)."""
    return PERIODS_PER_YEAR.get(interval, 252)


# --- Returns --------------------------------------------------------------

def period_returns(prices: pd.Series) -> pd.Series:
    """Simple period returns from a price series: R_t = P_t / P_{t-1} - 1."""
    return prices.pct_change().dropna()


def holding_period_return(prices: pd.Series) -> float:
    """Total return from first to last price: V_f / V_i - 1."""
    if len(prices) < 2:
        return 0.0
    return float(prices.iloc[-1] / prices.iloc[0] - 1)


def compounded_return(returns: pd.Series) -> float:
    """Compounded return across periods: prod(1 + R_t) - 1."""
    return float(np.prod(1 + returns) - 1)


# --- Risk -----------------------------------------------------------------

def sample_volatility(returns: pd.Series) -> float:
    """Sample standard deviation of returns (ddof=1)."""
    return float(returns.std(ddof=1))


def annualize_return(period_return: float, ppy: float) -> float:
    """Convert a per-period return to an annualised return: (1 + R)^P - 1."""
    return float((1 + period_return) ** ppy - 1)


def annualize_volatility(period_vol: float, ppy: float) -> float:
    """Scale periodic volatility to annual via sqrt-of-time: sigma * sqrt(P)."""
    return float(period_vol * np.sqrt(ppy))


def sharpe_ratio(annual_return: float, annual_vol: float, risk_free_rate: float = 0.0) -> float:
    """Excess return per unit of volatility. Returns 0.0 if volatility is 0."""
    if annual_vol == 0:
        return 0.0
    return float((annual_return - risk_free_rate) / annual_vol)


# --- Wealth & drawdown ----------------------------------------------------

def wealth_index(returns: pd.Series, initial_wealth: float = 1.0) -> pd.Series:
    """Growth of one unit invested: WI_t = WI_{t-1}(1 + R_t)."""
    return initial_wealth * (1 + returns).cumprod()


def cumulative_return(returns: pd.Series) -> float:
    """Cumulative return over the whole series: WI_last - 1."""
    if returns.empty:
        return 0.0
    return float(wealth_index(returns).iloc[-1] - 1)


def drawdown(wi: pd.Series) -> pd.Series:
    """Drawdown from running peak: WI_t / cummax(WI)_t - 1 (<= 0)."""
    return wi / wi.cummax() - 1


def max_drawdown(returns: pd.Series) -> float:
    """Worst peak-to-trough decline over the series."""
    if returns.empty:
        return 0.0
    return float(drawdown(wealth_index(returns)).min())


# --- Aggregate ------------------------------------------------------------

def analyze_prices(prices: pd.Series, interval: str = "1d", risk_free_rate: float = 0.0) -> dict:
    """Compute the full analytics bundle from a price series.

    Returns keys matching the PortfolioAnalytics schema:
    total_return, annualized_return, annualized_volatility, sharpe_ratio,
    max_drawdown, wealth_index, drawdown.
    """
    if prices is None or len(prices) < 2:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "wealth_index": [],
            "drawdown": [],
        }

    ppy = periods_per_year(interval)
    rets = period_returns(prices)

    total = compounded_return(rets)
    mean_period_return = float(rets.mean())
    ann_return = annualize_return(mean_period_return, ppy)
    ann_vol = annualize_volatility(sample_volatility(rets), ppy)
    wi = wealth_index(rets)
    dd = drawdown(wi)

    return {
        "total_return": total,
        "annualized_return": ann_return,
        "annualized_volatility": ann_vol,
        "sharpe_ratio": sharpe_ratio(ann_return, ann_vol, risk_free_rate),
        "max_drawdown": float(dd.min()),
        "wealth_index": wi.tolist(),
        "drawdown": dd.tolist(),
    }
