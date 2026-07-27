"""Live price lookups against Yahoo Finance, with a short in-memory cache."""
import logging
import time
from decimal import Decimal
from typing import Optional

import yfinance as yf

_CACHE_TTL_SECONDS = 20
_cache: dict[str, tuple[float, Decimal]] = {}


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
