from datetime import date
from decimal import Decimal

from app.models.stock import build_compare_price_payload, build_price_candles, resolve_time_range


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


def test_resolve_time_range_supports_common_periods():
    as_of = date(2026, 8, 4)

    start, end = resolve_time_range("last_week", as_of=as_of)
    assert start == date(2026, 7, 28)
    assert end == as_of

    start, end = resolve_time_range("last_6_months", as_of=as_of)
    assert start == date(2026, 2, 4)
    assert end == as_of

    start, end = resolve_time_range("custom", as_of=as_of)
    assert start is None
    assert end is None


def test_build_compare_price_payload_groups_series_by_stock():
    payload = build_compare_price_payload(
        first_stock_id=1,
        first_symbol="AAPL",
        first_candles=[{"stock_id": 1, "close": Decimal("10"), "timestamp": date(2024, 1, 1)}],
        second_stock_id=2,
        second_symbol="MSFT",
        second_candles=[{"stock_id": 2, "close": Decimal("20"), "timestamp": date(2024, 1, 1)}],
    )

    assert payload["series"][0]["stock_id"] == 1
    assert payload["series"][0]["symbol"] == "AAPL"
    assert payload["series"][1]["stock_id"] == 2
    assert payload["series"][1]["symbol"] == "MSFT"
