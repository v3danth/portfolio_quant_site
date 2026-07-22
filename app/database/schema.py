"""Defines database-specific portfolio table creation statements."""


def get_schema_statements(backend: str) -> list[str]:
    """Returns idempotent schema statements for the selected database."""
    identifier = "INTEGER PRIMARY KEY AUTOINCREMENT" if backend == "sqlite" else "BIGINT AUTO_INCREMENT PRIMARY KEY"
    timestamp = "CURRENT_TIMESTAMP"
    return [
        f"""CREATE TABLE IF NOT EXISTS users (
            user_id {identifier},
            user_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE,
            bank_details VARCHAR(255),
            acct_balance NUMERIC(18, 2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT {timestamp}
        )""",
        f"""CREATE TABLE IF NOT EXISTS stocks (
            stock_id {identifier},
            symbol VARCHAR(20) NOT NULL UNIQUE,
            exchange VARCHAR(50),
            quote_type VARCHAR(50),
            short_name TEXT,
            long_name TEXT,
            currency VARCHAR(10),
            country VARCHAR(50),
            sector VARCHAR(100),
            industry VARCHAR(150),
            website TEXT,
            business_summary TEXT,
            market_cap BIGINT,
            shares_outstanding BIGINT,
            first_seen_at TIMESTAMP NOT NULL DEFAULT {timestamp},
            updated_at TIMESTAMP NOT NULL DEFAULT {timestamp}
        )""",
        f"""CREATE TABLE IF NOT EXISTS portfolios (
            portfolio_id {identifier},
            user_id BIGINT NOT NULL,
            name VARCHAR(100) NOT NULL DEFAULT 'My Portfolio',
            created_at TIMESTAMP NOT NULL DEFAULT {timestamp},
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS holdings (
            portfolio_id BIGINT NOT NULL,
            stock_id BIGINT NOT NULL,
            quantity NUMERIC(18, 6) NOT NULL DEFAULT 0,
            avg_buy_price NUMERIC(18, 6),
            updated_at TIMESTAMP NOT NULL DEFAULT {timestamp},
            PRIMARY KEY (portfolio_id, stock_id),
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
            FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS stock_prices (
            stock_id BIGINT NOT NULL,
            ts TIMESTAMP NOT NULL,
            interval VARCHAR(10) NOT NULL,
            open NUMERIC(18, 6) NOT NULL,
            high NUMERIC(18, 6) NOT NULL,
            low NUMERIC(18, 6) NOT NULL,
            close NUMERIC(18, 6) NOT NULL,
            adj_close NUMERIC(18, 6),
            volume BIGINT,
            dividend NUMERIC(18, 6),
            stock_split NUMERIC(18, 6),
            source VARCHAR(50) DEFAULT 'yahoo_finance',
            ingested_at TIMESTAMP NOT NULL DEFAULT {timestamp},
            PRIMARY KEY (stock_id, ts, interval),
            FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS transactions (
            trans_id {identifier},
            portfolio_id BIGINT NOT NULL,
            stock_id BIGINT,
            trans_type VARCHAR(20) NOT NULL,
            quantity NUMERIC(18, 6),
            price NUMERIC(18, 6),
            amount NUMERIC(18, 2),
            trans_details VARCHAR(255),
            ts TIMESTAMP NOT NULL DEFAULT {timestamp},
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
            FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_prices_stock_ts ON stock_prices (stock_id, ts)",
        "CREATE INDEX IF NOT EXISTS idx_txn_portfolio_ts ON transactions (portfolio_id, ts)",
        "CREATE INDEX IF NOT EXISTS idx_holdings_stock ON holdings (stock_id)",
    ]
