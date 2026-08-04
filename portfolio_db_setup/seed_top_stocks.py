import argparse

from seed_yahoo_data import seed_yahoo_data
from stocks import TOP_50_US, TOP_50_INDIA


def parse_args():
    """Read top stock load options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["us", "india", "all"], default="all")
    parser.add_argument("--period", default="1y")
    parser.add_argument("--interval", default="1d")
    return parser.parse_args()


def select_symbols(market):
    """Return symbols for the selected market."""
    if market == "us":
        return TOP_50_US
    if market == "india":
        return TOP_50_INDIA
    return TOP_50_US + TOP_50_INDIA


if __name__ == "__main__":
    args = parse_args()
    seed_yahoo_data(select_symbols(args.market), args.period, args.interval)