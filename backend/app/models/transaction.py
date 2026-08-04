"""Transaction SQL queries / data-access functions."""
from calendar import monthrange
from datetime import date, timedelta
from typing import Any, Optional

from app.database import fetch_all

# --- SQL statements -------------------------------------------------------

_SELECT_TRANSACTIONS_BASE = """
    SELECT trans_id, portfolio_id, stock_id, trans_type, quantity, price,
           amount, trans_details, ts
    FROM transactions
    WHERE portfolio_id = %s
"""


# --- Date and range helpers ----------------------------------------------

def resolve_time_range(range_name: Optional[str], as_of: Optional[date] = None) -> tuple[Optional[date], Optional[date]]:
    """Translate a common bank-style time range into inclusive start/end dates."""
    as_of = as_of or date.today()

    if range_name in {None, "", "all", "custom"}:
        return None, None

    if range_name == "last_week":
        return as_of - timedelta(days=7), as_of
    if range_name == "last_month":
        return _shift_months(as_of, -1), as_of
    if range_name == "last_6_months":
        return _shift_months(as_of, -6), as_of
    if range_name == "last_1_year":
        return _shift_months(as_of, -12), as_of
    if range_name == "last_5_years":
        return _shift_months(as_of, -60), as_of

    return None, None


def _shift_months(base_date: date, months: int) -> date:
    month_index = base_date.month - 1 + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(base_date.day, monthrange(year, month)[1])
    return date(year, month, day)


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

    return fetch_all(query, params)


def get_transactions_in_period(
    portfolio_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    trans_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return transactions for a portfolio within an inclusive date window."""
    query = _SELECT_TRANSACTIONS_BASE
    params: list[Any] = [portfolio_id]

    if trans_type:
        query += " AND trans_type = %s"
        params.append(trans_type)

    if start_date is not None and end_date is not None:
        query += " AND ts BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    elif start_date is not None:
        query += " AND ts >= %s"
        params.append(start_date)
    elif end_date is not None:
        query += " AND ts <= %s"
        params.append(end_date)

    query += " ORDER BY ts DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return fetch_all(query, params)
