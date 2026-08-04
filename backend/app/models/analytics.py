"""Portfolio-level performance analytics: P&L, TWR/XIRR, movers, benchmark data.

Builds on top of holdings/transactions/stock_prices to compute figures that
span the whole portfolio rather than a single stock.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

import pandas as pd
from app.database import fetch_all
from app.models import holding as holding_model
from app.models import stock as stock_model
from app.services import market_data

_SELECT_PORTFOLIO_TRADES = """
    SELECT stock_id, trans_type, quantity, price, amount, ts
    FROM transactions
    WHERE portfolio_id = %s AND trans_type IN ('BUY', 'SELL')
    ORDER BY ts ASC
"""


def _live_or_last_price(stock_id: int, symbol: str) -> Optional[Decimal]:
    live = market_data.get_live_price(symbol)
    if live is not None:
        return live
    quote = stock_model.get_latest_quote(stock_id)
    return Decimal(quote["price"]) if quote else None


# --- Per-holding & portfolio-level P&L --------------------------------------

def get_holdings_pnl(portfolio_id: int) -> list[dict[str, Any]]:
    """Per-holding cost basis, market value and unrealized P&L (abs + %)."""
    rows = holding_model.get_holdings(portfolio_id)
    result = []
    for row in rows:
        quantity = Decimal(row["quantity"])
        avg_buy_price = Decimal(row.get("avg_buy_price") or 0)
        price_live = _live_or_last_price(row["stock_id"], row["symbol"]) or Decimal(row.get("price_live") or 0)

        cost_basis = quantity * avg_buy_price
        market_value = quantity * price_live
        pnl = market_value - cost_basis
        pnl_pct = float(pnl / cost_basis) if cost_basis else 0.0

        result.append(
            {
                "stock_id": row["stock_id"],
                "symbol": row["symbol"],
                "short_name": row.get("short_name"),
                "quantity": quantity,
                "avg_buy_price": avg_buy_price,
                "price_live": price_live,
                "cost_basis": cost_basis,
                "market_value": market_value,
                "unrealized_pnl": pnl,
                "unrealized_pnl_pct": pnl_pct,
            }
        )
    return result


def get_portfolio_performance(portfolio_id: int) -> dict[str, Any]:
    """Aggregate value, cost basis, total P&L and day change for a portfolio."""
    holdings = get_holdings_pnl(portfolio_id)

    total_value = sum((h["market_value"] for h in holdings), Decimal("0"))
    total_cost = sum((h["cost_basis"] for h in holdings), Decimal("0"))
    total_pnl = total_value - total_cost
    total_pnl_pct = float(total_pnl / total_cost) if total_cost else 0.0

    day_change = Decimal("0")
    day_change_prev_value = Decimal("0")
    for row in holding_model.get_holdings(portfolio_id):
        stock = stock_model.get_stock_by_id(row["stock_id"])
        if stock is None or stock.get("previous_close") is None:
            continue
        prev_close = Decimal(stock["previous_close"])
        quantity = Decimal(row["quantity"])
        prev_value = quantity * prev_close
        day_change_prev_value += prev_value

    if day_change_prev_value:
        day_change = total_value - day_change_prev_value
        day_change_pct = float(day_change / day_change_prev_value)
    else:
        day_change_pct = 0.0

    return {
        "portfolio_id": portfolio_id,
        "total_market_value": total_value,
        "total_cost_basis": total_cost,
        "total_unrealized_pnl": total_pnl,
        "total_unrealized_pnl_pct": total_pnl_pct,
        "day_change": day_change,
        "day_change_pct": day_change_pct,
        "holdings_count": len(holdings),
    }


def get_top_movers(portfolio_id: int, limit: int = 5) -> dict[str, list[dict[str, Any]]]:
    """Best/worst performing holdings by unrealized P&L %."""
    holdings = get_holdings_pnl(portfolio_id)
    ranked = sorted(holdings, key=lambda h: h["unrealized_pnl_pct"], reverse=True)
    return {
        "top_gainers": ranked[:limit],
        "top_losers": list(reversed(ranked[-limit:])) if len(ranked) > limit else list(reversed(ranked)),
    }


# --- Cash flows / value history (for TWR, XIRR, benchmarking) --------------

def get_portfolio_cashflows(portfolio_id: int) -> list[tuple[date, float]]:
    """(date, signed amount) pairs for every BUY/SELL, oldest first.

    amount is already sign-correct in the transactions table: negative for
    BUY (cash out), positive for SELL (cash in).
    """
    rows = fetch_all(_SELECT_PORTFOLIO_TRADES, (portfolio_id,))
    return [(row["ts"].date() if isinstance(row["ts"], datetime) else row["ts"], float(row["amount"])) for row in rows]


def get_portfolio_value_history(portfolio_id: int, interval: str = "1d") -> pd.DataFrame:
    """Reconstruct daily portfolio market value and net external cash flow.

    Returns a DataFrame indexed by date with columns:
        value       - total market value of all holdings at that date's close
        cash_flow   - net BUY/SELL cash flow that date (negative = net buy,
                      i.e. a contribution into the invested position; positive
                      = net sell, i.e. a withdrawal)

    Value is approximated using daily closing prices (not intraday), which is
    the standard simplification when only end-of-day data is available.
    """
    trades = fetch_all(_SELECT_PORTFOLIO_TRADES, (portfolio_id,))
    if not trades:
        return pd.DataFrame(columns=["value", "cash_flow"])

    stock_ids = sorted({row["stock_id"] for row in trades})

    qty_frames = []
    for stock_id in stock_ids:
        stock_trades = [row for row in trades if row["stock_id"] == stock_id]
        signed_qty = pd.Series(
            {
                pd.Timestamp(row["ts"]).normalize(): (
                    Decimal(row["quantity"]) if row["trans_type"] == "BUY" else -Decimal(row["quantity"])
                )
                for row in stock_trades
            }
        ).astype(float)
        signed_qty = signed_qty.groupby(signed_qty.index).sum().sort_index()

        prices = stock_model.get_stock_prices_df(stock_id, interval=interval)
        if prices.empty:
            continue
        price_index = prices.index.normalize()
        close = prices["close"].astype(float)
        close.index = price_index

        qty_on_price_dates = signed_qty.reindex(close.index.union(signed_qty.index)).fillna(0).cumsum()
        qty_on_price_dates = qty_on_price_dates.reindex(close.index).ffill().fillna(0)

        qty_frames.append((qty_on_price_dates * close).rename(f"stock_{stock_id}"))

    if not qty_frames:
        return pd.DataFrame(columns=["value", "cash_flow"])

    value = pd.concat(qty_frames, axis=1).sort_index().ffill().fillna(0).sum(axis=1)

    cash_flow = pd.Series(
        {pd.Timestamp(row["ts"]).normalize(): float(row["amount"]) for row in trades}
    )
    cash_flow = cash_flow.groupby(cash_flow.index).sum().reindex(value.index).fillna(0.0)

    return pd.DataFrame({"value": value, "cash_flow": cash_flow})
