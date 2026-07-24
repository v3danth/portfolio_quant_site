"""Dark-mode styling shared across the app: CSS injection + chart colors."""
import streamlit as st

# Validated dark-mode categorical palette (CVD-safe adjacent pairs).
CHART_COLORS = [
    "#3987e5",  # blue
    "#d95926",  # orange
    "#199e70",  # aqua
    "#c98500",  # yellow
    "#d55181",  # magenta
    "#008300",  # green
    "#9085e9",  # violet
    "#e66767",  # red
]

SURFACE = "#0f172a"
PAGE_BG = "#020617"
GRIDLINE = "#1e293b"
INK_PRIMARY = "#f8fafc"
INK_MUTED = "#94a3b8"
GOOD = "#22c55e"
BAD = "#ef4444"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=INK_PRIMARY, family="system-ui, -apple-system, 'Segoe UI', sans-serif"),
    xaxis=dict(gridcolor=GRIDLINE, zerolinecolor=GRIDLINE, linecolor=GRIDLINE),
    yaxis=dict(gridcolor=GRIDLINE, zerolinecolor=GRIDLINE, linecolor=GRIDLINE),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=10, r=10, t=40, b=10),
)


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        :root {{ color-scheme: dark; }}
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, {PAGE_BG} 0%, #111827 100%);
            color: {INK_PRIMARY};
        }}
        [data-testid="stSidebar"] {{
            background: {PAGE_BG};
            border-right: 1px solid {GRIDLINE};
        }}
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div,
        .stTextArea > div > div > textarea {{
            background-color: {SURFACE};
            color: {INK_PRIMARY};
        }}
        [data-testid="stMetric"] {{
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid {GRIDLINE};
            border-radius: 12px;
            padding: 0.75rem 1rem;
        }}
        .block-container {{ padding-top: 1.2rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
