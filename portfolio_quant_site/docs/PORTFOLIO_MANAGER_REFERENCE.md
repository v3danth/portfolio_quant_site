# Portfolio Manager — Project Reference (Go-To File)

> Single source of truth for the Portfolio Management REST API training project.
> Covers: goals, tech plan, data model, SQL schema, API design, and a phased build plan.

---

## 1. Project Overview

Build a **Portfolio Management REST API** (with a simple web front end) that lets a
single user:

1. Browse a portfolio
2. View portfolio performance (ideally graphically)
3. Add items to the portfolio
4. Remove items from the portfolio

**Assumptions**
- No authentication, single user.
- Live/historic prices come from Yahoo Finance.
- Persistence via MySQL database.
- FastAPI backend with Streamlit frontend for UI.
- Use Git properly: branches + pull requests.
- Document the API (Swagger/OpenAPI if covered).

**Golden rule:** START SMALL. Get `id + symbol + quantity` working end-to-end
before adding complexity.

---

## 2. Technical Goals & Stack

| Layer      | Implementation                                   |
|------------|--------------------------------------------------|
| Backend    | Python (FastAPI)                                 |
| Database   | MySQL                                            |
| Frontend   | Streamlit                                        |
| Docs       | Swagger / OpenAPI                                |
| Prices     | Yahoo Finance (yfinance in Python)               |

---

## 3. Data Model — Design Notes

Key design principles:

1. **Store instrument metadata once** in `stocks` and reference by `stock_id`
   everywhere else. Never duplicate names/symbols across tables.
2. **Portfolio holdings ≠ transactions.** Keep a `holdings` table for *current*
   positions and a `transactions` table for *history* (buy/sell/deposit).
3. **Prices belong in their own table** keyed by `(stock_id, ts, interval)`.
4. **Live price** can be read from the most recent `stock_prices` row, or cached
   for convenience (see note below).
5. **Store money carefully** — use `NUMERIC(18,6)`, never `FLOAT`.

**Entity relationships**

```
users (1) ─────────< portfolios (1) ─────< holdings >──── stocks
                                   │                        │
                                   └──< transactions        └──< stock_prices
```

---

## 4. SQL Schema

```sql
-- =========================================================
-- USERS
-- =========================================================
CREATE TABLE users (
    user_id       BIGSERIAL PRIMARY KEY,
    user_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(255) UNIQUE,
    bank_details  VARCHAR(255),          -- keep minimal for a training project
    acct_balance  NUMERIC(18,2) NOT NULL DEFAULT 0,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- STOCKS  (reference/master data — enriched from Yahoo Finance)
-- =========================================================
CREATE TABLE stocks (
    stock_id            BIGSERIAL PRIMARY KEY,
    symbol              VARCHAR(20) NOT NULL UNIQUE,   -- e.g. AAPL
    exchange            VARCHAR(50),                   -- NASDAQ, NSE, etc
    quote_type          VARCHAR(50),                   -- EQUITY, ETF, etc
    short_name          TEXT,
    long_name           TEXT,
    currency            VARCHAR(10),
    country             VARCHAR(50),
    sector              VARCHAR(100),
    industry            VARCHAR(150),
    website             TEXT,
    business_summary    TEXT,

    market_cap          BIGINT,
    shares_outstanding  BIGINT,

    first_seen_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- PORTFOLIOS  (a user can have one or many)
-- =========================================================
CREATE TABLE portfolios (
    portfolio_id  BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(user_id),
    name          VARCHAR(100) NOT NULL DEFAULT 'My Portfolio',
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- HOLDINGS  (CURRENT positions — one row per stock per portfolio)
-- =========================================================
CREATE TABLE holdings (
    portfolio_id  BIGINT NOT NULL REFERENCES portfolios(portfolio_id),
    stock_id      BIGINT NOT NULL REFERENCES stocks(stock_id),
    quantity      NUMERIC(18,6) NOT NULL DEFAULT 0,
    avg_buy_price NUMERIC(18,6),                 -- optional: for P&L
    updated_at    TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (portfolio_id, stock_id)
);

-- =========================================================
-- STOCK_PRICES  (historic + intraday candles from Yahoo Finance)
-- =========================================================
CREATE TABLE stock_prices (
    stock_id      BIGINT NOT NULL REFERENCES stocks(stock_id),
    ts            TIMESTAMP NOT NULL,            -- candle timestamp
    interval      VARCHAR(10) NOT NULL,          -- 1d, 1h, 5m, etc

    open          NUMERIC(18,6) NOT NULL,
    high          NUMERIC(18,6) NOT NULL,
    low           NUMERIC(18,6) NOT NULL,
    close         NUMERIC(18,6) NOT NULL,
    adj_close     NUMERIC(18,6),
    volume        BIGINT,

    dividend      NUMERIC(18,6),
    stock_split   NUMERIC(18,6),

    source        VARCHAR(50) DEFAULT 'yahoo_finance',
    ingested_at   TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (stock_id, ts, interval)
);

-- =========================================================
-- TRANSACTIONS  (immutable history of everything that happened)
-- =========================================================
CREATE TABLE transactions (
    trans_id      BIGSERIAL PRIMARY KEY,
    portfolio_id  BIGINT NOT NULL REFERENCES portfolios(portfolio_id),
    stock_id      BIGINT REFERENCES stocks(stock_id),   -- NULL for cash moves
    trans_type    VARCHAR(20) NOT NULL,   -- BUY, SELL, DEPOSIT, WITHDRAW, DIVIDEND
    quantity      NUMERIC(18,6),
    price         NUMERIC(18,6),          -- price per unit at trade time
    amount        NUMERIC(18,2),          -- total cash impact
    trans_details VARCHAR(255),
    ts            TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- Helpful indexes
-- =========================================================
CREATE INDEX idx_prices_stock_ts   ON stock_prices (stock_id, ts DESC);
CREATE INDEX idx_txn_portfolio_ts  ON transactions (portfolio_id, ts DESC);
CREATE INDEX idx_holdings_stock    ON holdings (stock_id);
CREATE INDEX idx_stocks_symbol     ON stocks (symbol);
```

