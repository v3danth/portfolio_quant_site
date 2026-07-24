"""Formatting helpers and client-side analytics.

The analytics functions mirror ``backend/app/services/analytics.py`` (same
formulas, documented in ``docs/MATH_SPECS.md``) so the numbers shown here are
consistent with the backend's math, without importing backend internals.
"""
from typing import Any, Optional

import numpy as np
import pandas as pd

PERIODS_PER_YEAR = {"1d": 252, "1wk": 52, "1mo": 12, "1h": 252 * 6.5}


def periods_per_year(interval: str) -> float:
    return PERIODS_PER_YEAR.get(interval, 252)


# --- Formatting -------------------------------------------------------

def format_currency(value: Optional[float]) -> str:
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"


def format_pct(value: Optional[float]) -> str:
    if value is None:
        return "0.00%"
    return f"{value * 100:,.2f}%"


# --- Holdings -----------------------------------------------------------

def holdings_dataframe(holdings: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in holdings:
        qty = float(item.get("quantity") or 0)
        avg_price = float(item.get("avg_buy_price") or 0)
        live_price = float(item.get("price_live") or 0)
        market_value = float(item.get("market_value") or 0)
        rows.append(
            {
                "stock_id": item.get("stock_id"),
                "symbol": item.get("symbol", ""),
                "short_name": item.get("short_name") or "",
                "quantity": qty,
                "avg_buy_price": avg_price,
                "price_live": live_price,
                "market_value": market_value,
                "unrealized_pnl": (live_price - avg_price) * qty if qty else 0.0,
            }
        )
    return pd.DataFrame(rows)


def portfolio_metrics(holdings: list[dict[str, Any]], cash_balance: float) -> dict[str, float]:
    market_value = sum(float(item.get("market_value") or 0) for item in holdings)
    invested_value = sum(
        float(item.get("avg_buy_price") or 0) * float(item.get("quantity") or 0) for item in holdings
    )
    pnl = market_value - invested_value
    return {
        "cash_balance": cash_balance,
        "market_value": market_value,
        "equity": cash_balance + market_value,
        "invested_value": invested_value,
        "pnl": pnl,
        "pnl_pct": pnl / invested_value if invested_value else 0.0,
    }


# --- Analytics (ported from backend/app/services/analytics.py) -----------

def period_returns(prices: pd.Series) -> pd.Series:
    """Simple period returns from a price series: R_t = P_t / P_{t-1} - 1."""
    return prices.pct_change().dropna()


def compounded_return(returns: pd.Series) -> float:
    """Compounded return across periods: prod(1 + R_t) - 1."""
    if returns.empty:
        return 0.0
    return float(np.prod(1 + returns) - 1)


def sample_volatility(returns: pd.Series) -> float:
    """Sample standard deviation of returns (ddof=1)."""
    if len(returns) < 2:
        return 0.0
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


def wealth_index(returns: pd.Series, initial_wealth: float = 1.0) -> pd.Series:
    """Growth of one unit invested: WI_t = WI_{t-1}(1 + R_t)."""
    return initial_wealth * (1 + returns).cumprod()


def drawdown(wi: pd.Series) -> pd.Series:
    """Drawdown from running peak: WI_t / cummax(WI)_t - 1 (<= 0)."""
    return wi / wi.cummax() - 1


def max_drawdown(returns: pd.Series) -> float:
    """Worst peak-to-trough decline over the series."""
    if returns.empty:
        return 0.0
    return float(drawdown(wealth_index(returns)).min())


def analyze_prices(prices: pd.Series, interval: str = "1d", risk_free_rate: float = 0.0) -> dict:
    """Compute the full analytics bundle from a price series (returns keyed
    as: total_return, annualized_return, annualized_volatility, sharpe_ratio,
    max_drawdown, wealth_index, drawdown)."""
    if prices is None or len(prices) < 2:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "wealth_index": pd.Series(dtype="float64"),
            "drawdown": pd.Series(dtype="float64"),
        }

    ppy = periods_per_year(interval)
    rets = period_returns(prices)

    mean_period_return = float(rets.mean()) if not rets.empty else 0.0
    ann_return = annualize_return(mean_period_return, ppy)
    ann_vol = annualize_volatility(sample_volatility(rets), ppy)
    wi = wealth_index(rets)
    dd = drawdown(wi)

    return {
        "total_return": compounded_return(rets),
        "annualized_return": ann_return,
        "annualized_volatility": ann_vol,
        "sharpe_ratio": sharpe_ratio(ann_return, ann_vol, risk_free_rate),
        "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
        "wealth_index": wi,
        "drawdown": dd,
    }


def portfolio_wealth_index(price_series_by_symbol: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    """Combine each holding's price history into one value-weighted wealth curve.

    ``weights`` should be each holding's share of total market value (summing
    to ~1.0). Series are aligned on their shared dates (inner join) since
    holdings may have different available history.
    """
    frames = {
        symbol: series for symbol, series in price_series_by_symbol.items() if not series.empty and weights.get(symbol)
    }
    if not frames:
        return pd.Series(dtype="float64")

    returns = {symbol: period_returns(series) for symbol, series in frames.items()}
    returns_df = pd.DataFrame(returns).dropna(how="all").fillna(0.0)
    if returns_df.empty:
        return pd.Series(dtype="float64")

    total_weight = sum(weights.get(symbol, 0.0) for symbol in returns_df.columns)
    if total_weight <= 0:
        return pd.Series(dtype="float64")

    weighted_returns = sum(
        returns_df[symbol] * (weights.get(symbol, 0.0) / total_weight) for symbol in returns_df.columns
    )
    return wealth_index(weighted_returns)
