"""Application entry point.

Run with:
    uvicorn app:app --reload
or:
    python app.py
"""
import uvicorn
from app import create_app

app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
import sys
from pathlib import Path

# Allow importing db_config/db.py from portfolio_db_setup
sys.path.append(str(Path(__file__).resolve().parent.parent / "portfolio_db_setup"))

from fastapi import Depends, FastAPI, HTTPException
from mysql.connector import Error as MySQLError

from db import connect_database
from schemas import Stock

app = FastAPI(
    title="Portfolio Management API",
    description="Backend API for the portfolio quant site, serving data from MySQL to the Streamlit UI.",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",
)


@app.get("/health", tags=["Health"])
def health():
    """Basic health-check endpoint returning OK."""
    return {"status": "ok"}


def get_db():
    """Yield a MySQL connection for the duration of a request, then close it."""
    connection = connect_database()
    try:
        yield connection
    finally:
        connection.close()


def fetch_all(db, query, params=None):
    """Run a SELECT and return all rows as dicts, raising a 500 on DB errors."""
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except MySQLError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")


# ---- Stocks ----

@app.get("/stocks", response_model=list[Stock], tags=["Stocks"])
def get_stocks(db=Depends(get_db)):
    """Return all rows from the stocks table."""
    return fetch_all(db, "SELECT * FROM stocks")
