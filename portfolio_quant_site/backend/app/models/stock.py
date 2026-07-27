"""Stock SQL queries / data-access functions."""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

import pandas as pd
from app.database import fetch_all, fetch_df, fetch_one

# --- SQL statements -------------------------------------------------------

_LATEST_CLOSE_SUBQUERY = """
    (SELECT p.`close` FROM stock_prices p
     WHERE p.stock_id = s.stock_id
     ORDER BY p.ts DESC LIMIT 1) AS current_price
"""

_PREVIOUS_CLOSE_SUBQUERY = """
    (SELECT p.`close` FROM stock_prices p
     WHERE p.stock_id = s.stock_id
     ORDER BY p.ts DESC LIMIT 1 OFFSET 1) AS previous_close
"""

_SELECT_STOCKS_BASE = f"""
    SELECT s.stock_id, s.symbol, s.short_name, s.sector,
           {_LATEST_CLOSE_SUBQUERY},
           {_PREVIOUS_CLOSE_SUBQUERY}
    FROM stocks s
"""

_SELECT_STOCK_BY_ID = f"""
    SELECT s.stock_id, s.symbol, s.exchange, s.quote_type, s.short_name, s.long_name,
           s.currency, s.country, s.sector, s.industry, s.website, s.business_summary,
           s.market_cap, s.shares_outstanding, s.first_seen_at, s.updated_at,
           {_LATEST_CLOSE_SUBQUERY},
           {_PREVIOUS_CLOSE_SUBQUERY}
    FROM stocks s
    WHERE s.stock_id = %s
"""

_SELECT_STOCK_BY_SYMBOL = """
    SELECT stock_id, symbol, short_name
    FROM stocks
    WHERE symbol = %s
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

_INTERVAL_ALIASES = {
    "1w": "1wk",
}


def normalize_interval(interval: str) -> str:
    return _INTERVAL_ALIASES.get(interval, interval)


def normalize_chart_interval(interval: str) -> str:
    """Normalize a UI-facing chart interval into the supported buckets."""
    normalized = (interval or "1d").strip().lower()
    aliases = {
        "1day": "1d",
        "1days": "1d",
        "1d": "1d",
        "1week": "1w",
        "1weeks": "1w",
        "1wk": "1w",
        "1w": "1w",
        "1month": "1mo",
        "1months": "1mo",
        "1mo": "1mo",
        "1m": "1mo",
        "1year": "1y",
        "1years": "1y",
        "1yr": "1y",
        "1y": "1y",
    }
    return aliases.get(normalized, normalized)


def _bucket_timestamp(ts: Any, chart_interval: str) -> datetime:
    ts_value = pd.to_datetime(ts).to_pydatetime()
    if chart_interval == "1d":
        return ts_value.replace(hour=0, minute=0, second=0, microsecond=0)
    if chart_interval == "1w":
        start_of_week = ts_value - timedelta(days=ts_value.weekday())
        return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    if chart_interval == "1mo":
        return ts_value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if chart_interval == "1y":
        return ts_value.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return ts_value


def build_price_candles(rows: list[dict[str, Any]], interval: str, stock_id: int) -> list[dict[str, Any]]:
    """Aggregate raw price rows into chart candles using the requested bucket size."""
    chart_interval = normalize_chart_interval(interval)
    if chart_interval not in {"1d", "1w", "1mo", "1y"}:
        return [
            {
                "stock_id": stock_id,
                "open": Decimal(str(row.get("open", 0))),
                "high": Decimal(str(row.get("high", 0))),
                "low": Decimal(str(row.get("low", 0))),
                "close": Decimal(str(row.get("close", 0))),
            }
            for row in rows
        ]

    buckets: dict[datetime, list[dict[str, Any]]] = {}
    for row in rows:
        bucket_key = _bucket_timestamp(row.get("ts"), chart_interval)
        buckets.setdefault(bucket_key, []).append(row)

    candles: list[dict[str, Any]] = []
    for bucket_key, bucket_rows in sorted(buckets.items()):
        open_values = [Decimal(str(row.get("open", 0))) for row in bucket_rows if row.get("open") is not None]
        high_values = [Decimal(str(row.get("high", 0))) for row in bucket_rows if row.get("high") is not None]
        low_values = [Decimal(str(row.get("low", 0))) for row in bucket_rows if row.get("low") is not None]
        close_values = [Decimal(str(row.get("close", 0))) for row in bucket_rows if row.get("close") is not None]
        adj_close_values = [
            Decimal(str(row.get("adj_close", row.get("close", 0))))
            for row in bucket_rows
            if row.get("adj_close") is not None or row.get("close") is not None
        ]

        candles.append(
            {
                "stock_id": stock_id,
                "open": sum(open_values, Decimal("0")) / Decimal(len(open_values)) if open_values else Decimal("0"),
                "high": max(high_values) if high_values else Decimal("0"),
                "low": min(low_values) if low_values else Decimal("0"),
                "close": sum(close_values, Decimal("0")) / Decimal(len(close_values)) if close_values else Decimal("0"),
            }
        )
    return candles


def compute_day_change(current: Any, previous: Any) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """Return (day_change, day_change_pct), or (None, None) if unavailable."""
    if current is None or not previous:
        return None, None
    current = Decimal(current)
    previous = Decimal(previous)
    change = current - previous
    change_pct = (change / previous * 100).quantize(Decimal("0.01"))
    return change, change_pct


def _with_day_change(row: dict[str, Any]) -> dict[str, Any]:
    row["day_change"], row["day_change_pct"] = compute_day_change(
        row.get("current_price"), row.get("previous_close")
    )
    return row


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

    query += " ORDER BY stock_id LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return [_with_day_change(row) for row in fetch_all(query, tuple(params))]


def get_stock_by_id(stock_id: int) -> Optional[dict[str, Any]]:
    """Return full stock detail by id, or None."""
    row = fetch_one(_SELECT_STOCK_BY_ID, (stock_id,))
    return _with_day_change(row) if row else None


def get_stock_by_symbol(symbol: str) -> Optional[dict[str, Any]]:
    """Return a minimal stock row by symbol (case-insensitive), or None."""
    return fetch_one(_SELECT_STOCK_BY_SYMBOL, (symbol.upper(),))


def get_stock_prices(
    stock_id: int,
    interval: str = "1d",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return OHLC candles for a stock, aggregated into the requested chart interval."""
    query = _SELECT_PRICES.replace("WHERE stock_id = %s AND `interval` = %s", "WHERE stock_id = %s")
    params: list[Any] = [stock_id]

    if start is not None:
        query += " AND ts >= %s"
        params.append(start)
    if end is not None:
        query += " AND ts <= %s"
        params.append(end)

    query += " ORDER BY ts ASC"
    rows = fetch_all(query, tuple(params))
    candles = build_price_candles(rows, interval, stock_id)

    if offset:
        candles = candles[offset:]
    if limit is not None:
        candles = candles[:limit]
    return candles


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
    interval = normalize_interval(interval)
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
