import time
from functools import wraps
import logging

import pandas as pd
import yfinance as yf

from db_operations import upsert_stock, clean_decimal, clean_int

logging.getLogger('yfinance').setLevel(logging.WARNING)


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
                        logging.warning(f"Rate limited ({error_type}). Attempt {attempt + 1}/{max_retries}. Waiting {delay}s before retry...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise
            return None
        return wrapper
    return decorator


def fetch_ticker(symbol):
    """Fetch one Yahoo Finance ticker."""
    return yf.Ticker(symbol.upper())


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
    logging.info("Fetching %s", symbol)
    time.sleep(2)
    try:
        ticker = fetch_ticker(symbol)
        try:
            info = get_ticker_info(ticker)
        except Exception as e:
            logging.warning("Failed to get info for %s: %s", symbol, e)
            info = {}
        stock_id = upsert_stock(connection, symbol, info)
        time.sleep(3)
        logging.info("Downloading history for %s (period=%s, interval=%s)", symbol, period, interval)
        try:
            history = ticker.history(period=period, interval=interval, actions=True, auto_adjust=False)
        except Exception as e:
            logging.error("Failed to download history for %s: %s", symbol, e)
            return symbol.upper(), 0
        if history.empty:
            logging.warning("%s returned no data", symbol)
            return symbol.upper(), 0
        result = symbol.upper(), upsert_prices(connection, stock_id, history, interval)
        del ticker
        return result
    except Exception as e:
        logging.error("Fatal error loading %s: %s", symbol, e)
        return symbol.upper(), 0