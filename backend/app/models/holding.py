"""Holdings & transactions SQL queries / data-access functions.

Buy and sell are multi-statement operations (holding + transaction + user cash
balance) and are executed atomically within a single DB transaction.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from app.database import fetch_all, fetch_one, get_cursor

# --- SQL statements -------------------------------------------------------

_SELECT_HOLDINGS = """
    SELECT h.portfolio_id, h.stock_id, s.symbol, s.short_name,
           h.quantity, h.avg_buy_price, h.is_position, h.position_expires_at, h.updated_at,
           (SELECT p.`close` FROM stock_prices p
            WHERE p.stock_id = h.stock_id
            ORDER BY p.ts DESC LIMIT 1) AS price_live
    FROM holdings h
    JOIN stocks s ON s.stock_id = h.stock_id
    WHERE h.portfolio_id = %s
    ORDER BY s.symbol
"""

_SELECT_HOLDING = """
    SELECT portfolio_id, stock_id, quantity, avg_buy_price
    FROM holdings
    WHERE portfolio_id = %s AND stock_id = %s
"""

_SELECT_HOLDING_VIEW = """
    SELECT h.portfolio_id, h.stock_id, s.symbol, s.short_name,
           h.quantity, h.avg_buy_price, h.is_position, h.position_expires_at, h.updated_at,
           (SELECT p.`close` FROM stock_prices p
            WHERE p.stock_id = h.stock_id
            ORDER BY p.ts DESC LIMIT 1) AS price_live
    FROM holdings h
    JOIN stocks s ON s.stock_id = h.stock_id
    WHERE h.portfolio_id = %s AND h.stock_id = %s
"""

_UPSERT_HOLDING = """
    INSERT INTO holdings (portfolio_id, stock_id, quantity, avg_buy_price, is_position, position_expires_at)
    VALUES (%s, %s, %s, %s, TRUE, DATE_ADD(NOW(), INTERVAL 1 MINUTE))
    ON DUPLICATE KEY UPDATE
        quantity = VALUES(quantity),
        avg_buy_price = VALUES(avg_buy_price),
        is_position = TRUE,
        position_expires_at = VALUES(position_expires_at)
"""

_UPDATE_HOLDING_QTY = """
    UPDATE holdings SET quantity = %s,
                        is_position = TRUE,
                        position_expires_at = DATE_ADD(NOW(), INTERVAL 1 MINUTE)
    WHERE portfolio_id = %s AND stock_id = %s
"""

_DELETE_HOLDING = """
    DELETE FROM holdings
    WHERE portfolio_id = %s AND stock_id = %s
"""

_INSERT_TRANSACTION = """
    INSERT INTO transactions
        (portfolio_id, stock_id, trans_type, quantity, price, amount, trans_details)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

_SELECT_TRANSACTION = """
    SELECT trans_id, portfolio_id, stock_id, trans_type, quantity, price,
           amount, trans_details, ts
    FROM transactions
    WHERE trans_id = %s
"""

_UPDATE_USER_BALANCE = """
    UPDATE users u
    JOIN portfolios p ON p.user_id = u.user_id
    SET u.acct_balance = u.acct_balance + %s
    WHERE p.portfolio_id = %s
"""

_SELECT_USER_BALANCE = """
    SELECT u.user_id, u.acct_balance
    FROM users u
    JOIN portfolios p ON p.user_id = u.user_id
    WHERE p.portfolio_id = %s
"""


class InsufficientFundsError(Exception):
    """Raised when the user cannot afford a purchase."""


class InsufficientQuantityError(Exception):
    """Raised when selling more than is held."""


# --- Read functions -------------------------------------------------------

def _position_is_active(row: dict[str, Any]) -> bool:
    expires_at = row.get("position_expires_at")
    if not row.get("is_position") or expires_at is None:
        return False
    now = datetime.now() if expires_at.tzinfo is None else datetime.now(expires_at.tzinfo)
    return expires_at > now


def _normalize_holding_row(row: dict[str, Any]) -> dict[str, Any]:
    if row is None:
        return row
    row["is_position"] = _position_is_active(row)
    row["market_value"] = _market_value(row.get("quantity"), row.get("price_live"))
    return row


def get_holdings(portfolio_id: int) -> list[dict[str, Any]]:
    """Return current positions for a portfolio, with live value."""
    rows = fetch_all(_SELECT_HOLDINGS, (portfolio_id,))
    return [_normalize_holding_row(row) for row in rows]


