"""Profit & loss analytics.

Pure-Decimal, side-effect-free computation. Weighted-average cost accounting is
used so realized P&L stays consistent with how app/models/holding.py maintains
holdings.avg_buy_price:

  - BUY  updates the running average cost: avg' = (qty * avg + q * price) / (qty + q)
  - SELL realizes (price - avg) * qty and leaves the average cost unchanged
"""
from decimal import Decimal
from typing import Any, Optional

import pandas as pd

_ZERO = Decimal("0")
_PERIODS_PER_YEAR = 252


def _dec(value: Any) -> Decimal:
    """Coerce a DB value to Decimal, defaulting to zero for None."""
    if value is None:
        return _ZERO
    return Decimal(str(value))


def unrealized_pnl(
    quantity: Any,
    avg_buy_price: Any,
    current_price: Any,
) -> tuple[Optional[Decimal], Optional[float]]:
    """Unrealized P&L: (price - avg) * quantity, plus a percentage of cost basis.

    Returns (None, None) when any input is missing; the percentage is None when
    the cost basis is zero.
    """
    if quantity is None or avg_buy_price is None or current_price is None:
        return None, None

    qty = _dec(quantity)
    avg = _dec(avg_buy_price)
    price = _dec(current_price)
    cost_basis = qty * avg
    pnl = (price - avg) * qty
    pnl_pct = float(pnl / cost_basis) if cost_basis else None
    return pnl, pnl_pct


def realized_pnl_by_position(transactions: list[dict[str, Any]]) -> dict[tuple[int, int], Decimal]:
    """Weighted-average cost simulation over chronologically ordered transactions.

    Args:
        transactions: rows from the transactions table ordered by ts ascending,
            each with portfolio_id, stock_id, trans_type, quantity and price.

    Returns:
        Mapping {(portfolio_id, stock_id): realized_pnl}. Non BUY/SELL rows are
        ignored; each portfolio's position is tracked independently.
    """
    state: dict[tuple[int, int], list[Decimal]] = {}
    realized: dict[tuple[int, int], Decimal] = {}

    for txn in transactions:
        trans_type = (txn.get("trans_type") or "").upper()
        if trans_type not in ("BUY", "SELL"):
            continue

        key = (int(txn["portfolio_id"]), int(txn["stock_id"]))
        qty = _dec(txn.get("quantity"))
        price = _dec(txn.get("price"))
        if qty <= 0 or price < 0:
            continue

        held_qty, avg_cost = state.get(key, [_ZERO, _ZERO])
        if trans_type == "BUY":
            new_qty = held_qty + qty
            new_avg = (held_qty * avg_cost + qty * price) / new_qty
            state[key] = [new_qty, new_avg]
        else:
            sell_qty = min(qty, held_qty)
            realized[key] = realized.get(key, _ZERO) + (price - avg_cost) * sell_qty
            state[key] = [held_qty - sell_qty, avg_cost]

    return realized


def invested_by_position(transactions: list[dict[str, Any]]) -> dict[tuple[int, int], Decimal]:
    """Total cash spent on BUY transactions per (portfolio_id, stock_id)."""
    invested: dict[tuple[int, int], Decimal] = {}
    for txn in transactions:
        if (txn.get("trans_type") or "").upper() != "BUY":
            continue
        key = (int(txn["portfolio_id"]), int(txn["stock_id"]))
        qty = _dec(txn.get("quantity"))
        price = _dec(txn.get("price"))
        if qty > 0 and price >= 0:
            invested[key] = invested.get(key, _ZERO) + qty * price
    return invested


