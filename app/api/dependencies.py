"""Provides shared API dependencies."""

from collections.abc import Callable
from typing import TypeVar

from app.core.config import get_database_config
from app.database.connection import connect_database

Result = TypeVar("Result")


def get_backend() -> str:
    """Returns the configured database backend."""
    return str(get_database_config()["backend"])


def with_connection(operation: Callable[[object], Result]) -> Result:
    """Runs an operation using a short-lived database connection."""
    connection = connect_database()
    try:
        return operation(connection)
    finally:
        connection.close()
