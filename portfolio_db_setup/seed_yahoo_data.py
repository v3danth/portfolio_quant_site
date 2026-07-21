import argparse
import logging

from create_database import setup_database
from db import connect_database
from yahoo_finance_loader import load_symbol

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def parse_args():
    """Read command line options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "GOOGL", "AMZN"])
    parser.add_argument("--period", default="1y")
    parser.add_argument("--interval", default="1d")
    return parser.parse_args()


def seed_yahoo_data(symbols, period, interval):
    """Seed stocks and prices from Yahoo Finance."""
    logging.info("Setting up database")
    setup_database()
    connection = connect_database()
    logging.info("Connected to database")
    try:
        for symbol in symbols:
            logging.info("Loading symbol: %s", symbol)
            try:
                loaded_symbol, row_count = load_symbol(connection, symbol, period, interval)
                logging.info("Loaded %s: %d rows", loaded_symbol, row_count)
            except Exception as exc:
                logging.error("%s: failed (%s)", symbol.upper(), exc)
    finally:
        connection.close()
        logging.info("Database connection closed")


if __name__ == "__main__":
    args = parse_args()
    logging.info("Seeding data for symbols: %s", ", ".join(args.symbols))
    seed_yahoo_data(args.symbols, args.period, args.interval)
    logging.info("Seeding completed successfully")