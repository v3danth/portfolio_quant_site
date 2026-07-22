"""Provides compatibility imports for database connections."""

from app.database.connection import (connect_database, get_connection,
                                     initialize_database)

__all__ = ["connect_database", "get_connection", "initialize_database"]
