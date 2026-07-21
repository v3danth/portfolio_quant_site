import argparse

from seed_yahoo_data import seed_yahoo_data

TOP_50_US = [
    "NVDA",
    "MSFT",
    "AAPL",
    "AMZN",
    "GOOGL",
    "GOOG",
    "META",
    "AVGO",
    "TSLA",
    "BRK-B",
    "JPM",
    "WMT",
    "LLY",
    "V",
    "ORCL",
    "MA",
    "NFLX",
    "XOM",
    "COST",
    "JNJ",
    "HD",
    "PG",
    "ABBV",
    "BAC",
    "PLTR",
    "KO",
    "PM",
    "GE",
    "CSCO",
    "CRM",
    "CVX",
    "IBM",
    "WFC",
    "ABT",
    "LIN",
    "MCD",
    "NOW",
    "ISRG",
    "DIS",
    "AMD",
    "MRK",
    "ACN",
    "T",
    "GS",
    "INTU",
    "TXN",
    "VZ",
    "PEP",
    "QCOM",
    "ADBE",
]

TOP_50_INDIA = [
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "APOLLOHOSP.NS",
    "ASIANPAINT.NS",
    "AXISBANK.NS",
    "BAJAJ-AUTO.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "BEL.NS",
    "BHARTIARTL.NS",
    "BPCL.NS",
    "BRITANNIA.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "DRREDDY.NS",
    "EICHERMOT.NS",
    "GRASIM.NS",
    "HCLTECH.NS",
    "HDFCBANK.NS",
    "HDFCLIFE.NS",
    "HEROMOTOCO.NS",
    "HINDALCO.NS",
    "HINDUNILVR.NS",
    "ICICIBANK.NS",
    "INDUSINDBK.NS",
    "INFY.NS",
    "ITC.NS",
    "JSWSTEEL.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "M&M.NS",
    "MARUTI.NS",
    "NESTLEIND.NS",
    "NTPC.NS",
    "ONGC.NS",
    "POWERGRID.NS",
    "RELIANCE.NS",
    "SBILIFE.NS",
    "SBIN.NS",
    "SHRIRAMFIN.NS",
    "SUNPHARMA.NS",
    "TATACONSUM.NS",
    "TATAMOTORS.NS",
    "TATASTEEL.NS",
    "TCS.NS",
    "TECHM.NS",
    "TITAN.NS",
    "TRENT.NS",
    "ULTRACEMCO.NS",
    "WIPRO.NS",
]


def parse_args():
    """Read top stock load options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["us", "india", "all"], default="all")
    parser.add_argument("--period", default="10y")
    parser.add_argument("--interval", default="1m")
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