---

## 5. Table Summary (Quick Reference)

| Table          | Purpose                                | Key                         |
|----------------|----------------------------------------|-----------------------------|
| `users`        | Single user + cash balance             | `user_id`                   |
| `stocks`       | Master instrument data (Yahoo-enriched)| `stock_id` (`symbol` uniq)  |
| `portfolios`   | Groups holdings for a user             | `portfolio_id`              |
| `holdings`     | **Current** positions                  | `(portfolio_id, stock_id)`  |
| `stock_prices` | Historic/intraday OHLC candles         | `(stock_id, ts, interval)`  |
| `transactions` | **History** of buys/sells/cash         | `trans_id`                  |

---

## 6. REST API Design

Prioritise the front-end needs (browse → view → add → remove).

| Method | Endpoint                                   | Purpose                          |
|--------|--------------------------------------------|----------------------------------|
| GET    | `/api/portfolios/{id}/holdings`            | Browse portfolio (P1)            |
| GET    | `/api/portfolios/{id}/performance`         | Value over time for charts (P2)  |
| POST   | `/api/portfolios/{id}/holdings`            | Add / buy a stock (P3)           |
| DELETE | `/api/portfolios/{id}/holdings/{stockId}`  | Remove / sell a stock (P4)       |
| GET    | `/api/stocks`                              | List known stocks                |
| GET    | `/api/stocks/{id}`                         | Stock detail (sector, summary…)  |
| GET    | `/api/stocks/{id}/prices?interval=1d`      | Price history for a stock        |
| GET    | `/api/portfolios/{id}/transactions`        | Transaction history              |

**Sample "add holding" request**
```json
POST /api/portfolios/1/holdings
{
  "symbol": "AAPL",
  "quantity": 10,
  "price": 192.35
}
```

**Sample "holding" response**
```json
{
  "symbol": "AAPL",
  "shortName": "Apple Inc.",
  "quantity": 10,
  "priceLive": 195.10,
  "marketValue": 1951.00
}
```

---

## 7. Phased Build Plan

### Phase 0 — Setup
- [ ] Create Git repo + branch strategy (`main` + feature branches + PRs)
- [ ] Skeleton backend project + connect to DB
- [ ] Create `stocks` + `holdings` tables only

### Phase 1 — Minimal Working System (MVP)
- [ ] `GET /holdings` and `POST /holdings`
- [ ] Store `id, symbol, quantity, purchase_date`
- [ ] Verify end-to-end with Postman

### Phase 2 — Prices & Performance
- [ ] Add `stock_prices` table
- [ ] Yahoo Finance ingestion script (also enriches `stocks` metadata)
- [ ] `GET /stocks/{id}/prices`
- [ ] Compute portfolio market value

### Phase 3 — Transactions & Cash
- [ ] Add `users`, `portfolios`, `transactions`
- [ ] BUY/SELL update holdings + balance
- [ ] Transaction history endpoint (tracks all buy/sell activity for ROI calculation)

### Phase 4 — Frontend (Streamlit)
- [ ] Browse portfolio table (collection of stocks)
- [ ] Performance chart
- [ ] Add / remove UI
- [ ] Display holdings with current stocks and purchase dates
- [ ] Show ROI calculations based on transaction history

### Phase 5 — Polish
- [ ] Swagger docs
- [ ] Error handling & validation
- [ ] Tests
- [ ] Prep presentation demo

### Key Concepts
- **Portfolio**: A collection of stocks owned by a user
- **Holdings**: Current positions in the portfolio, including purchase date for each stock
- **Transactions**: Immutable history of all buy/sell activity; used to calculate returns when the same stock is bought and sold multiple times at different prices/quantities

---

## 8. Key Decisions to Remember

- **Money:** always `NUMERIC`, never floating point.
- **No duplicated names:** join to `stocks` for names/descriptions.
- **Holdings = now, Transactions = history.** Never mix them.
- **`stocks` is Yahoo-enriched:** `updated_at` tracks last metadata refresh;
  `first_seen_at` tracks when the symbol was first added.
- **Live price:** read latest `stock_prices` row (or cache if you prefer).
- **Stay Agile:** the biggest risk is an over-complex data model on day one.

