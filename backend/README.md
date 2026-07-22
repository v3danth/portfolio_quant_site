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

| Method | Path                             | Purpose                          |
|--------|----------------------------------|----------------------------------|
| GET    | `/api/v1/users`                  | List users                       |
| GET    | `/api/v1/users/{id}`             | Get user (name + balance)        |
| GET    | `/api/v1/stocks`                 | List stocks (search/sector/page) |
| GET    | `/api/v1/stocks/{id}`            | Full stock detail                |
| GET    | `/api/v1/stocks/{id}/prices`     | OHLC price history               |
| GET    | `/api/v1/stocks/{id}/quote`      | Latest live price                |
| GET    | `/health`                        | Health check                     |

## Analytics service

`app/services/analytics.py` implements the formulas in `docs/MATH_SPECS.md`
(returns, annualised volatility, Sharpe ratio, wealth index, drawdown) on the
pandas Series returned by `app/models/stock.py:get_close_series`.

## Adding a new module (e.g. stocks)

1. `app/schemas/stock.py` — Pydantic models.
2. `app/models/stock.py` — SQL queries.
3. `app/routers/stocks.py` — `APIRouter(prefix="/stocks", ...)`.
4. Register in `app/__init__.py`: `app.include_router(stocks.router, prefix="/api/v1")`.
