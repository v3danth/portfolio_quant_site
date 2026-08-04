"""Streamlit frontend for the QPMS FastAPI backend.

Run with: streamlit run frontend/app.py
"""
import inspect
import os
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api_client
import utils
from api_client import APIError, ApiClient
from theme import CHART_COLORS, PLOTLY_LAYOUT, inject_css

DEFAULT_BASE_URL = getattr(api_client, "DEFAULT_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Portfolio Quant Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


# --- State & client -----------------------------------------------------

def initialize_state() -> None:
    st.session_state.setdefault("api_base_url", os.getenv("API_BASE_URL", DEFAULT_BASE_URL))
    st.session_state.setdefault("selected_user_id", None)
    st.session_state.setdefault("selected_portfolio_id", None)


def get_client() -> ApiClient:
    return ApiClient(st.session_state.api_base_url)


<<<<<<< HEAD
=======
def select_option(options: list[Any], current_value: Any, label: str, format_func=str) -> Any:
    if not options:
        return None
    index = options.index(current_value) if current_value in options else 0
    return st.selectbox(label, options=options, index=index, format_func=format_func)


>>>>>>> 030c08ed865699155ee3d25a9ed6cbd5efe70357
def list_transactions_compat(client: ApiClient, portfolio_id: int, *, type_filter: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    sig = inspect.signature(client.list_transactions)
    parameters = sig.parameters

    if type_filter and "trans_type" in parameters:
        params["trans_type"] = type_filter
    if "limit" in parameters:
        params["limit"] = 200

    return client.list_transactions(portfolio_id, **params)


def price_series(candles: list[dict[str, Any]]) -> pd.Series:
    """Build a time-indexed close-price series from raw OHLC candle dicts."""
    if not candles:
        return pd.Series(dtype="float64")
    df = pd.DataFrame(candles)
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.sort_values("ts").set_index("ts")
    close = pd.to_numeric(df["close"], errors="coerce")
    if "adj_close" in df.columns:
        adj = pd.to_numeric(df["adj_close"], errors="coerce")
        close = adj.fillna(close)
    close.name = "price"
    return close


# --- App ------------------------------------------------------------------

initialize_state()
client = get_client()

st.title("📈 Portfolio Quant Dashboard")

try:
    health = client.health()
except APIError as exc:
    st.error(str(exc))
    st.info("Start the backend with: uvicorn main:app --reload  (run from the backend/ folder)")
    st.stop()

with st.sidebar:
    st.header("Controls")
    st.text_input("Backend URL", key="api_base_url")
    if st.button("Refresh data", use_container_width=True):
        st.rerun()

    st.divider()

    users = client.list_users()
<<<<<<< HEAD
    preferred_user = None
    for user in users:
        raw_name = str(user.get("user_name") or "").strip()
        if raw_name.lower().replace(" ", "") == "pawcoder":
            preferred_user = user
            break
    if preferred_user is None and users:
        preferred_user = users[0]

    if preferred_user is not None:
        st.session_state.selected_user_id = preferred_user["user_id"]
        st.selectbox(
            "User",
            options=[preferred_user["user_id"]],
            index=0,
            format_func=lambda uid: "Paw Coder",
            disabled=True,
            key="user_selector",
=======
    user_ids = [user["user_id"] for user in users]
    user_lookup = {user["user_id"]: user for user in users}
    if user_ids:
        st.session_state.selected_user_id = select_option(
            user_ids,
            st.session_state.selected_user_id,
            "User",
            format_func=lambda uid: user_lookup[uid].get("user_name", f"User {uid}"),
>>>>>>> 030c08ed865699155ee3d25a9ed6cbd5efe70357
        )
    else:
        st.session_state.selected_user_id = None
        st.info("No users found in the database yet.")

    if st.session_state.selected_user_id is not None:
        portfolios = client.list_portfolios(int(st.session_state.selected_user_id))
        portfolio_ids = [p["portfolio_id"] for p in portfolios]
        portfolio_lookup = {p["portfolio_id"]: p for p in portfolios}
        if portfolio_ids:
<<<<<<< HEAD
            if st.session_state.selected_portfolio_id not in portfolio_ids:
                st.session_state.selected_portfolio_id = portfolio_ids[0]
            selected_portfolio_id = st.selectbox(
                "Portfolio",
                options=portfolio_ids,
                index=portfolio_ids.index(st.session_state.selected_portfolio_id),
                format_func=lambda pid: portfolio_lookup[pid].get("name", f"Portfolio {pid}"),
                key="portfolio_selector",
            )
            st.session_state.selected_portfolio_id = selected_portfolio_id
=======
            st.session_state.selected_portfolio_id = select_option(
                portfolio_ids,
                st.session_state.selected_portfolio_id,
                "Portfolio",
                format_func=lambda pid: portfolio_lookup[pid].get("name", f"Portfolio {pid}"),
            )
>>>>>>> 030c08ed865699155ee3d25a9ed6cbd5efe70357
        else:
            st.session_state.selected_portfolio_id = None
            st.info("No portfolios yet for this user.")
    else:
        st.session_state.selected_portfolio_id = None

    with st.form("create_portfolio"):
        st.caption("Create a new portfolio")
        portfolio_name = st.text_input("Name", value="My Portfolio")
        submitted = st.form_submit_button("Create portfolio", use_container_width=True)
        if submitted and st.session_state.selected_user_id is not None:
            try:
<<<<<<< HEAD
                created_portfolio = client.create_portfolio(
                    int(st.session_state.selected_user_id), portfolio_name.strip() or "My Portfolio"
                )
                st.session_state.selected_portfolio_id = created_portfolio.get("portfolio_id")
=======
                client.create_portfolio(int(st.session_state.selected_user_id), portfolio_name.strip() or "My Portfolio")
>>>>>>> 030c08ed865699155ee3d25a9ed6cbd5efe70357
                st.success("Portfolio created")
                st.rerun()
            except APIError as exc:
                st.error(str(exc))

if st.session_state.selected_user_id is None:
    st.info("No users exist yet — seed one via the backend/portfolio_db_setup scripts.")
    st.stop()

if st.session_state.selected_portfolio_id is None:
    st.info("Create a portfolio in the sidebar to get started.")
    st.stop()

selected_user_id = int(st.session_state.selected_user_id)
selected_portfolio_id = int(st.session_state.selected_portfolio_id)

user = client.get_user(selected_user_id)
portfolio = client.get_portfolio(selected_portfolio_id)
holdings = client.list_holdings(selected_portfolio_id)
metrics = utils.portfolio_metrics(holdings, float(user.get("acct_balance", 0) or 0))
holdings_df = utils.holdings_dataframe(holdings)

<<<<<<< HEAD
st.subheader(f"{portfolio.get('name', 'Portfolio')} · Paw Coder")
=======
st.subheader(f"{portfolio.get('name', 'Portfolio')} · {user.get('user_name', 'User')}")
>>>>>>> 030c08ed865699155ee3d25a9ed6cbd5efe70357

col1, col2, col3, col4 = st.columns(4)
col1.metric("Cash balance", utils.format_currency(metrics["cash_balance"]))
col2.metric("Holdings value", utils.format_currency(metrics["market_value"]))
col3.metric("Net equity", utils.format_currency(metrics["equity"]))
col4.metric("Unrealized P/L", utils.format_currency(metrics["pnl"]), utils.format_pct(metrics["pnl_pct"]))

dashboard_tab, trade_tab, stocks_tab, analytics_tab, transactions_tab = st.tabs(
    ["Dashboard", "Trade", "Stocks", "Analytics", "Transactions"]
)

# --- Dashboard --------------------------------------------------------

with dashboard_tab:
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Holdings")
        if holdings_df.empty:
            st.info("This portfolio has no holdings yet — buy a position in the Trade tab.")
        else:
            st.dataframe(
                holdings_df[
                    ["symbol", "short_name", "quantity", "avg_buy_price", "price_live", "market_value", "unrealized_pnl"]
                ].sort_values("symbol"),
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.subheader("Allocation")
        if holdings_df.empty or holdings_df["market_value"].sum() <= 0:
            st.info("No market value to chart yet.")
        else:
            alloc = holdings_df[holdings_df["market_value"] > 0]
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=alloc["symbol"],
                        values=alloc["market_value"],
                        hole=0.55,
                        marker=dict(colors=CHART_COLORS, line=dict(color="#020617", width=2)),
                        textinfo="label+percent",
                    )
                ]
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=320, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent transactions")
    try:
        recent_tx = client.list_transactions(selected_portfolio_id, limit=10)
    except TypeError:
        recent_tx = client.list_transactions(selected_portfolio_id)
    if recent_tx:
        tx_df = pd.DataFrame(recent_tx)
        tx_df["ts"] = pd.to_datetime(tx_df["ts"])
        st.dataframe(
            tx_df[["trans_type", "stock_id", "quantity", "price", "amount", "ts"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No transactions yet.")

# --- Trade --------------------------------------------------------------

with trade_tab:
    stock_search = st.text_input("Search stocks to trade (symbol or name)", key="trade_search")
    stocks = client.list_stocks(search=stock_search or None, limit=200)
    stock_lookup = {s["symbol"]: s for s in stocks}
    stock_symbols = sorted(stock_lookup.keys())

    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("🛒 Buy a position", expanded=True):
            if not stock_symbols:
                st.info("No stocks match your search.")
            else:
                with st.form("buy_form"):
                    buy_symbol = st.selectbox("Stock", stock_symbols, index=0)
<<<<<<< HEAD
                    selected_stock = stock_lookup.get(buy_symbol)
                    quote_price = None
                    if selected_stock:
                        quote = client.get_stock_quote(int(selected_stock["stock_id"]))
                        if quote:
                            quote_price = float(quote["price"])
                            st.caption(f"Live price from API: {utils.format_currency(quote_price)}")
                        else:
                            st.caption("Live price unavailable")

                    buy_quantity = st.number_input(
                        "Quantity",
                        min_value=1,
                        step=1,
                        value=1,
                        format="%d",
                    )
                    buy_submitted = st.form_submit_button("Buy stock")
                    if buy_submitted:
                        try:
                            client.buy_stock(selected_portfolio_id, buy_symbol, buy_quantity, quote_price)
                            st.success(f"Purchased {buy_quantity} share(s) of {buy_symbol}")
=======
                    buy_quantity = st.number_input("Quantity", min_value=0.01, step=0.01, format="%.2f")
                    buy_price = st.number_input(
                        "Optional buy price (blank/0 = use live price)", min_value=0.0, step=0.01, format="%.2f"
                    )
                    buy_submitted = st.form_submit_button("Buy stock")
                    if buy_submitted:
                        price_value = None if buy_price <= 0 else buy_price
                        try:
                            client.buy_stock(selected_portfolio_id, buy_symbol, buy_quantity, price_value)
                            st.success(f"Purchased {buy_quantity} shares of {buy_symbol}")
>>>>>>> 030c08ed865699155ee3d25a9ed6cbd5efe70357
                            st.rerun()
                        except APIError as exc:
                            st.error(str(exc))

    with col_b:
        with st.expander("📉 Sell a position", expanded=True):
            if holdings_df.empty:
                st.info("Nothing to sell yet.")
            else:
                with st.form("sell_form"):
                    open_positions = {row["symbol"]: row for _, row in holdings_df.iterrows()}
                    sell_symbol = st.selectbox("Holding to sell", list(open_positions.keys()))
                    selected_holding = open_positions[sell_symbol]
                    sell_all = st.checkbox("Sell full position")
<<<<<<< HEAD
                    max_quantity = max(1, int(float(selected_holding["quantity"])))
                    sell_quantity = st.number_input(
                        "Quantity to sell",
                        min_value=1,
                        max_value=max_quantity,
                        step=1,
                        value=min(1, max_quantity),
                        format="%d",
                        disabled=sell_all,
                    )
                    quote_price = None
                    quote = client.get_stock_quote(int(selected_holding["stock_id"]))
                    if quote:
                        quote_price = float(quote["price"])
                        st.caption(f"Live price from API: {utils.format_currency(quote_price)}")
                    else:
                        st.caption("Live price unavailable")

                    sell_submitted = st.form_submit_button("Sell stock")
                    if sell_submitted:
                        quantity_value = None if sell_all else sell_quantity
                        try:
                            client.sell_stock(
                                selected_portfolio_id, int(selected_holding["stock_id"]), quantity_value, quote_price
=======
                    sell_quantity = st.number_input(
                        "Quantity to sell",
                        min_value=0.01,
                        max_value=float(selected_holding["quantity"]),
                        value=float(selected_holding["quantity"]),
                        step=0.01,
                        format="%.2f",
                        disabled=sell_all,
                    )
                    sell_price = st.number_input(
                        "Optional sell price (blank/0 = use live price)", min_value=0.0, step=0.01, format="%.2f"
                    )
                    sell_submitted = st.form_submit_button("Sell stock")
                    if sell_submitted:
                        quantity_value = None if sell_all else sell_quantity
                        price_value = None if sell_price <= 0 else sell_price
                        try:
                            client.sell_stock(
                                selected_portfolio_id, int(selected_holding["stock_id"]), quantity_value, price_value
>>>>>>> 030c08ed865699155ee3d25a9ed6cbd5efe70357
                            )
                            st.success(f"Sold {sell_symbol}")
                            st.rerun()
                        except APIError as exc:
                            st.error(str(exc))

    st.divider()
    with st.expander("⚠️ Danger zone"):
        st.caption(f"Delete portfolio '{portfolio.get('name')}' — this cannot be undone.")
        if st.button("Delete this portfolio"):
            try:
                client.delete_portfolio(selected_portfolio_id)
                st.success("Portfolio deleted")
                st.session_state.selected_portfolio_id = None
                st.rerun()
            except APIError as exc:
                st.error(str(exc))

# --- Stocks -------------------------------------------------------------

with stocks_tab:
    st.subheader("Discover stocks")
    discover_search = st.text_input("Search by symbol or name", key="discover_search")
    discover_results = client.list_stocks(search=discover_search or None, limit=200)
    discover_df = pd.DataFrame(discover_results)

    if discover_df.empty:
        st.info("No matching stocks found.")
    else:
        st.dataframe(
            discover_df[["symbol", "short_name", "sector"]],
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("Price chart")
        symbol_options = discover_df["symbol"].tolist()
        chosen_symbol = st.selectbox("Stock", symbol_options)
        chosen_stock = discover_df[discover_df["symbol"] == chosen_symbol].iloc[0]
        stock_id = int(chosen_stock["stock_id"])

        detail = client.get_stock(stock_id)
        quote_getter = getattr(client, "get_stock_quote", None)
        quote = quote_getter(stock_id) if callable(quote_getter) else None

        info_cols = st.columns(4)
        info_cols[0].metric("Live price", utils.format_currency(float(quote["price"])) if quote else "n/a")
        info_cols[1].metric("Exchange", detail.get("exchange") or "n/a")
        info_cols[2].metric("Industry", detail.get("industry") or "n/a")
        info_cols[3].metric("Currency", detail.get("currency") or "n/a")

<<<<<<< HEAD
        st.caption("Interval: 1d (daily data only)")
        interval = "1d"
=======
        interval = st.selectbox("Interval", ["1d", "1wk", "1mo", "1h"], index=0)
>>>>>>> 030c08ed865699155ee3d25a9ed6cbd5efe70357
        candles = client.get_stock_prices(stock_id, interval=interval)
        if not candles:
            st.info(f"No price history at interval '{interval}' for {chosen_symbol}.")
        else:
            candles_df = pd.DataFrame(candles)
            candles_df["ts"] = pd.to_datetime(candles_df["ts"])
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=candles_df["ts"],
                        open=candles_df["open"].astype(float),
                        high=candles_df["high"].astype(float),
                        low=candles_df["low"].astype(float),
                        close=candles_df["close"].astype(float),
                        increasing_line_color=CHART_COLORS[2],
                        decreasing_line_color=CHART_COLORS[7],
                        name=chosen_symbol,
                    )
                ]
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=420, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

# --- Analytics --------------------------------------------------------

with analytics_tab:
    st.subheader("Portfolio analytics")
    if holdings_df.empty:
        st.info("Add holdings in the Trade tab to view analytics.")
    else:
        interval = "1d"
        price_series_by_symbol: dict[str, pd.Series] = {}
        analytics_rows: list[dict[str, Any]] = []

        for _, row in holdings_df.iterrows():
            symbol = row["symbol"]
            stock_id = int(row["stock_id"])
            candles = client.get_stock_prices(stock_id, interval=interval)
            series = price_series(candles)
            price_series_by_symbol[symbol] = series
            result = utils.analyze_prices(series, interval=interval)
            analytics_rows.append(
                {
                    "symbol": symbol,
                    "total_return": result["total_return"],
                    "annualized_return": result["annualized_return"],
                    "annualized_volatility": result["annualized_volatility"],
                    "sharpe_ratio": result["sharpe_ratio"],
                    "max_drawdown": result["max_drawdown"],
                }
            )

        analytics_df = pd.DataFrame(analytics_rows)
        display_df = analytics_df.copy()
        for col in ["total_return", "annualized_return", "annualized_volatility", "max_drawdown"]:
            display_df[col] = display_df[col].map(utils.format_pct)
        display_df["sharpe_ratio"] = analytics_df["sharpe_ratio"].map(lambda v: f"{v:,.2f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        weights = {
            row["symbol"]: float(row["market_value"])
            for _, row in holdings_df.iterrows()
            if float(row["market_value"] or 0) > 0
        }
        wi = utils.portfolio_wealth_index(price_series_by_symbol, weights)

        if wi.empty:
            st.info("Not enough shared price history across holdings to build a portfolio wealth curve.")
        else:
            dd = utils.drawdown(wi)
            chart_cols = st.columns(2)
            with chart_cols[0]:
                st.caption("Wealth index (growth of $1, weighted by market value)")
                fig = go.Figure(data=[go.Scatter(x=wi.index, y=wi.values, mode="lines", line=dict(color=CHART_COLORS[0], width=2))])
                fig.update_layout(**PLOTLY_LAYOUT, height=320)
                st.plotly_chart(fig, use_container_width=True)
            with chart_cols[1]:
                st.caption("Drawdown from peak")
                fig = go.Figure(
                    data=[go.Scatter(x=dd.index, y=dd.values, mode="lines", fill="tozeroy", line=dict(color=CHART_COLORS[7], width=2))]
                )
                fig.update_layout(**PLOTLY_LAYOUT, height=320)
                st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("What-if analysis")
        hypo_prices: dict[str, float] = {}
        with st.form("what_if_form"):
            cols = st.columns(2)
            for index, row in holdings_df.iterrows():
                symbol = row["symbol"]
                with cols[index % 2]:
                    hypo_prices[symbol] = st.number_input(
                        f"Hypothetical price for {symbol}",
                        min_value=0.01,
                        value=max(float(row.get("price_live") or 100.0), 0.01),
                        step=0.25,
                        format="%.2f",
                    )
            run_what_if = st.form_submit_button("Run what-if")
        if run_what_if:
            hypothetical_value = sum(
                float(row["quantity"]) * hypo_prices.get(row["symbol"], 0.0) for _, row in holdings_df.iterrows()
            )
            value_difference = hypothetical_value - metrics["market_value"]
            wcol1, wcol2 = st.columns(2)
            wcol1.metric("Hypothetical holdings value", utils.format_currency(hypothetical_value))
            wcol2.metric("Value difference", utils.format_currency(value_difference))

# --- Transactions -------------------------------------------------------

with transactions_tab:
    st.subheader("Transaction history")
    type_filter = st.selectbox("Type", ["All", "BUY", "SELL", "DEPOSIT", "WITHDRAW", "DIVIDEND"])
    try:
        transactions = list_transactions_compat(
            client,
            selected_portfolio_id,
            type_filter=None if type_filter == "All" else type_filter,
        )
    except TypeError:
        transactions = client.list_transactions(selected_portfolio_id)
    if not transactions:
        st.info("No transactions match this filter.")
    else:
        tx_df = pd.DataFrame(transactions)
        tx_df["ts"] = pd.to_datetime(tx_df["ts"])
        st.dataframe(
            tx_df[["trans_id", "trans_type", "stock_id", "quantity", "price", "amount", "trans_details", "ts"]],
            use_container_width=True,
            hide_index=True,
        )
