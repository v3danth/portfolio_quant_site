# QPMS Backend (FastAPI)

Modular FastAPI backend for the Quantitative Portfolio Management System.

## Structure

```text
backend/
├── main.py                    # entry point (uvicorn main:app)
└── app/
    ├── __init__.py            # create_app() + router registration
    ├── config.py              # env-based settings (DB creds)
    ├── database.py            # MySQL connection pool + query/DataFrame helpers
    ├── models/                # SQL queries / data-access layer
    │   ├── user.py
    │   └── stock.py           # incl. DataFrame/Series price helpers
    ├── schemas/               # Pydantic request/response models
    │   ├── user.py
    │   └── stock.py
    ├── services/              # business logic / computations
    │   └── analytics.py       # returns, volatility, Sharpe, drawdown
    └── routers/               # API route modules
        ├── users.py
        └── stocks.py
```

Separation of concerns:

- `routers/` — HTTP layer (paths, status codes, validation).
- `schemas/` — Pydantic I/O contracts.
- `models/` — raw SQL and DB access only (dicts, DataFrames, Series).
- `services/` — pure computation on pandas data (see docs/MATH_SPECS.md).

## Run

```powershell
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload
```

Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Config (env vars)

`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

## Endpoints (implemented)

| Method | Path                                         | Purpose                          |
|--------|----------------------------------------------|----------------------------------|
| GET    | `/api/v1/users`                              | List users                       |
| GET    | `/api/v1/users/{id}`                         | Get user (name + balance)        |
| GET    | `/api/v1/stocks`                             | List stocks (search/sector/page) |
| GET    | `/api/v1/stocks/{id}`                        | Full stock detail                |
| GET    | `/api/v1/stocks/{id}/prices`                 | OHLC price history               |
| GET    | `/api/v1/stocks/{id}/quote`                  | Latest live price                |
| POST   | `/api/v1/stocks/prices/refresh`              | Fetch live quotes, override today's candles |
| GET    | `/api/v1/portfolios?userId=`                 | List a user's portfolios         |
| POST   | `/api/v1/portfolios`                         | Create a portfolio               |
| GET    | `/api/v1/portfolios/{id}`                    | Get a portfolio                  |
| DELETE | `/api/v1/portfolios/{id}`                    | Delete a portfolio               |
| GET    | `/api/v1/portfolios/{id}/holdings`           | Browse holdings (live value)     |
| POST   | `/api/v1/portfolios/{id}/holdings`           | Buy / add a stock                |
| DELETE | `/api/v1/portfolios/{id}/holdings/{stockId}` | Sell / remove a stock            |
| GET    | `/api/v1/stocks/{id}/pnl`                    | Single-stock P&L (unrealized + realized) |
| GET    | `/api/v1/portfolios/{id}/pnl`                | Portfolio P&L with per-holding breakdown |
| GET    | `/api/v1/portfolios/{id}/allocation/by-quote-type` | Holdings count per quote_type (pie chart) |
| GET    | `/api/v1/portfolios/{id}/allocation/by-sector`     | Holdings count per sector (pie chart)    |
| GET    | `/api/v1/portfolios/performers`                    | Top & worst current holding per portfolio |
| GET    | `/api/v1/portfolios/risk`                          | Risk metrics (vol, Sharpe, drawdown, VaR, beta) per portfolio |
| GET    | `/api/v1/alerts?userId=`                          | List a user's alerts + unread count + per-portfolio health scores |
| POST   | `/api/v1/alerts/check?userId=&sendEmail=`         | Run a risk/health alert check now (persists new alerts, optional email) |
| POST   | `/api/v1/alerts/{alertId}/read`                   | Mark an alert as read (idempotent) |
| GET    | `/health`                                    | Health check                     |

## Analytics service

`app/services/analytics.py` computes profit & loss using `Decimal` math:

- **Unrealized P&L** = `(current price - avg buy price) * quantity` for open
  holdings.
- **Realized P&L** = weighted-average cost simulation over the transaction
  history, so `avg_buy_price` stays consistent with `app/models/holding.py`.

Data access lives in `app/models/analytics.py`; the endpoints are in
`app/routers/analytics.py` (`/stocks/{id}/pnl` and `/portfolios/{id}/pnl`).

## Adding a new module (e.g. stocks)

1. `app/schemas/stock.py` — Pydantic models.
2. `app/models/stock.py` — SQL queries.
3. `app/routers/stocks.py` — `APIRouter(prefix="/stocks", ...)`.
4. Register in `app/__init__.py`: `app.include_router(stocks.router, prefix="/api/v1")`.
