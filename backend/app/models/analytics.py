"""Analytics SQL queries / data-access functions."""
from decimal import Decimal
from typing import Any

import pandas as pd
from app.database import fetch_all, fetch_df
from app.models import holding as holding_model

# --- SQL statements -------------------------------------------------------

_SELECT_HOLDINGS_BY_STOCK = """
    SELECT h.portfolio_id, h.stock_id, s.symbol, s.short_name,
           h.quantity, h.avg_buy_price, h.updated_at,
           (SELECT p.`close` FROM stock_prices p
            WHERE p.stock_id = h.stock_id
            ORDER BY p.ts DESC LIMIT 1) AS price_live
    FROM holdings h
    JOIN stocks s ON s.stock_id = h.stock_id
    WHERE h.stock_id = %s
    ORDER BY h.portfolio_id
"""

_SELECT_TRANSACTIONS_ALL = """
    SELECT trans_id, portfolio_id, stock_id, trans_type, quantity, price, amount, ts
    FROM transactions
    WHERE portfolio_id = %s
    ORDER BY ts ASC, trans_id ASC
"""

_SELECT_TRANSACTIONS_BY_STOCK = """
    SELECT trans_id, portfolio_id, stock_id, trans_type, quantity, price, amount, ts
    FROM transactions
    WHERE stock_id = %s
    ORDER BY ts ASC, trans_id ASC
"""

_SELECT_ALLOCATION_ROWS = """
    SELECT h.stock_id, s.symbol, s.quote_type, s.sector
    FROM holdings h
    JOIN stocks s ON s.stock_id = h.stock_id
    WHERE h.portfolio_id = %s
    ORDER BY s.symbol
"""

_SELECT_PORTFOLIO_PRICES = """
    SELECT h.stock_id, p.ts, p.`close`, p.adj_close
    FROM holdings h
    JOIN stock_prices p ON p.stock_id = h.stock_id AND p.`interval` = %s
    WHERE h.portfolio_id = %s
    ORDER BY p.ts ASC
"""


# --- Data-access functions ------------------------------------------------

def get_portfolio_allocation_rows(portfolio_id: int) -> list[dict[str, Any]]:
    """Return each holding's stock quote_type and sector for allocation charts."""
    return fetch_all(_SELECT_ALLOCATION_ROWS, (portfolio_id,))

def get_holdings_by_stock(stock_id: int) -> list[dict[str, Any]]:
    """Return every holding of a stock across all portfolios, with last close."""
    rows = fetch_all(_SELECT_HOLDINGS_BY_STOCK, (stock_id,))
    for row in rows:
        quantity, price = row.get("quantity"), row.get("price_live")
        row["market_value"] = (
            Decimal(quantity) * Decimal(price)
            if quantity is not None and price is not None
            else None
        )
    return rows


def get_portfolio_holdings(portfolio_id: int) -> list[dict[str, Any]]:
    """Return a portfolio's current holdings (delegates to the holding model)."""
    return holding_model.get_holdings(portfolio_id)


def get_transactions_all(portfolio_id: int) -> list[dict[str, Any]]:
    """Return a portfolio's full transaction history, oldest first."""
    return fetch_all(_SELECT_TRANSACTIONS_ALL, (portfolio_id,))


def get_transactions_by_stock(stock_id: int) -> list[dict[str, Any]]:
    """Return every transaction for a stock across all portfolios, oldest first."""
    return fetch_all(_SELECT_TRANSACTIONS_BY_STOCK, (stock_id,))


def get_portfolio_price_frames(
    portfolio_id: int,
    interval: str = "1d",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (adj_close, close) daily frames pivoted to (ts, stock_id) columns.

    Columns are the portfolio's current stock_ids. adj_close is backfilled with
    the raw close wherever it is missing.
    """
    df = fetch_df(_SELECT_PORTFOLIO_PRICES, (interval, portfolio_id))
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    adj = df.pivot(index="ts", columns="stock_id", values="adj_close")
    closes = df.pivot(index="ts", columns="stock_id", values="close")
    adj.index = pd.to_datetime(adj.index)
    closes.index = pd.to_datetime(closes.index)
    adj = adj.fillna(closes)
    return adj, closes
