"""Executes persistence operations for portfolio resources."""

from decimal import Decimal


def get_placeholder(backend: str) -> str:
    """Returns the parameter marker supported by the selected backend."""
    return "?" if backend == "sqlite" else "%s"


def to_serializable(value):
    """Converts database values to JSON-compatible primitive values."""
    if isinstance(value, Decimal):
        return float(value)
    return value


def row_to_dict(cursor, row) -> dict | None:
    """Converts a database result row into a serializable dictionary."""
    if row is None:
        return None
    if hasattr(row, "keys"):
        return {key: to_serializable(row[key]) for key in row.keys()}
    return {column[0]: to_serializable(value) for column, value in zip(cursor.description, row)}


def fetch_all(cursor) -> list[dict]:
    """Returns all cursor rows as serializable dictionaries."""
    return [row_to_dict(cursor, row) for row in cursor.fetchall()]


def fetch_stocks(connection) -> list[dict]:
    """Returns all stocks with their latest available closing price."""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT s.stock_id, s.symbol, s.short_name, s.sector, s.industry, s.market_cap,
                   p.close AS latest_close, p.ts AS price_timestamp
            FROM stocks s
            LEFT JOIN stock_prices p ON p.stock_id = s.stock_id
                AND p.ts = (SELECT MAX(p2.ts) FROM stock_prices p2 WHERE p2.stock_id = s.stock_id)
            ORDER BY s.symbol
        """)
        return fetch_all(cursor)
    finally:
        cursor.close()


def create_user(connection, backend: str, user_name: str, email: str | None) -> dict:
    """Creates a user and returns its identifier."""
    marker = get_placeholder(backend)
    cursor = connection.cursor()
    try:
        cursor.execute(f"INSERT INTO users (user_name, email) VALUES ({marker}, {marker})", (user_name, email))
        connection.commit()
        return {"user_id": cursor.lastrowid, "user_name": user_name, "email": email}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def create_portfolio(connection, backend: str, user_id: int, name: str) -> dict:
    """Creates a portfolio for an existing user."""
    marker = get_placeholder(backend)
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT user_id FROM users WHERE user_id = {marker}", (user_id,))
        if cursor.fetchone() is None:
            raise LookupError("User not found.")
        cursor.execute(f"INSERT INTO portfolios (user_id, name) VALUES ({marker}, {marker})", (user_id, name))
        connection.commit()
        return {"portfolio_id": cursor.lastrowid, "user_id": user_id, "name": name}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def fetch_stock(connection, stock_id: int) -> dict | None:
    """Returns one stock by its identifier."""
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * FROM stocks WHERE stock_id = {get_placeholder('sqlite' if hasattr(connection, 'execute') else 'mysql')}", (stock_id,))
        return row_to_dict(cursor, cursor.fetchone())
    finally:
        cursor.close()


def fetch_prices(connection, stock_id: int, interval: str) -> list[dict]:
    """Returns ordered historical price records for one stock."""
    marker = get_placeholder("sqlite" if hasattr(connection, "execute") else "mysql")
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * FROM stock_prices WHERE stock_id = {marker} AND interval = {marker} ORDER BY ts", (stock_id, interval))
        return fetch_all(cursor)
    finally:
        cursor.close()


def fetch_holdings(connection, portfolio_id: int) -> list[dict]:
    """Returns holdings valued using each stock's latest closing price."""
    marker = get_placeholder("sqlite" if hasattr(connection, "execute") else "mysql")
    cursor = connection.cursor()
    try:
        cursor.execute(f"""
            SELECT h.portfolio_id, h.stock_id, s.symbol, s.short_name, h.quantity, h.avg_buy_price,
                   p.close AS price_live, h.quantity * COALESCE(p.close, 0) AS market_value
            FROM holdings h
            JOIN stocks s ON s.stock_id = h.stock_id
            LEFT JOIN stock_prices p ON p.stock_id = h.stock_id
                AND p.ts = (SELECT MAX(p2.ts) FROM stock_prices p2 WHERE p2.stock_id = h.stock_id)
            WHERE h.portfolio_id = {marker}
            ORDER BY s.symbol
        """, (portfolio_id,))
        return fetch_all(cursor)
    finally:
        cursor.close()


def fetch_portfolio(connection, portfolio_id: int) -> dict | None:
    """Returns one portfolio by its identifier."""
    marker = get_placeholder("sqlite" if hasattr(connection, "execute") else "mysql")
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * FROM portfolios WHERE portfolio_id = {marker}", (portfolio_id,))
        return row_to_dict(cursor, cursor.fetchone())
    finally:
        cursor.close()


def find_stock_by_symbol(cursor, symbol: str, marker: str) -> dict | None:
    """Returns a stock record matching an uppercase symbol."""
    cursor.execute(f"SELECT stock_id, symbol FROM stocks WHERE symbol = {marker}", (symbol.upper(),))
    return row_to_dict(cursor, cursor.fetchone())


