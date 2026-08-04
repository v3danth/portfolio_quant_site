from decimal import Decimal

import pandas as pd
import pytest
from app.services.analytics import (
    annualized_return,
    annualized_volatility,
    beta,
    build_allocation,
    build_portfolio_pnl,
    build_portfolio_risk,
    build_stock_pnl,
    historical_var,
    invested_by_position,
    max_drawdown,
    realized_pnl_by_position,
    select_performers,
    sharpe_ratio,
    unrealized_pnl,
)

_ZERO = Decimal("0")


def _t(portfolio_id, stock_id, trans_type, quantity, price):
    return {
        "portfolio_id": portfolio_id,
        "stock_id": stock_id,
        "trans_type": trans_type,
        "quantity": Decimal(str(quantity)) if quantity is not None else None,
        "price": Decimal(str(price)) if price is not None else None,
    }


def test_unrealized_pnl_basic():
    pnl, pct = unrealized_pnl(Decimal("10"), Decimal("150"), Decimal("170"))
    assert pnl == Decimal("200")
    assert pct == 200 / 1500


def test_unrealized_pnl_missing_price_returns_none():
    assert unrealized_pnl(Decimal("10"), Decimal("150"), None) == (None, None)


def test_unrealized_pnl_zero_cost_basis_has_none_pct():
    pnl, pct = unrealized_pnl(Decimal("0"), Decimal("0"), Decimal("170"))
    assert pnl == Decimal("0")
    assert pct is None


def test_realized_pnl_weighted_average():
    transactions = [
        _t(1, 1, "BUY", 10, 100),
        _t(1, 1, "BUY", 10, 200),
        _t(1, 1, "SELL", 10, 150),
        _t(1, 1, "SELL", 5, 200),
    ]
    realized = realized_pnl_by_position(transactions)
    assert realized == {(1, 1): Decimal("250")}


def test_realized_pnl_ignores_non_trade_types():
    transactions = [
        _t(1, 1, "DEPOSIT", None, None),
        _t(1, 1, "BUY", 4, 100),
        _t(1, 1, "SELL", 2, 150),
        _t(1, 1, "DIVIDEND", 1, 5),
    ]
    realized = realized_pnl_by_position(transactions)
    assert realized == {(1, 1): Decimal("100")}


def test_realized_pnl_tracks_portfolios_independently():
    transactions = [
        _t(1, 1, "BUY", 10, 100),
        _t(2, 1, "BUY", 5, 200),
        _t(1, 1, "SELL", 10, 150),
    ]
    realized = realized_pnl_by_position(transactions)
    assert realized[(1, 1)] == Decimal("500")
    assert realized.get((2, 1), _ZERO) == _ZERO


def test_invested_by_position():
    transactions = [
        _t(1, 1, "BUY", 10, 100),
        _t(1, 1, "BUY", 10, 200),
        _t(1, 1, "SELL", 10, 150),
        _t(1, 2, "BUY", 3, 50),
    ]
    assert invested_by_position(transactions) == {
        (1, 1): Decimal("3000"),
        (1, 2): Decimal("150"),
    }


def test_build_stock_pnl_aggregates_across_portfolios():
    stock = {"stock_id": 1, "symbol": "AAA", "short_name": "Alpha"}
    holdings = [
        {
            "portfolio_id": 1,
            "stock_id": 1,
            "symbol": "AAA",
            "short_name": "Alpha",
            "quantity": Decimal("5"),
            "avg_buy_price": Decimal("150"),
            "price_live": Decimal("180"),
            "market_value": Decimal("900"),
        },
        {
            "portfolio_id": 2,
            "stock_id": 1,
            "symbol": "AAA",
            "short_name": "Alpha",
            "quantity": Decimal("10"),
            "avg_buy_price": Decimal("100"),
            "price_live": Decimal("180"),
            "market_value": Decimal("1800"),
        },
    ]
    transactions = [
        _t(1, 1, "BUY", 10, 100),
        _t(1, 1, "BUY", 10, 200),
        _t(1, 1, "SELL", 10, 150),
        _t(1, 1, "SELL", 5, 200),
        _t(2, 1, "BUY", 10, 100),
    ]

    result = build_stock_pnl(stock, holdings, transactions)

    assert result["symbol"] == "AAA"
    assert result["quantity"] == Decimal("15")
    assert result["cost_basis"] == Decimal("1750")
    assert result["market_value"] == Decimal("2700")
    assert result["avg_buy_price"] == Decimal("1750") / Decimal("15")
    assert result["unrealized_pnl"] == Decimal("950")
    assert result["realized_pnl"] == Decimal("250")
    assert result["invested"] == Decimal("4000")
    assert result["total_pnl"] == Decimal("1200")
    assert result["total_pnl_pct"] == 1200 / 4000


