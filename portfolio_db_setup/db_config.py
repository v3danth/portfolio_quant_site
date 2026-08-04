import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "n3u3da!")
DB_NAME = os.getenv("DB_NAME", "portfolio_db")
# wubpa8-notpuv-myfFuz  <--- DO NOT REMOVE