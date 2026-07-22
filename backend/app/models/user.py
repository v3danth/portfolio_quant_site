"""User SQL queries / data-access functions."""
from typing import Any, Optional

from app.database import fetch_all, fetch_one

# --- SQL statements -------------------------------------------------------

_SELECT_USER_BY_ID = """
    SELECT user_id, user_name, email, acct_balance, created_at
    FROM users
    WHERE user_id = %s
"""

_SELECT_ALL_USERS = """
    SELECT user_id, user_name, email, acct_balance, created_at
    FROM users
    ORDER BY user_id
"""


# --- Data-access functions ------------------------------------------------

def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    """Return a single user row by id, or None if not found."""
    return fetch_one(_SELECT_USER_BY_ID, (user_id,))


def get_all_users() -> list[dict[str, Any]]:
    """Return all users."""
    return fetch_all(_SELECT_ALL_USERS)