def test_build_portfolio_pnl():
    holdings = [
        {
            "stock_id": 1,
            "symbol": "AAA",
            "short_name": "Alpha",
            "quantity": Decimal("5"),
            "avg_buy_price": Decimal("150"),
            "price_live": Decimal("180"),
            "market_value": Decimal("900"),
        },
        {
            "stock_id": 2,
            "symbol": "BBB",
            "short_name": "Beta",
            "quantity": Decimal("3"),
            "avg_buy_price": Decimal("50"),
            "price_live": Decimal("60"),
            "market_value": Decimal("180"),
        },
    ]
    transactions = [
        _t(1, 1, "BUY", 10, 100),
        _t(1, 1, "BUY", 10, 200),
        _t(1, 1, "SELL", 10, 150),
        _t(1, 1, "SELL", 5, 200),
        _t(1, 2, "BUY", 3, 50),
    ]

    result = build_portfolio_pnl(1, holdings, transactions)

    assert result["holdings_count"] == 2
    assert result["total_cost_basis"] == Decimal("900")
    assert result["total_market_value"] == Decimal("1080")
    assert result["total_unrealized_pnl"] == Decimal("180")
    assert result["total_realized_pnl"] == Decimal("250")
    assert result["total_pnl"] == Decimal("430")
    assert result["total_invested"] == Decimal("3150")

    alpha = result["holdings"][0]
    assert alpha["symbol"] == "AAA"
    assert alpha["unrealized_pnl"] == Decimal("150")
    assert alpha["realized_pnl"] == Decimal("250")
    assert alpha["total_pnl"] == Decimal("400")


def test_build_portfolio_pnl_empty_returns_zeros():
    result = build_portfolio_pnl(9, [], [])
    assert result["holdings_count"] == 0
    assert result["total_cost_basis"] == _ZERO
    assert result["total_realized_pnl"] == _ZERO
    assert result["total_invested"] == _ZERO
    assert result["holdings"] == []


def test_build_allocation_counts_by_key():
    rows = [
        {"quote_type": "EQUITY", "sector": "Technology"},
        {"quote_type": "EQUITY", "sector": "Financials"},
        {"quote_type": "ETF", "sector": "Technology"},
        {"quote_type": "ETF", "sector": "Technology"},
    ]
    result = build_allocation(1, rows, "quote_type")
    assert result["portfolio_id"] == 1
    assert result["grouping"] == "quote_type"
    assert result["total_holdings"] == 4
    by_label = {group["label"]: group for group in result["groups"]}
    assert by_label["EQUITY"]["holdings_count"] == 2
    assert by_label["EQUITY"]["weight"] == 0.5
    assert by_label["ETF"]["holdings_count"] == 2
    assert sum(group["weight"] for group in result["groups"]) == 1.0


def test_build_allocation_sorts_by_count_desc():
    rows = [
        {"sector": "Technology"},
        {"sector": "Technology"},
        {"sector": "Technology"},
        {"sector": "Financials"},
    ]
    result = build_allocation(1, rows, "sector")
    assert [group["label"] for group in result["groups"]] == ["Technology", "Financials"]


def test_build_allocation_unknown_for_missing_key():
    rows = [{"quote_type": "EQUITY"}, {"quote_type": None}, {"sector": ""}]
    result = build_allocation(1, rows, "quote_type")
    by_label = {group["label"]: group for group in result["groups"]}
    assert by_label["Unknown"]["holdings_count"] == 2
    assert result["total_holdings"] == 3


def test_build_allocation_empty():
    result = build_allocation(9, [], "quote_type")
    assert result["total_holdings"] == 0
    assert result["groups"] == []


def _pnl_row(symbol, total_pnl_pct):
    return {"symbol": symbol, "total_pnl_pct": total_pnl_pct}


def test_select_performers_picks_best_and_worst():
    rows = [
        _pnl_row("AAA", 0.20),
        _pnl_row("BBB", -0.10),
        _pnl_row("CCC", 0.05),
    ]
    result = select_performers(rows, "total_pnl_pct")
    assert result["holdings_count"] == 3
    assert result["metric"] == "total_pnl_pct"
    assert result["top_performer"]["symbol"] == "AAA"
    assert result["worst_performer"]["symbol"] == "BBB"


