"""Common database operations for stock data."""
from decimal import Decimal
from datetime import datetime, timedelta
import pandas as pd


def upsert_stock(connection, symbol, info):
    """Upsert stock metadata into the database."""
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO stocks (
            symbol, exchange, quote_type, short_name, long_name, currency, country,
            sector, industry, website, business_summary, market_cap, shares_outstanding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            exchange = VALUES(exchange),
            quote_type = VALUES(quote_type),
            short_name = VALUES(short_name),
            long_name = VALUES(long_name),
            currency = VALUES(currency),
            country = VALUES(country),
            sector = VALUES(sector),
            industry = VALUES(industry),
            website = VALUES(website),
            business_summary = VALUES(business_summary),
            market_cap = VALUES(market_cap),
            shares_outstanding = VALUES(shares_outstanding)
        """,
        (
            symbol.upper(),
            info.get("exchange"),
            info.get("quoteType"),
            info.get("shortName"),
            info.get("longName"),
            info.get("currency"),
            info.get("country"),
            info.get("sector"),
            info.get("industry"),
            info.get("website"),
            info.get("longBusinessSummary"),
            info.get("marketCap"),
            info.get("sharesOutstanding"),
        ),
    )
    connection.commit()
    cursor.execute("SELECT stock_id FROM stocks WHERE symbol = %s", (symbol.upper(),))
    stock_id = cursor.fetchone()[0]
    cursor.close()
    return stock_id


def upsert_prices(connection, stock_id, prices, interval):
    """Upsert price history into the database.

    Args:
        connection: Database connection
        stock_id: Stock ID from stocks table
        prices: List of price tuples (ts, open, high, low, close, adj_close, volume, dividend, stock_split)
        interval: Price interval (e.g., "1d" for daily)
    """
    cursor = connection.cursor()
    rows = [
        (stock_id, ts, interval, open_p, high, low, close, adj_close, volume, dividend, split)
        for ts, open_p, high, low, close, adj_close, volume, dividend, split in prices
    ]
    cursor.executemany(
        """
        INSERT INTO stock_prices (
            stock_id, ts, `interval`, `open`, high, low, `close`, adj_close,
            volume, dividend, stock_split
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `open` = VALUES(`open`),
            high = VALUES(high),
            low = VALUES(low),
            `close` = VALUES(`close`),
            adj_close = VALUES(adj_close),
            volume = VALUES(volume),
            dividend = VALUES(dividend),
            stock_split = VALUES(stock_split)
        """,
        rows,
    )
    connection.commit()
    cursor.close()
    return len(rows)


def clean_decimal(value):
    """Convert numeric values for MySQL."""
    if pd.isna(value):
        return None
    return Decimal(str(value))


def clean_int(value):
    """Convert integer values for MySQL."""
    if pd.isna(value):
        return None
    return int(value)