def get_holding(portfolio_id: int, stock_id: int) -> Optional[dict[str, Any]]:
    """Return a single enriched holding, or None."""
    row = fetch_one(_SELECT_HOLDING_VIEW, (portfolio_id, stock_id))
    return _normalize_holding_row(row)


# --- Write functions (atomic) --------------------------------------------

def buy_stock(portfolio_id: int, stock_id: int, quantity: Decimal, price: Decimal) -> dict[str, Any]:
    """Buy a stock: debit cash, upsert holding (weighted avg), record BUY.

    Raises:
        InsufficientFundsError: if the user's balance is too low.
    """
    amount = Decimal(quantity) * Decimal(price)

    with get_cursor(commit=True) as cursor:
        # 1. Check funds.
        cursor.execute(_SELECT_USER_BALANCE, (portfolio_id,))
        user = cursor.fetchone()
        if user is None:
            raise ValueError("Portfolio has no associated user")
        if Decimal(user["acct_balance"]) < amount:
            raise InsufficientFundsError(
                f"Balance {user['acct_balance']} is insufficient for purchase of {amount}"
            )

        # 2. Compute new quantity / weighted-average buy price.
        cursor.execute(_SELECT_HOLDING, (portfolio_id, stock_id))
        existing = cursor.fetchone()
        if existing:
            old_qty = Decimal(existing["quantity"])
            old_avg = Decimal(existing["avg_buy_price"] or 0)
            new_qty = old_qty + Decimal(quantity)
            new_avg = (old_qty * old_avg + Decimal(quantity) * Decimal(price)) / new_qty
        else:
            new_qty = Decimal(quantity)
            new_avg = Decimal(price)

        cursor.execute(_UPSERT_HOLDING, (portfolio_id, stock_id, new_qty, new_avg))

        # 3. Record the transaction (negative cash impact).
        cursor.execute(
            _INSERT_TRANSACTION,
            (portfolio_id, stock_id, "BUY", quantity, price, -amount, "Buy order"),
        )

        # 4. Debit the user's cash balance.
        cursor.execute(_UPDATE_USER_BALANCE, (-amount, portfolio_id))

    return get_holding(portfolio_id, stock_id)


def sell_stock(
    portfolio_id: int,
    stock_id: int,
    price: Decimal,
    quantity: Optional[Decimal] = None,
) -> dict[str, Any]:
    """Sell a stock: credit cash, reduce/remove holding, record SELL.

    Args:
        quantity: amount to sell; if None the whole position is sold.

    Returns:
        The created SELL transaction row.

    Raises:
        InsufficientQuantityError: if selling more than is held.
    """
    with get_cursor(commit=True) as cursor:
        cursor.execute(_SELECT_HOLDING, (portfolio_id, stock_id))
        existing = cursor.fetchone()
        if existing is None:
            raise InsufficientQuantityError("No holding for this stock in the portfolio")

        held_qty = Decimal(existing["quantity"])
        sell_qty = held_qty if quantity is None else Decimal(quantity)

        if sell_qty <= 0:
            raise ValueError("Sell quantity must be positive")
        if sell_qty > held_qty:
            raise InsufficientQuantityError(
                f"Cannot sell {sell_qty}; only {held_qty} held"
            )

        amount = sell_qty * Decimal(price)
        remaining = held_qty - sell_qty

        # 1. Reduce or remove the holding.
        if remaining == 0:
            cursor.execute(_DELETE_HOLDING, (portfolio_id, stock_id))
        else:
            cursor.execute(_UPDATE_HOLDING_QTY, (remaining, portfolio_id, stock_id))

        # 2. Record the transaction (positive cash impact).
        cursor.execute(
            _INSERT_TRANSACTION,
            (portfolio_id, stock_id, "SELL", sell_qty, price, amount, "Sell order"),
        )
        trans_id = cursor.lastrowid

        # 3. Credit the user's cash balance.
        cursor.execute(_UPDATE_USER_BALANCE, (amount, portfolio_id))

        cursor.execute(_SELECT_TRANSACTION, (trans_id,))
        return cursor.fetchone()


# --- Helpers --------------------------------------------------------------

def _market_value(quantity: Any, price_live: Any) -> Optional[Decimal]:
    """Compute quantity * live price, or None if price is unavailable."""
    if quantity is None or price_live is None:
        return None
    return Decimal(quantity) * Decimal(price_live)
