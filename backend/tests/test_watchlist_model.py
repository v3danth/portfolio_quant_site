from decimal import Decimal

from app.models.watchlist import get_watchlist_stocks


def test_get_watchlist_stocks_enriches_day_change(monkeypatch):
    rows = [
        {
            "stock_id": 1,
            "symbol": "NVDA",
            "short_name": "NVIDIA Corporation",
            "sector": "Technology",
            "current_price": Decimal("200.75"),
            "previous_close": Decimal("195.04"),
        }
    ]

    monkeypatch.setattr("app.models.watchlist.fetch_all", lambda query, params=(): rows)

    result = get_watchlist_stocks()

    assert result[0]["symbol"] == "NVDA"
    assert result[0]["day_change"] == Decimal("5.71")
    assert result[0]["day_change_pct"] == Decimal("2.93")
