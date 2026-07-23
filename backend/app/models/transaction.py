"""Transaction SQL queries / data-access functions."""
from typing import Any, Optional

from app.database import fetch_all

# --- SQL statements -------------------------------------------------------

_SELECT_TRANSACTIONS_BASE = """
    SELECT trans_id, portfolio_id, stock_id, trans_type, quantity, price,
           amount, trans_details, ts
    FROM transactions
    WHERE portfolio_id = %s
"""


# --- Data-access functions ------------------------------------------------

def get_transactions(
    portfolio_id: int,
    trans_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return a portfolio's transactions (newest first), optionally filtered."""
    query = _SELECT_TRANSACTIONS_BASE
    params: list[Any] = [portfolio_id]

    if trans_type:
        query += " AND trans_type = %s"
        params.append(trans_type)

    query += " ORDER BY ts DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return fetch_all(query, tuple(params))
