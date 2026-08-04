"""Generates docs/schema_diagram.png from SQL/create_tables.sql (portfolio_db).

Run once to (re)produce the picture; not part of the app runtime.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

HEADER_BG = "#2f4f6f"
HEADER_FG = "#ffffff"
BODY_BG = "#f4f7fa"
BORDER = "#22344a"
PK_COLOR = "#b3541e"
FK_COLOR = "#2f6f4f"
LINE_COLOR = "#5a6b7a"
ROW_H = 0.34
HEADER_H = 0.44
PAD = 0.18

TABLES = {
    "users": {
        "pos": (0.6, 8.6),
        "cols": [
            ("user_id", "BIGINT", "PK"),
            ("user_name", "VARCHAR(100)", ""),
            ("email", "VARCHAR(255) UNIQUE", ""),
            ("bank_details", "VARCHAR(255)", ""),
            ("acct_balance", "NUMERIC(18,2)", ""),
            ("created_at", "TIMESTAMP", ""),
        ],
    },
    "stocks": {
        "pos": (10.6, 7.6),
        "cols": [
            ("stock_id", "BIGINT", "PK"),
            ("symbol", "VARCHAR(20) UNIQUE", ""),
            ("exchange", "VARCHAR(50)", ""),
            ("quote_type", "VARCHAR(50)", ""),
            ("short_name / long_name", "TEXT", ""),
            ("currency / country", "VARCHAR", ""),
            ("sector / industry", "VARCHAR", ""),
            ("website / business_summary", "TEXT", ""),
            ("market_cap", "BIGINT", ""),
            ("shares_outstanding", "BIGINT", ""),
            ("first_seen_at / updated_at", "TIMESTAMP", ""),
        ],
    },
    "portfolios": {
        "pos": (0.6, 5.5),
        "cols": [
            ("portfolio_id", "BIGINT", "PK"),
            ("user_id", "BIGINT", "FK"),
            ("name", "VARCHAR(100)", ""),
            ("created_at", "TIMESTAMP", ""),
        ],
    },
    "stock_prices": {
        "pos": (10.6, 3.6),
        "cols": [
            ("stock_id", "BIGINT", "PK, FK"),
            ("ts", "TIMESTAMP", "PK"),
            ("interval", "VARCHAR(10)", "PK"),
            ("open / high / low / close", "NUMERIC(18,6)", ""),
            ("adj_close", "NUMERIC(18,6)", ""),
            ("volume", "BIGINT", ""),
            ("dividend / stock_split", "NUMERIC(18,6)", ""),
            ("source", "VARCHAR(50)", ""),
            ("ingested_at", "TIMESTAMP", ""),
        ],
    },
    "holdings": {
        "pos": (0.6, 1.6),
        "cols": [
            ("portfolio_id", "BIGINT", "PK, FK"),
            ("stock_id", "BIGINT", "PK, FK"),
            ("quantity", "NUMERIC(18,6)", ""),
            ("avg_buy_price", "NUMERIC(18,6)", ""),
            ("updated_at", "TIMESTAMP", ""),
        ],
    },
    "transactions": {
        "pos": (5.6, 0.6),
        "cols": [
            ("trans_id", "BIGINT", "PK"),
            ("portfolio_id", "BIGINT", "FK"),
            ("stock_id", "BIGINT", "FK (nullable)"),
            ("trans_type", "VARCHAR(20)", ""),
            ("quantity / price", "NUMERIC(18,6)", ""),
            ("amount", "NUMERIC(18,2)", ""),
            ("trans_details", "VARCHAR(255)", ""),
            ("ts", "TIMESTAMP", ""),
        ],
    },
}

TABLE_W = 4.1

fig, ax = plt.subplots(figsize=(16, 11))
ax.set_xlim(0, 16)
ax.set_ylim(0, 11)
ax.axis("off")
fig.patch.set_facecolor("white")

ax.text(8, 10.6, "portfolio_db — schema", ha="center", va="center",
        fontsize=18, fontweight="bold", color="#1c2b3a", family="sans-serif")

boxes = {}

def draw_table(name, spec):
    x, y_top = spec["pos"]
    cols = spec["cols"]
    h = HEADER_H + ROW_H * len(cols) + PAD
    y = y_top - h

    body = FancyBboxPatch((x, y), TABLE_W, h,
                           boxstyle="round,pad=0,rounding_size=0.08",
                           linewidth=1.4, edgecolor=BORDER, facecolor=BODY_BG, zorder=2)
    ax.add_patch(body)

    header = FancyBboxPatch((x, y_top - HEADER_H), TABLE_W, HEADER_H,
                             boxstyle="round,pad=0,rounding_size=0.08",
                             linewidth=1.4, edgecolor=BORDER, facecolor=HEADER_BG, zorder=3)
    ax.add_patch(header)
    ax.text(x + TABLE_W / 2, y_top - HEADER_H / 2, name, ha="center", va="center",
            fontsize=12.5, fontweight="bold", color=HEADER_FG, family="monospace", zorder=4)

    row_y = y_top - HEADER_H - ROW_H / 2 - PAD / 2
    for col_name, col_type, key in cols:
        if "PK" in key:
            label_color = PK_COLOR
            weight = "bold"
        elif "FK" in key:
            label_color = FK_COLOR
            weight = "normal"
        else:
            label_color = "#1c2b3a"
            weight = "normal"
        ax.text(x + 0.18, row_y, col_name, ha="left", va="center",
                fontsize=9.5, color=label_color, fontweight=weight, family="monospace", zorder=4)
        ax.text(x + TABLE_W - 0.12, row_y, col_type, ha="right", va="center",
                fontsize=8, color="#5a6b7a", style="italic", family="monospace", zorder=4)
        if key:
            ax.text(x + TABLE_W - 0.12, row_y + ROW_H * 0.42, key, ha="right", va="center",
                    fontsize=6.8, color=label_color, fontweight="bold", family="monospace", zorder=4)
        row_y -= ROW_H

    boxes[name] = (x, y, TABLE_W, h, y_top)

for name, spec in TABLES.items():
    draw_table(name, spec)

def edge(src, dst, src_side, dst_side, label):
    sx, sy, sw, sh, sytop = boxes[src]
    dx, dy, dw, dh, dytop = boxes[dst]
    points = {
        "left": (sx, (sy + sytop) / 2),
        "right": (sx + sw, (sy + sytop) / 2),
        "top": (sx + sw / 2, sytop),
        "bottom": (sx + sw / 2, sy),
    }
    dpoints = {
        "left": (dx, (dy + dytop) / 2),
        "right": (dx + dw, (dy + dytop) / 2),
        "top": (dx + dw / 2, dytop),
        "bottom": (dx + dw / 2, dy),
    }
    p1 = points[src_side]
    p2 = dpoints[dst_side]
    arrow = FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=14,
                             color=LINE_COLOR, linewidth=1.5, zorder=1,
                             connectionstyle="arc3,rad=0.08")
    ax.add_patch(arrow)
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    ax.text(mx, my + 0.12, label, ha="center", va="center", fontsize=8,
            color="#1c2b3a", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85), zorder=5)

edge("users", "portfolios", "bottom", "top", "1 : N\n(user_id)")
edge("portfolios", "holdings", "bottom", "top", "1 : N\n(portfolio_id)")
edge("portfolios", "transactions", "bottom", "top", "1 : N\n(portfolio_id)")
edge("stocks", "stock_prices", "bottom", "top", "1 : N\n(stock_id)")
edge("stocks", "holdings", "left", "right", "1 : N\n(stock_id)")
edge("stocks", "transactions", "bottom", "right", "1 : N\n(stock_id, nullable)")

legend_elements = [
    Line2D([0], [0], marker="s", color="none", markerfacecolor=PK_COLOR, markersize=10, label="Primary key"),
    Line2D([0], [0], marker="s", color="none", markerfacecolor=FK_COLOR, markersize=10, label="Foreign key"),
]
ax.legend(handles=legend_elements, loc="lower right", frameon=False, fontsize=9,
          bbox_to_anchor=(0.995, 0.01))

plt.tight_layout()
out_path = __file__.replace("_gen_schema_diagram.py", "schema_diagram.png")
plt.savefig(out_path, dpi=180, facecolor="white", bbox_inches="tight")
print(f"Saved {out_path}")
