"""Reads application configuration from environment variables."""

from os import getenv

SUPPORTED_DATABASES = {"sqlite", "mysql"}


def get_database_config() -> dict[str, str | int]:
    """Returns the selected database connection configuration."""
    backend = getenv("DB_BACKEND", "sqlite").lower()
    if backend not in SUPPORTED_DATABASES:
        raise ValueError("DB_BACKEND must be either 'sqlite' or 'mysql'.")
    return {
        "backend": backend,
        "sqlite_path": getenv("SQLITE_PATH", "portfolio.db"),
        "host": getenv("DB_HOST", "localhost"),
        "port": int(getenv("DB_PORT", "3306")),
        "user": getenv("DB_USER", "root"),
        "password": getenv("DB_PASSWORD", ""),
        "name": getenv("DB_NAME", "portfolio_db"),
    }
