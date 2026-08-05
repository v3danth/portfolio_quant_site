"""Alert SQL queries / data-access functions."""
from typing import Any, Optional

from app.database import execute, fetch_all, fetch_one, insert

# --- SQL statements -------------------------------------------------------

_INSERT_ALERT = """
    INSERT INTO alerts (portfolio_id, user_id, category, severity, metric,
                        observed_value, threshold, message)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

_SELECT_ALERTS = """
    SELECT alert_id, portfolio_id, user_id, category, severity, metric,
           observed_value, threshold, message, is_read, created_at
    FROM alerts
    WHERE user_id = %s
    AND (%s IS NULL OR portfolio_id = %s)
    AND (%s = FALSE OR is_read = FALSE)
    ORDER BY created_at DESC, alert_id DESC
    LIMIT %s
"""

_SELECT_UNREAD_COUNT = """
    SELECT COUNT(*) AS unread_count
    FROM alerts
    WHERE user_id = %s AND is_read = FALSE
"""

_SELECT_ACTIVE_ALERT = """
    SELECT alert_id
    FROM alerts
    WHERE user_id = %s AND portfolio_id = %s AND category = %s AND metric = %s
      AND created_at > NOW() - INTERVAL 24 HOUR
    LIMIT 1
"""

_UPDATE_MARK_READ = """
    UPDATE alerts SET is_read = TRUE
    WHERE alert_id = %s
"""

_SELECT_ALERT_BY_ID = """
    SELECT alert_id, portfolio_id, user_id, category, severity, metric,
           observed_value, threshold, message, is_read, created_at
    FROM alerts
    WHERE alert_id = %s
"""


# --- Data-access functions ------------------------------------------------

def get_alert(alert_id: int) -> Optional[dict[str, Any]]:
    """Return a single alert row by id, or None."""
    return fetch_one(_SELECT_ALERT_BY_ID, (alert_id,))

def insert_alert(alert: dict[str, Any]) -> int:
    """Persist a generated alert and return its new alert_id."""
    return insert(
        _INSERT_ALERT,
        (
            alert.get("portfolio_id"),
            alert["user_id"],
            alert["category"],
            alert["severity"],
            alert["metric"],
            alert.get("observed_value"),
            alert.get("threshold"),
            alert.get("message", ""),
        ),
    )


def list_alerts(
    user_id: int,
    portfolio_id: Optional[int] = None,
    unread_only: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return a user's alerts, newest first, optionally filtered."""
    return fetch_all(
        _SELECT_ALERTS,
        (user_id, portfolio_id, portfolio_id, unread_only, min(max(limit, 1), 1000)),
    )


def count_unread(user_id: int) -> int:
    """Return how many of the user's alerts are still unread."""
    row = fetch_one(_SELECT_UNREAD_COUNT, (user_id,))
    return int((row or {}).get("unread_count") or 0)


def has_active_alert(
    user_id: int,
    portfolio_id: int,
    category: str,
    metric: str,
) -> bool:
    """True if an alert for the same condition already exists from the last 24h.

    Read state is intentionally ignored: emailing marks an alert read, so checking
    only unread rows would let a persistent condition be re-created (and re-emailed)
    every interval. This window-based dedupe caps it at roughly one alert/day per
    condition while still letting read alerts stay cleared from the dashboard.
    """
    row = fetch_one(_SELECT_ACTIVE_ALERT, (user_id, portfolio_id, category, metric))
    return row is not None


def mark_read(alert_id: int) -> bool:
    """Mark an alert as read. Returns True when a row was updated."""
    return execute(_UPDATE_MARK_READ, (alert_id,)) > 0
