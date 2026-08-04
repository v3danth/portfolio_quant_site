"""Portfolio analytics.

Pure-pandas/numpy implementations of the formulas in docs/MATH_SPECS.md.
All returns are simple returns in decimal form (1% = 0.01). Functions accept a
price ``pd.Series`` or a returns ``pd.Series`` as noted and are side-effect free.
"""
from datetime import date
from typing import Optional, Sequence

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


# --- Cash-flow-aware returns (TWR / XIRR) ----------------------------------

def time_weighted_return(values: pd.Series, external_flows: pd.Series) -> float:
    """Time-weighted return, linking daily sub-periods around external cash flows.

    Args:
        values: portfolio market value at the end of each date (index = date).
        external_flows: net external contribution for that date (positive =
            money added to the invested pool, e.g. a buy; negative = a sell),
            aligned to the same index as ``values``.

    Sub-period return excludes the effect of that period's flow:
        r_t = (V_t - CF_t) / V_{t-1} - 1
    The overall TWR is the geometric link of all sub-period returns.
    """
    if values is None or len(values) < 2:
        return 0.0

    flows = external_flows.reindex(values.index).fillna(0.0)
    prev_values = values.shift(1)

    sub_returns = []
    for t in range(1, len(values)):
        v_prev = float(prev_values.iloc[t])
        v_curr = float(values.iloc[t])
        cf = float(flows.iloc[t])
        if v_prev == 0:
            continue
        sub_returns.append((v_curr - cf) / v_prev - 1)

    if not sub_returns:
        return 0.0
    return float(np.prod([1 + r for r in sub_returns]) - 1)


def xirr(cashflows: Sequence[tuple[date, float]], guess: float = 0.1) -> Optional[float]:
    """Money-weighted annualized return solving NPV(cashflows) = 0 for the rate.

    Args:
        cashflows: (date, amount) pairs. Outflows (buys) are negative, inflows
            (sells, and a final terminal value) are positive. Must contain at
            least one negative and one positive amount.
        guess: unused placeholder kept for API symmetry; solved via bisection.

    Returns:
        The annualized rate as a decimal (0.10 = 10%), or None if it can't be
        solved (e.g. all flows have the same sign, or no convergence).
    """
    if len(cashflows) < 2:
        return None

    amounts = [amt for _, amt in cashflows]
    if not (any(a > 0 for a in amounts) and any(a < 0 for a in amounts)):
        return None

    t0 = min(d for d, _ in cashflows)
    times = [(d - t0).days / 365.0 for d, _ in cashflows]

    def npv(rate: float) -> float:
        return sum(amt / (1 + rate) ** t for amt, t in zip(amounts, times))

    low, high = -0.999999, 10.0
    npv_low, npv_high = npv(low), npv(high)
    if npv_low * npv_high > 0:
        return None

    for _ in range(200):
        mid = (low + high) / 2
        npv_mid = npv(mid)
        if abs(npv_mid) < 1e-6:
            return float(mid)
        if npv_low * npv_mid < 0:
            high = mid
            npv_high = npv_mid
        else:
            low = mid
            npv_low = npv_mid

    return float((low + high) / 2)
