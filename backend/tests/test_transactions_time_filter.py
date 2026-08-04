import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.transaction import get_transactions_in_period, resolve_time_range


def test_resolve_time_range_supports_common_intervals(monkeypatch):
    assert resolve_time_range("last_week", as_of=date(2024, 5, 15)) == (
        date(2024, 5, 8),
        date(2024, 5, 15),
    )
    assert resolve_time_range("last_month", as_of=date(2024, 5, 15)) == (
        date(2024, 4, 15),
        date(2024, 5, 15),
    )
    assert resolve_time_range("last_6_months", as_of=date(2024, 5, 15)) == (
        date(2023, 11, 15),
        date(2024, 5, 15),
    )
    assert resolve_time_range("last_1_year", as_of=date(2024, 5, 15)) == (
        date(2023, 5, 15),
        date(2024, 5, 15),
    )
    assert resolve_time_range("last_5_years", as_of=date(2024, 5, 15)) == (
        date(2019, 5, 15),
        date(2024, 5, 15),
    )


def test_get_transactions_in_period_builds_range_query(monkeypatch):
    captured = {}

    def fake_fetch_all(query, params):
        captured["query"] = query
        captured["params"] = params
        return [{"trans_id": 1}]

    monkeypatch.setattr("app.models.transaction.fetch_all", fake_fetch_all)

    result = get_transactions_in_period(
        portfolio_id=7,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        limit=10,
        offset=5,
    )

    assert result == [{"trans_id": 1}]
    assert "AND ts BETWEEN %s AND %s" in captured["query"]
    assert captured["params"][:2] == [7, date(2024, 1, 1)]
    assert captured["params"][2] == date(2024, 1, 31)
    assert captured["params"][-2:] == [10, 5]
