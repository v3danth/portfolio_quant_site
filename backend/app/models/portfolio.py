"""Portfolio SQL queries / data-access functions."""
from typing import Any, Optional

from app.database import execute, execute_transaction, fetch_all, fetch_one, insert

# --- SQL statements -------------------------------------------------------

_SELECT_PORTFOLIOS_BY_USER = """
    SELECT portfolio_id, user_id, name, created_at
    FROM portfolios
    WHERE user_id = %s
    ORDER BY portfolio_id
"""

_SELECT_PORTFOLIO_BY_ID = """
    SELECT portfolio_id, user_id, name, created_at
    FROM portfolios
    WHERE portfolio_id = %s
"""

_INSERT_PORTFOLIO = """
    INSERT INTO portfolios (user_id, name)
    VALUES (%s, %s)
"""

_DELETE_PORTFOLIO = """
    DELETE FROM portfolios
    WHERE portfolio_id = %s
"""

_SELECT_HOLDING_QUANTITIES = """
    SELECT stock_id, quantity
    FROM holdings
    WHERE portfolio_id = %s AND quantity > 0
"""

_DELETE_HOLDINGS_FOR_PORTFOLIO = """
    DELETE FROM holdings
    WHERE portfolio_id = %s
"""

_DELETE_TRANSACTIONS_FOR_PORTFOLIO = """
    DELETE FROM transactions
    WHERE portfolio_id = %s
"""


# --- Data-access functions ------------------------------------------------

def get_portfolios_by_user(user_id: int) -> list[dict[str, Any]]:
    """Return all portfolios for a user."""
    return fetch_all(_SELECT_PORTFOLIOS_BY_USER, (user_id,))


def get_portfolio_by_id(portfolio_id: int) -> Optional[dict[str, Any]]:
    """Return a single portfolio by id, or None."""
    return fetch_one(_SELECT_PORTFOLIO_BY_ID, (portfolio_id,))


def create_portfolio(user_id: int, name: str) -> dict[str, Any]:
    """Insert a portfolio and return the created row."""
    portfolio_id = insert(_INSERT_PORTFOLIO, (user_id, name))
    return get_portfolio_by_id(portfolio_id)


def delete_portfolio(portfolio_id: int) -> int:
    """Delete a portfolio and its dependent rows (holdings, transactions).

    Child rows must be removed first because ``holdings`` and ``transactions``
    both carry a foreign key to ``portfolios``. Everything runs in a single
    transaction so a failure leaves the portfolio intact.

    Returns the number of portfolio rows removed (0 if the portfolio did not
    exist).
    """
    rowcounts = execute_transaction(
        [
            (_DELETE_TRANSACTIONS_FOR_PORTFOLIO, (portfolio_id,)),
            (_DELETE_HOLDINGS_FOR_PORTFOLIO, (portfolio_id,)),
            (_DELETE_PORTFOLIO, (portfolio_id,)),
        ]
    )
    return rowcounts[-1] if rowcounts else 0


def get_holding_quantities(portfolio_id: int) -> list[dict[str, Any]]:
    """Return current (stock_id, quantity) pairs for valuation."""
    return fetch_all(_SELECT_HOLDING_QUANTITIES, (portfolio_id,))
