"""Application configuration pulled from environment variables."""
import os


class Settings:
    """Database and app settings (env-overridable)."""

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "n3u3da!")
    DB_NAME: str = os.getenv("DB_NAME", "portfolio_db")
    PRICE_REFRESH_INTERVAL_SECONDS: int = int(os.getenv("PRICE_REFRESH_INTERVAL_SECONDS", "120"))


settings = Settings()
