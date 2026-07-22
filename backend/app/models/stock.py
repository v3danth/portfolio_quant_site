"""Stock SQL queries / data-access functions."""
from datetime import datetime
from typing import Any, Optional

import pandas as pd
from app.database import fetch_all, fetch_df, fetch_one

# --- SQL statements -------------------------------------------------------

_SELECT_STOCKS_BASE = """
    SELECT stock_id, symbol, short_name, sector
    FROM stocks
"""

_SELECT_STOCK_BY_ID = """
    SELECT stock_id, symbol, exchange, quote_type, short_name, long_name,
           currency, country, sector, industry, website, business_summary,
           market_cap, shares_outstanding, first_seen_at, updated_at
    FROM stocks
    WHERE stock_id = %s
"""

_SELECT_PRICES = """
    SELECT ts, `interval`, `open`, high, low, `close`, adj_close,
           volume, dividend, stock_split
    FROM stock_prices
    WHERE stock_id = %s AND `interval` = %s
"""

_SELECT_LATEST_QUOTE = """
    SELECT s.stock_id, s.symbol, p.`close` AS price, p.ts
    FROM stock_prices p
    JOIN stocks s ON s.stock_id = p.stock_id
    WHERE p.stock_id = %s
    ORDER BY p.ts DESC
    LIMIT 1
"""


# --- Data-access functions ------------------------------------------------

def get_stocks(
    search: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return a filtered, paged list of stocks."""
    query = _SELECT_STOCKS_BASE
    conditions: list[str] = []
    params: list[Any] = []

    if search:
        conditions.append("(symbol LIKE %s OR short_name LIKE %s OR long_name LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if sector:
        conditions.append("sector = %s")
        params.append(sector)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY symbol LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return fetch_all(query, tuple(params))


def get_stock_by_id(stock_id: int) -> Optional[dict[str, Any]]:
    """Return full stock detail by id, or None."""
    return fetch_one(_SELECT_STOCK_BY_ID, (stock_id,))


def get_stock_prices(
    stock_id: int,
    interval: str = "1d",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Return OHLC candles for a stock, optionally bounded by a time frame."""
    query = _SELECT_PRICES
    params: list[Any] = [stock_id, interval]

    if start is not None:
        query += " AND ts >= %s"
        params.append(start)
    if end is not None:
        query += " AND ts <= %s"
        params.append(end)

    query += " ORDER BY ts ASC"
    return fetch_all(query, tuple(params))


def get_stock_prices_df(
    stock_id: int,
    interval: str = "1d",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """Return OHLC candles as a time-indexed DataFrame ready for math.

    The frame is indexed by ``ts`` and numeric columns are cast to float so
    that returns, volatility, Sharpe ratio and drawdown can be computed
    directly (see docs/MATH_SPECS.md).
    """
    query = _SELECT_PRICES
    params: list[Any] = [stock_id, interval]

    if start is not None:
        query += " AND ts >= %s"
        params.append(start)
    if end is not None:
        query += " AND ts <= %s"
        params.append(end)

    query += " ORDER BY ts ASC"
    df = fetch_df(query, tuple(params), index="ts")

    if df.empty:
        return df

    df.index = pd.to_datetime(df.index)
    numeric_cols = ["open", "high", "low", "close", "adj_close", "volume", "dividend", "stock_split"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_close_series(
    stock_id: int,
    interval: str = "1d",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.Series:
    """Return the (adjusted) close price as a time-indexed pandas Series.

    Prefers ``adj_close`` when available, falling back to ``close``. Ideal for
    computing period returns via ``series.pct_change()``.
    """
    df = get_stock_prices_df(stock_id, interval=interval, start=start, end=end)
    if df.empty:
        return pd.Series(dtype="float64", name="price")

    price = df["adj_close"].fillna(df["close"]) if "adj_close" in df.columns else df["close"]
    price.name = "price"
    return price


def get_latest_quote(stock_id: int) -> Optional[dict[str, Any]]:
    """Return the most recent price row as a quote, or None."""
    return fetch_one(_SELECT_LATEST_QUOTE, (stock_id,))
