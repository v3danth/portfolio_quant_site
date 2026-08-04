from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.holding import _normalize_holding_row, _position_is_active


def test_position_is_active_with_future_expiry():
    row = {
        "is_position": True,
        "position_expires_at": datetime.now(timezone.utc) + timedelta(seconds=30),
    }

    assert _position_is_active(row) is True


def test_position_is_inactive_after_expiry():
    row = {
        "is_position": True,
        "position_expires_at": datetime.now(timezone.utc) - timedelta(seconds=30),
    }

    assert _position_is_active(row) is False


def test_normalize_holding_row_sets_market_value_and_position():
    row = {
        "quantity": Decimal("2.0"),
        "price_live": Decimal("50.0"),
        "is_position": True,
        "position_expires_at": datetime.now(timezone.utc) + timedelta(seconds=30),
    }

    normalized = _normalize_holding_row(row)

    assert normalized["market_value"] == Decimal("100.0")
    assert normalized["is_position"] is True
