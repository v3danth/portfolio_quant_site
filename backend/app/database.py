"""MySQL connection pooling and helpers."""
from contextlib import contextmanager
from typing import Any, Optional

import mysql.connector
import pandas as pd
from app.config import settings
from mysql.connector import pooling

_pool: Optional[pooling.MySQLConnectionPool] = None


def _get_pool() -> pooling.MySQLConnectionPool:
    """Lazily create a single shared connection pool."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="qpms_pool",
            pool_size=5,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
        )
    return _pool


@contextmanager
def get_cursor(dictionary: bool = True, commit: bool = False):
    """Yield a cursor from a pooled connection, handling cleanup.

    Args:
        dictionary: return rows as dicts instead of tuples.
        commit: commit the transaction on successful exit.
    """
    connection = _get_pool().get_connection()
    cursor = connection.cursor(dictionary=dictionary)
    try:
        yield cursor
        if commit:
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def fetch_one(query: str, params: tuple = ()) -> Optional[dict[str, Any]]:
    """Run a SELECT and return a single row (or None)."""
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def fetch_all(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Run a SELECT and return all rows."""
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def fetch_df(query: str, params: tuple = (), index: Optional[str] = None) -> pd.DataFrame:
    """Run a SELECT and return a pandas DataFrame.

    Args:
        query: SQL SELECT statement.
        params: query parameters.
        index: optional column to set as the DataFrame index (e.g. "ts").
    """
    with get_cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description] if cursor.description else []

    df = pd.DataFrame(rows, columns=columns)
    if index and index in df.columns:
        df = df.set_index(index)
    return df


def execute(query: str, params: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return the affected row count."""
    with get_cursor(commit=True) as cursor:
        cursor.execute(query, params)
        return cursor.rowcount


def insert(query: str, params: tuple = ()) -> int:
    """Run an INSERT and return the new auto-increment id."""
    with get_cursor(commit=True) as cursor:
        cursor.execute(query, params)
        return cursor.lastrowid
