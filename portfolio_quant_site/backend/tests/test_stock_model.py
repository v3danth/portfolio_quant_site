from datetime import date, datetime, time
from decimal import Decimal

from app.models.stock import build_price_candles
from app.services import market_data, price_refresh


def test_build_price_candles_aggregates_weekly():
    rows = [
        {
            "ts": "2024-01-01 00:00:00",
            "interval": "1d",
            "open": Decimal("100"),
            "high": Decimal("105"),
            "low": Decimal("95"),
            "close": Decimal("101"),
            "adj_close": Decimal("101"),
            "volume": 1000,
            "dividend": Decimal("0"),
            "stock_split": Decimal("0"),
        },
        {
            "ts": "2024-01-02 00:00:00",
            "interval": "1d",
            "open": Decimal("102"),
            "high": Decimal("108"),
            "low": Decimal("98"),
            "close": Decimal("103"),
            "adj_close": Decimal("103"),
            "volume": 1200,
            "dividend": Decimal("0"),
            "stock_split": Decimal("0"),
        },
    ]

    result = build_price_candles(rows, "1w", 42)

    assert len(result) == 1
    assert result[0]["stock_id"] == 42
    assert result[0]["open"] == Decimal("101")
    assert result[0]["high"] == Decimal("108")
    assert result[0]["low"] == Decimal("95")
    assert result[0]["close"] == Decimal("102")


class _FakeFastInfo:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)

    def __getitem__(self, key):
        return self._values[key]


class _FakeTicker:
    def __init__(self, fast_info_values):
        self.fast_info = _FakeFastInfo(fast_info_values)


def test_fetch_live_quote_falls_back_to_close(monkeypatch):
    monkeypatch.setattr(
        market_data.yf,
        "Ticker",
        lambda symbol: _FakeTicker(
            {
                "last_price": 150.5,
                "open": None,
                "day_high": None,
                "day_low": 148.25,
                "last_volume": 1000,
            }
        ),
    )

    quote = market_data.fetch_live_quote("TEST")

    assert quote is not None
    assert quote["open"] == Decimal("150.5")
    assert quote["high"] == Decimal("150.5")
    assert quote["low"] == Decimal("148.25")
    assert quote["close"] == Decimal("150.5")
    assert quote["volume"] == 1000


def test_refresh_all_prices_builds_daily_rows(monkeypatch):
    monkeypatch.setattr(
        price_refresh.stock_model,
        "get_all_symbols",
        lambda: [{"stock_id": 1, "symbol": "AAA"}, {"stock_id": 2, "symbol": "BBB"}],
    )
    monkeypatch.setattr(
        price_refresh,
        "fetch_live_quote",
        lambda symbol: {
            "open": Decimal("10"),
            "high": Decimal("11"),
            "low": Decimal("9"),
            "close": Decimal("10.5"),
            "volume": 500,
        },
    )

    captured = {}

    def fake_upsert(rows):
        captured["rows"] = rows
        return len(rows)

    monkeypatch.setattr(price_refresh.stock_model, "upsert_live_prices", fake_upsert)

    result = price_refresh.refresh_all_prices()

    assert result["status"] == "ok"
    assert result["total"] == 2
    assert result["updated"] == 2
    assert result["failed"] == 0

    today_midnight = datetime.combine(date.today(), time.min)
    assert captured["rows"] == [
        (1, today_midnight, "1d", Decimal("10"), Decimal("11"), Decimal("9"), Decimal("10.5"), Decimal("10.5"), 500),
        (2, today_midnight, "1d", Decimal("10"), Decimal("11"), Decimal("9"), Decimal("10.5"), Decimal("10.5"), 500),
    ]
