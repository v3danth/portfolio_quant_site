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


# --- Portfolio valuation --------------------------------------------------

def holdings_timeline(
    trades: list[dict],
    index: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Reconstruct quantity held per stock at each timestamp in ``index``.

    ``trades`` are BUY/SELL rows (stock_id, trans_type, quantity, ts). For each
    stock the signed quantity deltas are accumulated over time, then sampled
    "as-of" each price timestamp (step function, forward-filled, 0 before the
    first trade).
    """
    if not trades or len(index) == 0:
        return pd.DataFrame(index=index)

    # Signed delta per (stock_id, ts): BUY adds, SELL subtracts.
    deltas: dict[int, dict[pd.Timestamp, float]] = {}
    for trade in trades:
        stock_id = trade["stock_id"]
        qty = float(trade["quantity"] or 0)
        if trade["trans_type"] == "SELL":
            qty = -qty
        ts = pd.Timestamp(trade["ts"])
        deltas.setdefault(stock_id, {}).setdefault(ts, 0.0)
        deltas[stock_id][ts] += qty

    columns: dict[int, pd.Series] = {}
    for stock_id, by_ts in deltas.items():
        cumulative = pd.Series(by_ts).sort_index().cumsum()
        # Sample the step function as-of each price timestamp.
        combined = cumulative.reindex(index.union(cumulative.index)).ffill()
        columns[stock_id] = combined.reindex(index).fillna(0.0)

    return pd.DataFrame(columns, index=index)


def portfolio_value_series(
    price_series_by_stock: dict[int, pd.Series],
    trades: list[dict],
) -> pd.Series:
    """Build the point-in-time portfolio value Series.

    Weights each stock's price on each date by the quantity actually held on
    that date (reconstructed from ``trades``), so historical performance
    reflects what was owned then — not today's basket. Dates where a currently
    held stock has no price are dropped to avoid discontinuities.
    """
    active = {
        stock_id: series
        for stock_id, series in price_series_by_stock.items()
        if series is not None and not series.empty
    }
    if not active or not trades:
        return pd.Series(dtype="float64", name="value")

    price_frame = pd.DataFrame(active).sort_index()
    qty_frame = holdings_timeline(trades, price_frame.index).reindex(
        columns=price_frame.columns, fill_value=0.0
    )

    # Contribution is 0 where nothing is held, regardless of price availability.
    held = qty_frame.ne(0)
    contributions = (qty_frame * price_frame).where(held, 0.0)

    # Drop dates where a held stock is missing a price (undefined value).
    undefined = (held & price_frame.isna()).any(axis=1)
    value = contributions.sum(axis=1, min_count=1)[~undefined]

    # Trim leading dates before the first purchase (value == 0 / NaN).
    value = value[value.fillna(0) != 0].dropna()
    value.name = "value"
    return value


def cash_flow_series(trades: list[dict], index: pd.DatetimeIndex) -> pd.Series:
    """Net capital invested into positions per date, aligned to ``index``.

    A BUY is a positive inflow into the invested portfolio (qty * price); a SELL
    is a negative outflow. Used to strip cash-flow effects out of returns so the
    result is a true time-weighted return (TWR).
    """
    flows = pd.Series(0.0, index=index)
    if not trades or len(index) == 0:
        return flows

    for trade in trades:
        qty = float(trade["quantity"] or 0)
        price = float(trade["price"] or 0)
        value = qty * price
        if trade["trans_type"] == "SELL":
            value = -value
        ts = pd.Timestamp(trade["ts"]).normalize()
        # Snap the flow onto the nearest index date at or after the trade.
        matches = index[index >= ts]
        target = matches[0] if len(matches) else index[-1]
        flows.loc[target] += value

    flows.name = "cash_flow"
    return flows


def time_weighted_returns(value: pd.Series, cash_flows: pd.Series) -> pd.Series:
    """GIPS-style time-weighted period returns, adjusted for cash flows.

    Uses the end-of-period flow convention:  r_t = (V_t - CF_t) / V_{t-1} - 1.
    Subtracting the day's net inflow removes the mechanical value jump a buy/sell
    creates, leaving only return driven by price movement.
    """
    if value is None or len(value) < 2:
        return pd.Series(dtype="float64")

    cf = cash_flows.reindex(value.index).fillna(0.0)
    prev = value.shift(1)
    rets = (value - cf) / prev - 1
    return rets.dropna()


# --- Money-weighted return (XIRR) ----------------------------------------

def xirr(dated_amounts: list[tuple], guess: float = 0.1) -> Optional[float]:
    """Money-weighted annual return (XIRR) for irregular dated cash flows.

    Args:
        dated_amounts: list of (date, amount) where investor outflows are
            negative (buys) and inflows are positive (sells + terminal value).

    Returns the annualised IRR, or None if it cannot be solved.
    """
    if len(dated_amounts) < 2:
        return None

    dates = [pd.Timestamp(d) for d, _ in dated_amounts]
    amounts = [float(a) for _, a in dated_amounts]
    if not (any(a > 0 for a in amounts) and any(a < 0 for a in amounts)):
        return None  # need at least one inflow and one outflow

    t0 = min(dates)
    years = [(d - t0).days / 365.0 for d in dates]

    def npv(rate: float) -> float:
        return sum(a / (1 + rate) ** y for a, y in zip(amounts, years))

    def dnpv(rate: float) -> float:
        return sum(-y * a / (1 + rate) ** (y + 1) for a, y in zip(amounts, years))

    result = _solve_newton(npv, dnpv, guess)
    if result is not None:
        return result
    return _solve_bisection(npv)


def _solve_newton(npv, dnpv, guess: float) -> Optional[float]:
    """Newton-Raphson root finder for the NPV function."""
    rate = guess
    for _ in range(100):
        df = dnpv(rate)
        if abs(df) < 1e-12:
            return None
        step = npv(rate) / df
        rate = max(rate - step, -0.9999999)
        if abs(step) < 1e-8:
            return float(rate)
    return None


def _solve_bisection(npv) -> Optional[float]:
    """Bracketing fallback root finder for the NPV function."""
    low, high = -0.9999, 10.0
    f_low = npv(low)
    if f_low * npv(high) > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-8:
            return float(mid)
        if f_low * f_mid < 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    return float((low + high) / 2)


def portfolio_xirr(trades: list[dict], final_value: float, final_date) -> Optional[float]:
    """XIRR from the trade ledger plus the terminal portfolio value.

    Buys are outflows (money in), sells are inflows (money out), and the ending
    market value is booked as a final inflow on ``final_date``.
    """
    flows: list[tuple] = []
    for trade in trades:
        qty = float(trade["quantity"] or 0)
        price = float(trade["price"] or 0)
        amount = qty * price
        # Investor perspective: BUY = cash out (negative), SELL = cash in.
        signed = -amount if trade["trans_type"] == "BUY" else amount
        flows.append((pd.Timestamp(trade["ts"]).normalize(), signed))

    if final_value:
        flows.append((pd.Timestamp(final_date).normalize(), float(final_value)))

    return xirr(flows)


# --- Aggregate ------------------------------------------------------------

def analyze_prices(
    prices: pd.Series,
    interval: str = "1d",
    risk_free_rate: float = 0.0,
    cash_flows: Optional[pd.Series] = None,
) -> dict:
    """Compute the full analytics bundle from a portfolio value series.

    When ``cash_flows`` is supplied, period returns are time-weighted (TWR):
    daily buy/sell inflows are removed so the return reflects price performance
    only — the GIPS-compliant approach used by institutional managers.

    Returns keys matching the PortfolioAnalytics schema.
    """
    empty = {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "annualized_volatility": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "wealth_index": [],
        "drawdown": [],
    }
    if prices is None or len(prices) < 2:
        return empty

    ppy = periods_per_year(interval)
    if cash_flows is not None:
        rets = time_weighted_returns(prices, cash_flows)
    else:
        rets = period_returns(prices)

    if rets.empty:
        return empty

    total = compounded_return(rets)
    # Annualise the geometric total so it is consistent with total_return.
    num_periods = len(rets)
    ann_return = (1 + total) ** (ppy / num_periods) - 1 if num_periods > 0 else 0.0
    ann_vol = annualize_volatility(sample_volatility(rets), ppy)
    wi = wealth_index(rets)
    dd = drawdown(wi)

    return {
        "total_return": total,
        "annualized_return": float(ann_return),
        "annualized_volatility": ann_vol,
        "sharpe_ratio": sharpe_ratio(ann_return, ann_vol, risk_free_rate),
        "max_drawdown": float(dd.min()),
        "wealth_index": wi.tolist(),
        "drawdown": dd.tolist(),
    }