def test_select_performers_excludes_unranked_rows():
    rows = [
        _pnl_row("AAA", 0.20),
        _pnl_row("BBB", None),
        _pnl_row("CCC", -0.10),
    ]
    result = select_performers(rows, "total_pnl_pct")
    assert result["holdings_count"] == 3
    assert result["top_performer"]["symbol"] == "AAA"
    assert result["worst_performer"]["symbol"] == "CCC"


def test_select_performers_single_holding_is_both():
    result = select_performers([_pnl_row("AAA", 0.20)], "total_pnl_pct")
    assert result["top_performer"]["symbol"] == "AAA"
    assert result["worst_performer"]["symbol"] == "AAA"


def test_select_performers_empty_returns_none():
    result = select_performers([], "total_pnl_pct")
    assert result["holdings_count"] == 0
    assert result["top_performer"] is None
    assert result["worst_performer"] is None


def test_select_performers_all_unranked_returns_none():
    rows = [_pnl_row("AAA", None), _pnl_row("BBB", None)]
    result = select_performers(rows, "total_pnl_pct")
    assert result["holdings_count"] == 2
    assert result["top_performer"] is None
    assert result["worst_performer"] is None


def test_annualized_volatility_constant_returns_is_zero():
    returns = pd.Series([0.01] * 100)
    assert annualized_volatility(returns) == pytest.approx(0.0, abs=1e-12)


def test_annualized_return_compounds_daily():
    returns = pd.Series([0.01] * 252)
    assert annualized_return(returns) == pytest.approx(1.01 ** 252 - 1)


def test_max_drawdown_measures_peak_to_trough():
    returns = pd.Series([0.5, -0.5])
    assert max_drawdown(returns) == pytest.approx(-0.5)


def test_historical_var_negates_tail_quantile():
    returns = pd.Series([0.1, -0.2, 0.0, 0.05, -0.05, 0.02])
    assert historical_var(returns, 0.95) == pytest.approx(-float(returns.quantile(0.05)))


def test_beta_scales_with_portfolio_leverage():
    benchmark_returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
    portfolio_returns = 2 * benchmark_returns
    assert beta(portfolio_returns, benchmark_returns) == pytest.approx(2.0)


def test_sharpe_ratio_zero_volatility_is_none():
    assert sharpe_ratio(pd.Series([0.01] * 50), 0.02) is None


def test_build_portfolio_risk_computes_metrics():
    dates = pd.date_range("2024-01-01", periods=6, freq="B")
    adj = pd.DataFrame(
        {
            1: [100, 100, 100, 100, 100, 100],
            2: [100, 110, 121, 110, 100, 105],
        },
        index=dates,
    )
    holdings = [
        {"stock_id": 1, "quantity": 10},
        {"stock_id": 2, "quantity": 10},
    ]

    result = build_portfolio_risk(1, holdings, adj, adj.copy())

    assert result["portfolio_id"] == 1
    assert result["weights_count"] == 2
    assert result["observations"] == 5
    assert result["window_start"] == dates[0]
    assert result["window_end"] == dates[-1]
    metrics = result["metrics"]
    assert metrics["annualized_volatility"] is not None
    assert metrics["annualized_return"] is not None
    assert metrics["sharpe_ratio"] is not None
    assert metrics["max_drawdown"] is not None
    assert metrics["value_at_risk_95"] is not None
    assert metrics["beta"] is None
    assert result["benchmark_metrics"] is None


def test_build_portfolio_risk_beta_vs_benchmark():
    dates = pd.date_range("2024-01-01", periods=6, freq="B")
    benchmark_returns = pd.Series([0.0, 0.01, -0.02, 0.03, -0.01, 0.02], index=dates)
    benchmark_close = 100 * (1 + benchmark_returns).cumprod()
    prices = 100 * (1 + 2 * benchmark_returns).cumprod()
    closes = pd.DataFrame({1: prices}, index=dates)

    result = build_portfolio_risk(
        1,
        [{"stock_id": 1, "quantity": 1}],
        closes,
        closes.copy(),
        benchmark_close=benchmark_close,
        benchmark_symbol="SPY",
    )

    assert result["benchmark"] == "SPY"
    assert result["metrics"]["beta"] == pytest.approx(2.0)
    assert result["benchmark_metrics"]["beta"] is None


def test_build_portfolio_risk_empty_returns_none_metrics():
    result = build_portfolio_risk(1, [], pd.DataFrame(), pd.DataFrame())
    assert result["weights_count"] == 0
    assert result["observations"] == 0
    assert result["window_start"] is None
    assert result["metrics"]["annualized_volatility"] is None
    assert result["benchmark_metrics"] is None
