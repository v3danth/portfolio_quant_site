"""Single watchlist data-access helpers."""
from typing import Any, Optional

from app.database import execute, fetch_all, fetch_one
from app.models import stock as stock_model

_SELECT_WATCHLIST = """
    SELECT s.stock_id, s.symbol, s.short_name, s.sector,
           (SELECT p.`close` FROM stock_prices p
            WHERE p.stock_id = s.stock_id
            ORDER BY p.ts DESC LIMIT 1) AS current_price,
           (SELECT p.`close` FROM stock_prices p
            WHERE p.stock_id = s.stock_id
            ORDER BY p.ts DESC LIMIT 1 OFFSET 1) AS previous_close
    FROM watchlist w
    JOIN stocks s ON s.stock_id = w.stock_id
    ORDER BY s.symbol
"""

_SELECT_WATCHLIST_ITEM = """
    SELECT s.stock_id, s.symbol, s.short_name, s.sector,
           (SELECT p.`close` FROM stock_prices p
            WHERE p.stock_id = s.stock_id
            ORDER BY p.ts DESC LIMIT 1) AS current_price,
           (SELECT p.`close` FROM stock_prices p
            WHERE p.stock_id = s.stock_id
            ORDER BY p.ts DESC LIMIT 1 OFFSET 1) AS previous_close
    FROM watchlist w
    JOIN stocks s ON s.stock_id = w.stock_id
    WHERE s.stock_id = %s
"""

_INSERT_WATCHLIST_ITEM = """
    INSERT INTO watchlist (stock_id)
    VALUES (%s)
    ON DUPLICATE KEY UPDATE stock_id = VALUES(stock_id)
"""

_DELETE_WATCHLIST_ITEM = """
    DELETE FROM watchlist
    WHERE stock_id = %s
"""


def _with_day_change(row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    row["day_change"], row["day_change_pct"] = stock_model.compute_day_change(
        row.get("current_price"), row.get("previous_close")
    )
    return row


def get_watchlist_stocks() -> list[dict[str, Any]]:
    """Return the current watchlist with price and change metrics."""
    return [_with_day_change(row) for row in fetch_all(_SELECT_WATCHLIST, ())]


def get_watchlist_item(stock_id: int) -> Optional[dict[str, Any]]:
    """Return a single watchlist row for the provided stock ID."""
    return _with_day_change(fetch_one(_SELECT_WATCHLIST_ITEM, (stock_id,)))


def add_to_watchlist(stock_id: int) -> bool:
    """Add a stock to the global watchlist. Returns True when inserted or already present."""
    execute(_INSERT_WATCHLIST_ITEM, (stock_id,))
    return True


def remove_from_watchlist(stock_id: int) -> bool:
    """Remove a stock from the watchlist. Returns True if a row was deleted."""
    return execute(_DELETE_WATCHLIST_ITEM, (stock_id,)) > 0
