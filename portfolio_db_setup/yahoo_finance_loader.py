from decimal import Decimal
import time
from functools import wraps

import pandas as pd
import yfinance as yf
import requests

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})


def retry_with_backoff(max_retries=5, initial_delay=5):
    """Decorator to retry function with exponential backoff for rate limits."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    error_type = type(e).__name__
                    is_rate_limit = (
                        "429" in error_str or
                        "Too Many Requests" in error_str or
                        "JSONDecodeError" in error_type
                    )
                    if is_rate_limit and attempt < max_retries - 1:
                        print(f"Rate limited ({error_type}). Attempt {attempt + 1}/{max_retries}. Waiting {delay}s before retry...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise
            return None
        return wrapper
    return decorator


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


def fetch_ticker(symbol):
    """Fetch one Yahoo Finance ticker."""
    return yf.Ticker(symbol.upper(), session=session)


def get_ticker_info(ticker):
    """Get ticker info from fast_info."""
    info = ticker.fast_info
    return {
        'shortName': info.get('longName', ''),
        'longName': info.get('longName', ''),
        'currency': info.get('currency', ''),
        'marketCap': info.get('market_cap'),
        'quoteType': 'EQUITY',
    }


def upsert_stock(connection, symbol, info):
    """Upsert stock metadata."""
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


def normalize_history(history):
    """Prepare Yahoo Finance prices for insert."""
    prices = history.reset_index()
    date_column = "Datetime" if "Datetime" in prices.columns else "Date"
    prices[date_column] = pd.to_datetime(prices[date_column]).dt.tz_localize(None)
    return prices, date_column


def upsert_prices(connection, stock_id, history, interval):
    """Upsert price history."""
    prices, date_column = normalize_history(history)
    cursor = connection.cursor()
    rows = [
        (
            stock_id,
            row[date_column].to_pydatetime(),
            interval,
            clean_decimal(row["Open"]),
            clean_decimal(row["High"]),
            clean_decimal(row["Low"]),
            clean_decimal(row["Close"]),
            clean_decimal(row.get("Adj Close")),
            clean_int(row.get("Volume")),
            clean_decimal(row.get("Dividends")),
            clean_decimal(row.get("Stock Splits")),
        )
        for _, row in prices.iterrows()
        if not pd.isna(row["Open"]) and not pd.isna(row["High"]) and not pd.isna(row["Low"]) and not pd.isna(row["Close"])
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


def load_symbol(connection, symbol, period="1y", interval="1d"):
    """Load one symbol from Yahoo Finance."""
    time.sleep(3)
    ticker = fetch_ticker(symbol)
    try:
        info = get_ticker_info(ticker)
    except Exception as e:
        print(f"Warning: Failed to get info for {symbol}: {e}. Using empty info...")
        info = {}
    stock_id = upsert_stock(connection, symbol, info)
    time.sleep(3)
    history = ticker.history(period=period, interval=interval, actions=True, auto_adjust=False)
    if history.empty:
        return symbol.upper(), 0
    return symbol.upper(), upsert_prices(connection, stock_id, history, interval)