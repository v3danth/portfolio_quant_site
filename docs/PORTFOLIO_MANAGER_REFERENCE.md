# Portfolio Manager API — Project Reference

## Overview

This project is a single-user Portfolio Management REST API built with FastAPI. It supports user and portfolio creation, holdings purchases and sales, stocks, historical prices, transactions, and portfolio performance.

SQLite is the default database. MySQL is supported through an environment flag and the `mysql-connector-python-rf` dependency.

## Stack

| Layer | Implementation |
| --- | --- |
| Backend | FastAPI |
| Default database | SQLite |
| Optional database | MySQL |
| Price source | Yahoo Finance via `yfinance` |
| Tests | `pytest` and FastAPI `TestClient` |
| API documentation | Swagger UI at `/docs` |

## Run Locally

Use the existing virtual environment on Windows:

```powershell
.\venv\Scripts\python.exe -m pytest -q
.\scripts\run_api.ps1 -Reload
```

The API is served at `http://127.0.0.1:8000`. Swagger UI is at `http://127.0.0.1:8000/docs`.

`scripts/run_api.ps1` defaults to SQLite and accepts `-SqlitePath`, `-Port`, and `-Reload`. For example:

```powershell
.\scripts\run_api.ps1 -SqlitePath data\portfolio.db -Port 8080 -Reload
```

To run against MySQL, configure `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` in the active PowerShell session, then run:

```powershell
.\scripts\run_api.ps1 -DatabaseBackend mysql -Reload
```

## Database Configuration

Configuration is read from [app/core/config.py](app/core/config.py).

### SQLite

SQLite is the default and requires no configuration.

```env
DB_BACKEND=sqlite
SQLITE_PATH=portfolio.db
```

### MySQL

Set `DB_BACKEND` to `mysql` and provide the connection settings.

```env
DB_BACKEND=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=portfolio_db
```

See [.env.example](.env.example) for all supported environment variables. Application startup creates the selected database's tables and indexes.

## Package Structure

```text
app/
├── api/
│   ├── dependencies.py          Shared database-operation helpers
│   ├── validation.py            Request validation
│   └── routes/
│       ├── health.py            Health router
│       ├── stocks.py            Stock and price router
│       └── portfolios.py        Portfolio router entry point
├── core/
│   └── config.py                Environment configuration
├── database/
│   ├── connection.py            SQLite/MySQL connection and setup
│   └── schema.py                Database schema statements
├── repositories/
│   └── portfolio.py             Persistence entry point
├── repository.py                Portfolio SQL operations
└── main.py                      FastAPI application factory

tests/
├── test_api.py                  API lifecycle tests
└── test_config.py               Database configuration tests
```

The root-level `app/config.py`, `app/db.py`, and `app/schema.py` modules are compatibility imports. New code should import from the directories shown above.

## Data Model

```text
users (1) ──< portfolios (1) ──< holdings >── stocks
                         │                    │
                         └──< transactions    └──< stock_prices
```

| Table | Purpose | Key |
| --- | --- | --- |
| `users` | Portfolio owners | `user_id` |
| `stocks` | Instrument metadata | `stock_id`, unique `symbol` |
| `portfolios` | User portfolios | `portfolio_id` |
| `holdings` | Current positions | `(portfolio_id, stock_id)` |
| `stock_prices` | OHLC price history | `(stock_id, ts, interval)` |
| `transactions` | Immutable buy and sell history | `trans_id` |

Money is stored using `NUMERIC` database columns. Holdings represent current positions and transactions preserve the audit history.

## Implemented API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | API status and selected database backend |
| `GET` | `/api/stocks` | Lists stocks with latest close prices |
| `GET` | `/api/stocks/{stock_id}` | Returns stock metadata |
| `GET` | `/api/stocks/{stock_id}/prices?interval=1d` | Returns historical prices |
| `POST` | `/api/users` | Creates a user |
| `POST` | `/api/portfolios` | Creates a portfolio for a user |
| `GET` | `/api/portfolios/{portfolio_id}/holdings` | Lists holdings and market values |
| `POST` | `/api/portfolios/{portfolio_id}/holdings` | Buys or increases a holding |
| `DELETE` | `/api/portfolios/{portfolio_id}/holdings/{stock_id}` | Sells and removes a holding |
| `GET` | `/api/portfolios/{portfolio_id}/transactions` | Returns transaction history |
| `GET` | `/api/portfolios/{portfolio_id}/performance` | Returns daily historical portfolio values |

### Request Examples

```json
POST /api/users
{
    "user_name": "Ada",
    "email": "ada@example.com"
}
```

```json
POST /api/portfolios
{
    "user_id": 1,
    "name": "Core Portfolio"
}
```

```json
POST /api/portfolios/1/holdings
{
    "symbol": "AAPL",
    "quantity": 10,
    "price": 192.35
}
```

Buying an existing symbol increases quantity and recalculates the weighted average purchase price. Every buy and sell is recorded in `transactions`.

## Validation and Tests

- `user_name` and `symbol` are required non-empty strings.
- `user_id` is an integer.
- `quantity` and `price` are positive numbers.
- Missing resources return HTTP `404`.
- Invalid payloads return HTTP `422`.

Run tests using the existing virtual environment:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

The current suite covers configuration selection, modular router registration, the full holding lifecycle, transaction creation, and invalid quantity rejection.

## Next Steps

1. Add a Yahoo Finance ingestion command using the existing loader modules.
2. Add migrations for controlled schema evolution.
3. Add typed request and response models.
4. Add authentication before supporting multiple users.
5. Build the web frontend and performance chart.