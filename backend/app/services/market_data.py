"""Live price lookups against Yahoo Finance, with a short in-memory cache."""
import logging
import time
from decimal import Decimal
from typing import Optional

import yfinance as yf

_CACHE_TTL_SECONDS = 20
_cache: dict[str, tuple[float, Decimal]] = {}


def fetch_live_quote(symbol: str) -> Optional[dict[str, Decimal | int]]:
    """Return today's live OHLCV quote for a symbol, or None if unavailable.

    Uses fast_info (one lightweight request per symbol); the fields already
    describe the current trading day, so they can be written straight into a
    daily candle in stock_prices.
    """
    try:
        fast_info = yf.Ticker(symbol.upper()).fast_info
        close = fast_info["last_price"]
        if close is None:
            return None
        volume = fast_info.get("last_volume") or fast_info.get("regular_market_volume") or 0
        return {
            "open": Decimal(str(fast_info.get("open") or close)),
            "high": Decimal(str(fast_info.get("day_high") or close)),
            "low": Decimal(str(fast_info.get("day_low") or close)),
            "close": Decimal(str(close)),
            "volume": int(volume),
        }
    except Exception as exc:
        logging.warning("Live quote fetch failed for %s: %s", symbol, exc)
        return None


def get_live_price(symbol: str) -> Optional[Decimal]:
    """Return the live last-traded price for symbol, or None if unavailable.

    Cached in-process for _CACHE_TTL_SECONDS so rapid successive buy/sell
    calls don't re-hit Yahoo (which rate-limits aggressively).
    """
    symbol = symbol.upper()
    now = time.monotonic()

    cached = _cache.get(symbol)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        # FastInfo.get(...) always returns None regardless of key; bracket
        # access is what actually resolves against the live quote.
        last_price = yf.Ticker(symbol).fast_info["last_price"]
    except Exception as exc:
        logging.warning("Live price fetch failed for %s: %s", symbol, exc)
        return None

    if last_price is None:
        return None

    price = Decimal(str(last_price))
    _cache[symbol] = (now, price)
    return price