def create_stock(cursor, symbol: str, marker: str) -> int:
    """Creates a minimally defined stock and returns its identifier."""
    cursor.execute(f"INSERT INTO stocks (symbol) VALUES ({marker})", (symbol.upper(),))
    return cursor.lastrowid


def create_holding(connection, backend: str, portfolio_id: int, symbol: str, quantity: float, price: float) -> dict:
    """Creates or increases a holding and records its buy transaction."""
    marker = get_placeholder(backend)
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT portfolio_id FROM portfolios WHERE portfolio_id = {marker}", (portfolio_id,))
        if cursor.fetchone() is None:
            raise LookupError("Portfolio not found.")
        stock = find_stock_by_symbol(cursor, symbol, marker)
        stock_id = stock["stock_id"] if stock else create_stock(cursor, symbol, marker)
        cursor.execute(f"SELECT quantity, avg_buy_price FROM holdings WHERE portfolio_id = {marker} AND stock_id = {marker}", (portfolio_id, stock_id))
        holding = row_to_dict(cursor, cursor.fetchone())
        existing_quantity = float(holding["quantity"]) if holding else 0.0
        existing_price = float(holding["avg_buy_price"] or 0) if holding else 0.0
        total_quantity = existing_quantity + quantity
        average_price = ((existing_quantity * existing_price) + (quantity * price)) / total_quantity
        if holding:
            cursor.execute(f"UPDATE holdings SET quantity = {marker}, avg_buy_price = {marker}, updated_at = CURRENT_TIMESTAMP WHERE portfolio_id = {marker} AND stock_id = {marker}", (total_quantity, average_price, portfolio_id, stock_id))
        else:
            cursor.execute(f"INSERT INTO holdings (portfolio_id, stock_id, quantity, avg_buy_price) VALUES ({marker}, {marker}, {marker}, {marker})", (portfolio_id, stock_id, quantity, price))
        cursor.execute(f"INSERT INTO transactions (portfolio_id, stock_id, trans_type, quantity, price, amount) VALUES ({marker}, {marker}, 'BUY', {marker}, {marker}, {marker})", (portfolio_id, stock_id, quantity, price, quantity * price))
        connection.commit()
        return {"portfolio_id": portfolio_id, "stock_id": stock_id, "symbol": symbol.upper(), "quantity": total_quantity, "avg_buy_price": average_price}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def delete_holding(connection, backend: str, portfolio_id: int, stock_id: int) -> bool:
    """Deletes a holding and records its sale at the latest closing price."""
    marker = get_placeholder(backend)
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT quantity FROM holdings WHERE portfolio_id = {marker} AND stock_id = {marker}", (portfolio_id, stock_id))
        holding = row_to_dict(cursor, cursor.fetchone())
        if holding is None:
            return False
        cursor.execute(f"SELECT close FROM stock_prices WHERE stock_id = {marker} ORDER BY ts DESC LIMIT 1", (stock_id,))
        price_row = row_to_dict(cursor, cursor.fetchone())
        price = float(price_row["close"]) if price_row else 0.0
        quantity = float(holding["quantity"])
        cursor.execute(f"DELETE FROM holdings WHERE portfolio_id = {marker} AND stock_id = {marker}", (portfolio_id, stock_id))
        cursor.execute(f"INSERT INTO transactions (portfolio_id, stock_id, trans_type, quantity, price, amount) VALUES ({marker}, {marker}, 'SELL', {marker}, {marker}, {marker})", (portfolio_id, stock_id, quantity, price, quantity * price))
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def fetch_transactions(connection, portfolio_id: int) -> list[dict]:
    """Returns transaction history in reverse chronological order."""
    marker = get_placeholder("sqlite" if hasattr(connection, "execute") else "mysql")
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * FROM transactions WHERE portfolio_id = {marker} ORDER BY ts DESC, trans_id DESC", (portfolio_id,))
        return fetch_all(cursor)
    finally:
        cursor.close()


def fetch_performance(connection, portfolio_id: int) -> list[dict]:
    """Returns historical portfolio value based on current holding quantities."""
    marker = get_placeholder("sqlite" if hasattr(connection, "execute") else "mysql")
    cursor = connection.cursor()
    try:
        cursor.execute(f"""
            SELECT p.ts, SUM(h.quantity * p.close) AS market_value
            FROM holdings h
            JOIN stock_prices p ON p.stock_id = h.stock_id
            WHERE h.portfolio_id = {marker} AND p.interval = '1d'
            GROUP BY p.ts
            ORDER BY p.ts
        """, (portfolio_id,))
        return fetch_all(cursor)
    finally:
        cursor.close()
