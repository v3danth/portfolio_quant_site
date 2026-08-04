from decimal import Decimal

from app.models.stock import build_price_candles


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
