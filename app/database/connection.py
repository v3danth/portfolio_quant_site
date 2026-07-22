"""Creates database connections and initializes the schema."""

import sqlite3
from collections.abc import Generator
from importlib import import_module

from app.core.config import get_database_config
from app.database.schema import get_schema_statements


def connect_database(config: dict[str, str | int] | None = None):
    """Opens a connection to the configured database backend."""
    selected = config or get_database_config()
    if selected["backend"] == "sqlite":
        connection = sqlite3.connect(str(selected["sqlite_path"]))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
    mysql_connector = import_module("mysql.connector")
    return mysql_connector.connect(
        host=selected["host"],
        port=selected["port"],
        user=selected["user"],
        password=selected["password"],
        database=selected["name"],
    )


def initialize_database(config: dict[str, str | int] | None = None) -> None:
    """Creates all tables and indexes for the selected database."""
    selected = config or get_database_config()
    connection = connect_database(selected)
    cursor = connection.cursor()
    try:
        for statement in get_schema_statements(str(selected["backend"])):
            cursor.execute(statement)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def get_connection() -> Generator:
    """Yields a request-scoped database connection."""
    connection = connect_database()
    try:
        yield connection
    finally:
        connection.close()
