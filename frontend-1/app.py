from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

DEFAULT_BASE_URL = "http://localhost:9090"
DEFAULT_TIMEOUT = 12
FALLBACK_SYMBOLS = ["AAPL", "GOOGL", "MSFT", "TSLA", "YOYO"]


def inject_ui_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=DM+Serif+Display:ital@0;1&display=swap');

            :root {
                --bg-soft: #0e1117;
                --ink: #e8edf3;
                --accent: #4d9fff;
                --accent-2: #ff8b24;
                --good: #2ecc71;
                --bad: #e74c3c;
            }

            .stApp {
                background:
                    radial-gradient(circle at 15% 10%, rgba(77, 159, 255, 0.08), transparent 35%),
                    radial-gradient(circle at 85% 15%, rgba(255, 139, 36, 0.08), transparent 38%),
                    linear-gradient(180deg, #12161f 0%, var(--bg-soft) 100%);
                color: var(--ink);
                font-family: 'Space Grotesk', sans-serif;
            }

            h1, h2, h3 {
                font-family: 'DM Serif Display', serif;
                letter-spacing: 0.02em;
                color: var(--ink);
            }

            [data-testid="stMetricValue"] {
                color: var(--ink);
            }

            .panel {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(232, 237, 243, 0.10);
                border-radius: 14px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.8rem;
                backdrop-filter: blur(3px);
            }

            .caption {
                font-size: 0.9rem;
                color: #8fa3ba;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_base_url() -> str:
    return st.session_state.get("base_url", DEFAULT_BASE_URL).rstrip("/")


def get_timeout() -> int:
    return int(st.session_state.get("timeout", DEFAULT_TIMEOUT))


def api_request(method: str, path: str, **kwargs: Any) -> Tuple[bool, Any, str, int]:
    url = f"{get_base_url()}{path}"
    timeout = kwargs.pop("timeout", get_timeout())
    try:
        response = requests.request(method=method, url=url, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        return False, None, f"Connection error: {exc}", 0

    if not response.ok:
        return False, None, f"API error {response.status_code}: {response.text}", response.status_code

    if response.status_code == 204:
        return True, None, "", response.status_code

    try:
        return True, response.json(), "", response.status_code
    except ValueError:
        return True, response.text, "", response.status_code


@st.cache_data(ttl=8)
def fetch_market_prices_cache(base_url: str, timeout: int) -> Tuple[bool, Any, str, int]:
    del base_url, timeout
    return api_request("GET", "/analytics/market-prices")


@st.cache_data(ttl=8)
def fetch_portfolios_cache(base_url: str, timeout: int) -> Tuple[bool, Any, str, int]:
    del base_url, timeout
    return api_request("GET", "/portfolios")


def clear_caches() -> None:
    fetch_market_prices_cache.clear()
    fetch_portfolios_cache.clear()


def money(value: float) -> str:
    return f"${value:,.2f}"


def pct(value: float) -> str:
    return f"{value:,.2f}%"


def portfolio_label(p: Dict[str, Any]) -> str:
    return f"#{p.get('id', '?')} - {p.get('owner', 'Unknown')}"


def make_holdings_editor_df(symbols: List[str]) -> pd.DataFrame:
    rows = []
    for symbol in symbols:
        rows.append({"symbol": symbol, "quantity": 0, "purchasePrice": 0.0})
    return pd.DataFrame(rows)


def normalize_holdings(df: pd.DataFrame) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).strip().upper()
        qty = row.get("quantity", 0)
        price = row.get("purchasePrice", 0.0)

        if not symbol:
            continue

        try:
            qty_int = int(float(qty))
        except (TypeError, ValueError):
            continue

        try:
            price_float = float(price)
        except (TypeError, ValueError):
            continue

        if qty_int <= 0 or price_float <= 0:
            continue

        output.append(
            {
                "symbol": symbol,
                "quantity": qty_int,
                "purchasePrice": round(price_float, 4),
            }
        )

    return output


def build_market_sparkline(prices: Dict[str, float]) -> pd.DataFrame:
    ts_start = datetime.utcnow() - timedelta(minutes=55)
    data_rows: List[Dict[str, Any]] = []
    for symbol, current in prices.items():
        seed = abs(hash(symbol)) % (2**32 - 1)
        rng = np.random.default_rng(seed)
        walk = np.cumsum(rng.normal(0, 0.0035, 12))
        series = current * (1 + walk)
        series = np.maximum(series, current * 0.1)

        for i, value in enumerate(series):
            data_rows.append(
                {
                    "time": ts_start + timedelta(minutes=i * 5),
                    "symbol": symbol,
                    "price": float(value),
                }
            )
    return pd.DataFrame(data_rows)


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Connection")
        st.text_input("Backend URL", key="base_url", placeholder=DEFAULT_BASE_URL)
        st.slider("API timeout (seconds)", min_value=3, max_value=30, key="timeout")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Test API"):
                ok, data, error, _ = api_request("GET", "/analytics/market-prices")
                if ok:
                    total = data.get("totalSecurities", "?") if isinstance(data, dict) else "?"
                    st.success(f"Connected. Securities: {total}")
                else:
                    st.error(error)
        with c2:
            if st.button("Refresh"):
                clear_caches()
                st.rerun()

        st.markdown(
            "<div class='caption'>Use the tabs to create, manage, and analyze portfolios.</div>",
            unsafe_allow_html=True,
        )


def render_dashboard_tab() -> None:
    st.subheader("Live Market Snapshot")
    ok, data, error, _ = fetch_market_prices_cache(get_base_url(), get_timeout())
    if not ok:
        st.error(error)
        return

    prices = data.get("prices", {}) if isinstance(data, dict) else {}
    timestamp = data.get("timestamp", "") if isinstance(data, dict) else ""
    total = data.get("totalSecurities", 0) if isinstance(data, dict) else 0

    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Securities", int(total))
    c2.metric("Average Price", money(float(np.mean(list(prices.values()))) if prices else 0.0))
    c3.metric("Last Update", str(timestamp).replace("T", " "))
    st.markdown("</div>", unsafe_allow_html=True)

    if not prices:
        st.info("No market prices available.")
        return

    prices_df = pd.DataFrame(
        [{"symbol": s, "currentPrice": p} for s, p in sorted(prices.items())]
    )

    col_a, col_b = st.columns([1, 2])
    with col_a:
        fig = px.bar(
            prices_df,
            x="symbol",
            y="currentPrice",
            color="currentPrice",
            color_continuous_scale=["#0f62fe", "#ff8b24"],
            title="Current Price by Symbol",
        )
        fig.update_layout(margin=dict(l=10, r=10, t=50, b=20), height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        spark_df = build_market_sparkline(prices)
        fig2 = px.line(
            spark_df,
            x="time",
            y="price",
            color="symbol",
            title="Simulated Intraday Trend (Visual Aid)",
            markers=False,
        )
        fig2.update_layout(margin=dict(l=10, r=10, t=50, b=20), height=350)
        st.plotly_chart(fig2, use_container_width=True)


def render_create_manage_tab() -> None:
    st.subheader("Create Portfolio")
    ok_market, market_data, market_error, _ = fetch_market_prices_cache(get_base_url(), get_timeout())
    prices = market_data.get("prices", {}) if ok_market and isinstance(market_data, dict) else {}

    symbols = sorted(prices.keys()) if prices else FALLBACK_SYMBOLS
    default_df = make_holdings_editor_df(symbols)

    with st.form("create_portfolio_form", clear_on_submit=False):
        owner = st.text_input("Owner name", placeholder="Alice")
        editable_df = st.data_editor(
            default_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "symbol": st.column_config.TextColumn("Symbol", required=True),
                "quantity": st.column_config.NumberColumn("Quantity", min_value=0, step=1),
                "purchasePrice": st.column_config.NumberColumn("Purchase Price", min_value=0.0, step=0.01),
            },
            key="create_holdings_editor",
        )

        submitted = st.form_submit_button("Create Portfolio")

    if submitted:
        holdings = normalize_holdings(editable_df)
        if not owner.strip():
            st.error("Owner name is required.")
        elif not holdings:
            st.error("Add at least one holding with valid quantity and purchase price.")
        else:
            payload = {"owner": owner.strip(), "holdings": holdings}
            ok, created, error, _ = api_request("POST", "/portfolios", json=payload)
            if ok:
                st.success("Portfolio created successfully.")
                st.json(created)
                clear_caches()
            else:
                st.error(error)

    st.divider()
    st.subheader("Manage Existing Portfolio")

    ok, portfolios, error, _ = fetch_portfolios_cache(get_base_url(), get_timeout())
    if not ok:
        st.error(error)
        return

    if not portfolios:
        st.info("No portfolios yet. Create one above.")
        return

    options = {portfolio_label(p): p for p in portfolios}
    selected_label = st.selectbox("Choose portfolio", list(options.keys()))
    selected = options[selected_label]

    owner_new = st.text_input("Owner", value=selected.get("owner", ""), key="manage_owner")
    holdings = selected.get("holdings", []) or []
    holdings_df = pd.DataFrame(holdings) if holdings else pd.DataFrame(columns=["symbol", "quantity", "purchasePrice"])

    edited_df = st.data_editor(
        holdings_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "symbol": st.column_config.TextColumn("Symbol", required=True),
            "quantity": st.column_config.NumberColumn("Quantity", min_value=0, step=1),
            "purchasePrice": st.column_config.NumberColumn("Purchase Price", min_value=0.0, step=0.01),
        },
        key="manage_holdings_editor",
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Changes"):
            updated_holdings = normalize_holdings(edited_df)
            payload = {"owner": owner_new.strip(), "holdings": updated_holdings}
            ok_u, updated, error_u, _ = api_request("PUT", f"/portfolios/{selected.get('id')}", json=payload)
            if ok_u:
                st.success("Portfolio updated.")
                st.json(updated)
                clear_caches()
                st.rerun()
            else:
                st.error(error_u)

    with c2:
        if st.button("Delete Portfolio"):
            ok_d, _, error_d, _ = api_request("DELETE", f"/portfolios/{selected.get('id')}")
            if ok_d:
                st.success("Portfolio deleted.")
                clear_caches()
                st.rerun()
            else:
                st.error(error_d)

    if not ok_market:
        st.warning(f"Market data not available for price hints: {market_error}")


def render_analytics_tab() -> None:
    st.subheader("Portfolio Analytics")
    ok, portfolios, error, _ = fetch_portfolios_cache(get_base_url(), get_timeout())
    if not ok:
        st.error(error)
        return

    if not portfolios:
        st.info("No portfolios available.")
        return

    options = {portfolio_label(p): p for p in portfolios}
    selected_label = st.selectbox("Select portfolio", list(options.keys()), key="analytics_portfolio_select")
    selected = options[selected_label]
    pid = selected.get("id")

    ok_a, analytics, error_a, _ = api_request("GET", f"/analytics/portfolio/{pid}")
    ok_h, holdings, error_h, _ = api_request("GET", f"/analytics/portfolio/{pid}/holdings")

    if not ok_a:
        st.error(error_a)
        return

    invested = float(analytics.get("investedValue", 0.0))
    current = float(analytics.get("currentValue", 0.0))
    pnl = float(analytics.get("profitLoss", 0.0))
    pnl_pct = float(analytics.get("profitLossPercentage", 0.0))

    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Owner", str(analytics.get("owner", "N/A")))
    c2.metric("Invested", money(invested))
    c3.metric("Current", money(current))
    c4.metric("P/L", money(pnl), pct(pnl_pct))
    st.markdown("</div>", unsafe_allow_html=True)

    prices_map = analytics.get("currentMarketPrices", {}) or {}
    prices_df = pd.DataFrame(
        [{"symbol": s, "price": p} for s, p in sorted(prices_map.items())]
    )

    col1, col2 = st.columns(2)
    with col1:
        if ok_h and holdings:
            hold_df = pd.DataFrame(holdings)
            st.dataframe(
                hold_df,
                use_container_width=True,
                hide_index=True,
            )
        elif not ok_h:
            st.warning(error_h)
        else:
            st.info("No holding analytics available.")

    with col2:
        if not prices_df.empty:
            fig = px.bar(
                prices_df,
                x="symbol",
                y="price",
                color="price",
                color_continuous_scale=["#0f62fe", "#ff8b24"],
                title="Current Market Prices",
            )
            fig.update_layout(margin=dict(l=10, r=10, t=50, b=20), height=360)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("What-If Analysis")

    symbols: List[str] = []
    defaults: Dict[str, float] = {}
    if ok_h and holdings:
        for row in holdings:
            symbol = str(row.get("symbol", "")).upper()
            if symbol:
                symbols.append(symbol)
                defaults[symbol] = float(row.get("currentMarketPrice", prices_map.get(symbol, 100.0)))
    elif prices_map:
        symbols = list(prices_map.keys())
        defaults = {k: float(v) for k, v in prices_map.items()}

    if not symbols:
        st.info("No symbols found for what-if analysis.")
        return

    hypo_prices: Dict[str, float] = {}
    with st.form("what_if_form"):
        cols = st.columns(2)
        for idx, symbol in enumerate(symbols):
            with cols[idx % 2]:
                hypo_prices[symbol] = st.number_input(
                    f"Hypothetical price for {symbol}",
                    min_value=0.01,
                    value=max(defaults.get(symbol, 100.0), 0.01),
                    step=0.25,
                    format="%.2f",
                )

        submit = st.form_submit_button("Run What-If")

    if submit:
        payload = {"hypotheticalPrices": hypo_prices}
        ok_w, what_if, error_w, _ = api_request("POST", f"/analytics/portfolio/{pid}/whatif", json=payload)

        if not ok_w:
            st.error(error_w)
            return
        
        colx, coly, colz = st.columns(3)
        colx.metric("Actual Value", money(float(what_if.get("currentValueWithActualPrices", 0.0))))
        coly.metric("Hypothetical Value", money(float(what_if.get("hypotheticalValue", 0.0))))
        colz.metric("Value Difference", money(float(what_if.get("valueDifference", 0.0))))

        cola, colb = st.columns(2)
        cola.metric(
            "Actual P/L",
            money(float(what_if.get("actualProfitLoss", 0.0))),
            pct(float(what_if.get("actualProfitLossPercentage", 0.0))),
        )
        colb.metric(
            "Hypothetical P/L",
            money(float(what_if.get("hypotheticalProfitLoss", 0.0))),
            pct(float(what_if.get("hypotheticalProfitLossPercentage", 0.0))),
        )

        comparisons = what_if.get("holdingComparisons", []) or []
        if comparisons:
            comp_df = pd.DataFrame(comparisons)
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

            if "valueDifference" in comp_df.columns and "symbol" in comp_df.columns:
                fig_diff = px.bar(
                    comp_df,
                    x="symbol",
                    y="valueDifference",
                    color="valueDifference",
                    color_continuous_scale=["#b42318", "#ff8b24", "#13795b"],
                    title="What-If Value Difference by Holding",
                )
                fig_diff.update_layout(margin=dict(l=10, r=10, t=50, b=20), height=360)
                st.plotly_chart(fig_diff, use_container_width=True)


def render_stocks_tab() -> None:
    st.subheader("Available Stocks")

    stocks_url = "http://127.0.0.1:8000/stocks"
    try:
        response = requests.get(stocks_url, timeout=get_timeout())
        if response.ok:
            stocks = response.json()

            if stocks:
                stocks_df = pd.DataFrame([
                    {
                        "Symbol": stock.get("symbol", ""),
                        "Stock Name": stock.get("short_name", ""),
                        "Market Cap": f"${stock.get('market_cap', 0):,.0f}",
                        "Website": stock.get("website", ""),
                        "Industry": stock.get("industry", ""),
                        "Exchange": stock.get("exchange", ""),
                        "Company Created": pd.to_datetime(stock.get("first_seen_at", "")).strftime("%Y-%m-%d") if stock.get("first_seen_at") else ""
                    }
                    for stock in stocks
                ])

                st.dataframe(
                    stocks_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Symbol": st.column_config.TextColumn("Symbol", width=80),
                        "Stock Name": st.column_config.TextColumn("Stock Name", width=150),
                        "Market Cap": st.column_config.TextColumn("Market Cap", width=120),
                        "Website": st.column_config.LinkColumn("Website"),
                        "Industry": st.column_config.TextColumn("Industry", width=120),
                        "Exchange": st.column_config.TextColumn("Exchange", width=100),
                        "Company Created": st.column_config.TextColumn("Company Created", width=120),
                    }
                )
            else:
                st.info("No stocks available.")
        else:
            st.error(f"Failed to fetch stocks: {response.status_code}")
    except requests.RequestException as e:
        st.error(f"Connection error: {e}")


def render_portfolio_browser_tab() -> None:
    st.subheader("Portfolio Browser")
    ok, portfolios, error, _ = fetch_portfolios_cache(get_base_url(), get_timeout())
    if not ok:
        st.error(error)
        return

    if not portfolios:
        st.info("No portfolios to display.")
        return

    for portfolio in portfolios:
        pid = portfolio.get("id")
        owner = portfolio.get("owner", "Unknown")
        holdings = portfolio.get("holdings", []) or []

        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown(f"### Portfolio #{pid} - {owner}")

        if holdings:
            hold_df = pd.DataFrame(holdings)
            cols = st.columns(2)

            with cols[0]:
                st.dataframe(hold_df, use_container_width=True, hide_index=True)

            with cols[1]:
                if "quantity" in hold_df.columns and "symbol" in hold_df.columns:
                    fig = px.pie(
                        hold_df,
                        names="symbol",
                        values="quantity",
                        title="Quantity Mix",
                    )
                    fig.update_layout(height=320)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No holdings in this portfolio.")

        st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Portfolio Insight Frontend",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "base_url" not in st.session_state:
        st.session_state.base_url = DEFAULT_BASE_URL
    if "timeout" not in st.session_state:
        st.session_state.timeout = DEFAULT_TIMEOUT

    inject_ui_styles()

    st.title("Portfolio Insight UI")
    st.caption("Create, manage, and analyze portfolios using your Spring Boot backend.")

    render_sidebar()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Dashboard", "Create / Manage", "Analytics", "Stocks", "Browse"]
    )

    with tab1:
        render_dashboard_tab()

    with tab2:
        render_create_manage_tab()

    with tab3:
        render_analytics_tab()

    with tab4:
        render_stocks_tab()

    with tab5:
        render_portfolio_browser_tab()


if __name__ == "__main__":
    main()
      