def build_stock_pnl(
    stock_row: dict[str, Any],
    holdings: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate a single stock's P&L across every holding/portfolio.

    Args:
        stock_row: row from stock_model.get_stock_by_id (stock_id, symbol, short_name).
        holdings: all holdings of the stock, each with quantity, avg_buy_price,
            price_live and market_value.
        transactions: full transaction history for the stock, oldest first.
    """
    realized = realized_pnl_by_position(transactions)
    invested = invested_by_position(transactions)
    total_realized = sum(realized.values(), _ZERO)
    total_invested = sum(invested.values(), _ZERO)

    total_qty = sum(_dec(h.get("quantity")) for h in holdings)
    cost_basis = sum(_dec(h.get("quantity")) * _dec(h.get("avg_buy_price")) for h in holdings)
    priced = [h for h in holdings if h.get("price_live") is not None]
    market_value = sum(_dec(h.get("market_value")) for h in priced)

    unrealized = market_value - cost_basis if priced else None
    unrealized_pct = float(unrealized / cost_basis) if priced and cost_basis else None
    avg_buy_price = cost_basis / total_qty if total_qty else None

    total_pnl = unrealized + total_realized if unrealized is not None else None
    total_pnl_pct = (
        float(total_pnl / total_invested) if total_pnl is not None and total_invested else None
    )

    return {
        "stock_id": stock_row["stock_id"],
        "symbol": stock_row["symbol"],
        "short_name": stock_row.get("short_name"),
        "portfolio_id": None,
        "quantity": total_qty,
        "avg_buy_price": avg_buy_price,
        "current_price": _dec(priced[0].get("price_live")) if priced else None,
        "cost_basis": cost_basis,
        "market_value": market_value if priced else None,
        "unrealized_pnl": unrealized,
        "unrealized_pnl_pct": unrealized_pct,
        "realized_pnl": total_realized,
        "invested": total_invested,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
    }


def build_portfolio_pnl(
    portfolio_id: int,
    holdings: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Portfolio-wide P&L with a per-holding breakdown.

    Args:
        holdings: the portfolio's holdings, each with stock_id, symbol,
            short_name, quantity, avg_buy_price, price_live and market_value.
        transactions: full transaction history for the portfolio, oldest first.
    """
    realized_map = realized_pnl_by_position(transactions)
    invested_map = invested_by_position(transactions)

    stock_rows: list[dict[str, Any]] = []
    for holding in holdings:
        stock_id = int(holding["stock_id"])
        key = (portfolio_id, stock_id)
        qty = _dec(holding.get("quantity"))
        avg = _dec(holding.get("avg_buy_price"))
        price = holding.get("price_live")
        cost_basis = qty * avg
        market_value = _dec(holding.get("market_value")) if price is not None else None

        unrealized, unrealized_pct = unrealized_pnl(qty, avg, price)
        realized = realized_map.get(key, _ZERO)
        invested = invested_map.get(key, _ZERO)
        total_pnl = unrealized + realized if unrealized is not None else None
        total_pnl_pct = float(total_pnl / invested) if total_pnl is not None and invested else None

        stock_rows.append(
            {
                "stock_id": stock_id,
                "symbol": holding.get("symbol"),
                "short_name": holding.get("short_name"),
                "portfolio_id": portfolio_id,
                "quantity": qty,
                "avg_buy_price": avg,
                "current_price": price,
                "cost_basis": cost_basis,
                "market_value": market_value,
                "unrealized_pnl": unrealized,
                "unrealized_pnl_pct": unrealized_pct,
                "realized_pnl": realized,
                "invested": invested,
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
            }
        )

    if not stock_rows:
        return {
            "portfolio_id": portfolio_id,
            "holdings_count": 0,
            "total_cost_basis": _ZERO,
            "total_market_value": None,
            "total_unrealized_pnl": None,
            "total_unrealized_pnl_pct": None,
            "total_realized_pnl": _ZERO,
            "total_pnl": None,
            "total_pnl_pct": None,
            "total_invested": _ZERO,
            "holdings": [],
        }

    priced = [row for row in stock_rows if row["market_value"] is not None]
    total_cost_basis = sum(_dec(h.get("quantity")) * _dec(h.get("avg_buy_price")) for h in holdings)
    total_market_value = sum(row["market_value"] for row in priced)
    total_unrealized = sum(row["unrealized_pnl"] for row in priced)
    total_realized = sum(realized_map.values(), _ZERO)
    total_invested = sum(invested_map.values(), _ZERO)
    total_pnl = total_unrealized + total_realized if priced else None
    total_pnl_pct = float(total_pnl / total_invested) if total_pnl is not None and total_invested else None
    total_unrealized_pct = float(total_unrealized / total_cost_basis) if priced and total_cost_basis else None

    return {
        "portfolio_id": portfolio_id,
        "holdings_count": len(stock_rows),
        "total_cost_basis": total_cost_basis,
        "total_market_value": total_market_value if priced else None,
        "total_unrealized_pnl": total_unrealized if priced else None,
        "total_unrealized_pnl_pct": total_unrealized_pct,
        "total_realized_pnl": total_realized,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "total_invested": total_invested,
        "holdings": stock_rows,
    }


def select_performers(
    holdings_rows: list[dict[str, Any]],
    metric: str = "total_pnl_pct",
) -> dict[str, Any]:
    """Best and worst current holding by a P&L metric.

    Args:
        holdings_rows: per-holding P&L rows from build_portfolio_pnl.
        metric: the ranking field (e.g. total_pnl_pct); rows whose value is
            None (no price) are excluded from ranking.

    Returns:
        holdings_count, the metric used, and the top_performer / worst_performer
        holding rows (None when nothing can be ranked).
    """
    ranked = [row for row in holdings_rows if row.get(metric) is not None]
    top = max(ranked, key=lambda row: row[metric]) if ranked else None
    worst = min(ranked, key=lambda row: row[metric]) if ranked else None
    return {
        "holdings_count": len(holdings_rows),
        "metric": metric,
        "top_performer": top,
        "worst_performer": worst,
    }


def build_allocation(
    portfolio_id: int,
    rows: list[dict[str, Any]],
    grouping_key: str,
) -> dict[str, Any]:
    """Group holdings by a stock attribute (quote_type or sector) into counts.

    Args:
        rows: holdings joined with stocks, each containing grouping_key.
        grouping_key: the stocks column to group by, e.g. "quote_type" or "sector".

    Returns:
        Allocation payload: total_holdings, and per-group label, holdings_count
        and weight (count / total). Missing/empty group values fall back to
        "Unknown". Groups are ordered by count descending.
    """
    counts: dict[str, int] = {}
    for row in rows:
        label = row.get(grouping_key)
        if not label:
            label = "Unknown"
        counts[label] = counts.get(label, 0) + 1

    total = len(rows)
    groups = [
        {
            "label": label,
            "holdings_count": count,
            "weight": count / total if total else 0.0,
        }
        for label, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]

    return {
        "portfolio_id": portfolio_id,
        "grouping": grouping_key,
        "total_holdings": total,
        "groups": groups,
    }


def simple_returns(close: pd.Series) -> pd.Series:
    """Daily simple returns from a close series (price.pct_change(), NaN dropped)."""
    return close.pct_change().dropna()


def annualized_volatility(returns: pd.Series) -> Optional[float]:
    """Annualized sample volatility: std(ddof=1) * sqrt(252)."""
    if returns is None or returns.empty:
        return None
    return float(returns.std(ddof=1) * (_PERIODS_PER_YEAR ** 0.5))


def annualized_return(returns: pd.Series) -> Optional[float]:
    """Geometric annualized return: wealth_index ** (252 / n) - 1."""
    if returns is None or returns.empty:
        return None
    wealth = float((1 + returns).prod())
    return float(wealth ** (_PERIODS_PER_YEAR / len(returns)) - 1)


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> Optional[float]:
    """(annualized_return - risk_free_rate) / annualized_volatility."""
    if returns is None or returns.empty:
        return None
    ann_return = annualized_return(returns)
    ann_vol = annualized_volatility(returns)
    if ann_return is None or ann_vol is None or ann_vol == 0:
        return None
    return (ann_return - risk_free_rate) / ann_vol


def max_drawdown(returns: pd.Series) -> Optional[float]:
    """Largest peak-to-trough decline of the compounded wealth index."""
    if returns is None or returns.empty:
        return None
    wealth = (1 + returns).cumprod()
    drawdown = wealth / wealth.cummax() - 1
    return float(drawdown.min())


def historical_var(returns: pd.Series, level: float = 0.95) -> Optional[float]:
    """Historical Value-at-Risk at the given confidence level (a positive loss)."""
    if returns is None or returns.empty:
        return None
    return float(-returns.quantile(1 - level))


def beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> Optional[float]:
    """Cov(portfolio, benchmark) / Var(benchmark) on the common dates."""
    if portfolio_returns is None or benchmark_returns is None:
        return None
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return None
    benchmark_var = aligned.iloc[:, 1].var(ddof=1)
    if pd.isna(benchmark_var) or benchmark_var == 0:
        return None
    return float(aligned.iloc[:, 0].cov(aligned.iloc[:, 1]) / benchmark_var)


def _risk_metrics(
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    risk_free_rate: float = 0.0,
) -> dict[str, Any]:
    """The standard metric set for a single return series."""
    return {
        "annualized_return": annualized_return(returns),
        "annualized_volatility": annualized_volatility(returns),
        "sharpe_ratio": sharpe_ratio(returns, risk_free_rate),
        "max_drawdown": max_drawdown(returns),
        "value_at_risk_95": historical_var(returns, 0.95),
        "value_at_risk_99": historical_var(returns, 0.99),
        "beta": beta(returns, benchmark_returns) if benchmark_returns is not None else None,
    }


def build_portfolio_risk(
    portfolio_id: int,
    holdings: list[dict[str, Any]],
    adj_closes: pd.DataFrame,
    closes: pd.DataFrame,
    benchmark_close: Optional[pd.Series] = None,
    benchmark_symbol: Optional[str] = None,
    lookback_days: int = 252,
    risk_free_rate: float = 0.0,
) -> dict[str, Any]:
    """Risk metrics for a portfolio's current holdings, weighted by market value.

    Each holding's weight is its share of total market value using the last
    daily close in the window. Portfolio daily returns are the weighted sum of
    the holdings' adjusted-close daily returns, aligned on a common date index
    and truncated to the most recent ``lookback_days`` observations. Formulas
    follow docs/MATH_SPECS.md.

    Args:
        holdings: current holdings (stock_id, quantity); only those present in
            the price frames contribute to the weights.
        adj_closes: adjusted-close frame (index ts, columns stock_id).
        closes: raw-close frame (index ts, columns stock_id).
        benchmark_close: benchmark close series for beta / comparison metrics.
    """
    prices = {int(h["stock_id"]) for h in holdings}
    available = [col for col in adj_closes.columns if col in prices]
    if not available:
        return _empty_portfolio_risk(portfolio_id, benchmark_symbol, risk_free_rate)

    window = adj_closes[available].ffill().dropna(how="all").astype(float)
    if window.empty:
        return _empty_portfolio_risk(portfolio_id, benchmark_symbol, risk_free_rate)
    window = window.iloc[-lookback_days:]

    last_row = window.iloc[-1]
    raw_last = closes[available].reindex(window.index).ffill().iloc[-1].astype(float)
    prices_at_end = raw_last.where(raw_last.notna(), last_row)
    quantity_by_stock = {int(h["stock_id"]): Decimal(str(h.get("quantity") or 0)) for h in holdings}
    market_values = prices_at_end * pd.Series(
        {stock_id: float(quantity_by_stock[stock_id]) for stock_id in available}
    )
    total_value = float(market_values.sum())
    if total_value <= 0:
        return _empty_portfolio_risk(portfolio_id, benchmark_symbol, risk_free_rate)
    weights = market_values / total_value

    daily = window.pct_change().dropna()
    portfolio_returns = daily.mul(weights, axis=1).sum(axis=1)

    benchmark_returns = None
    benchmark_metrics = None
    if benchmark_close is not None and not benchmark_close.empty:
        benchmark_returns = (
            benchmark_close.reindex(portfolio_returns.index).astype(float).pct_change().dropna()
        )
        if not benchmark_returns.empty:
            benchmark_metrics = _risk_metrics(benchmark_returns, None, risk_free_rate)

    return {
        "portfolio_id": portfolio_id,
        "weights_count": len(available),
        "observations": len(portfolio_returns),
        "window_start": window.index[0],
        "window_end": window.index[-1],
        "risk_free_rate": risk_free_rate,
        "benchmark": benchmark_symbol,
        "metrics": _risk_metrics(portfolio_returns, benchmark_returns, risk_free_rate),
        "benchmark_metrics": benchmark_metrics,
    }


def _empty_portfolio_risk(
    portfolio_id: int,
    benchmark_symbol: Optional[str],
    risk_free_rate: float,
) -> dict[str, Any]:
    """Risk payload for a portfolio with no priceable holdings (all metrics null)."""
    return {
        "portfolio_id": portfolio_id,
        "weights_count": 0,
        "observations": 0,
        "window_start": None,
        "window_end": None,
        "risk_free_rate": risk_free_rate,
        "benchmark": benchmark_symbol,
        "metrics": {
            "annualized_return": None,
            "annualized_volatility": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "value_at_risk_95": None,
            "value_at_risk_99": None,
            "beta": None,
        },
        "benchmark_metrics": None,
    }
