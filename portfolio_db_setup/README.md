# Portfolio Database Setup

Install dependencies:

```powershell
pip install -r .\portfolio_db_setup\requirements.txt
```

Validate the setup scripts:

```powershell
cd C:\MSDE\svedant\github\chat
.\venv\Scripts\python.exe -m py_compile .\portfolio_db_setup\db_config.py .\portfolio_db_setup\schema.py .\portfolio_db_setup\create_database.py .\portfolio_db_setup\yahoo_finance_loader.py .\portfolio_db_setup\seed_yahoo_data.py .\portfolio_db_setup\seed_top_stocks.py
```

If it prints nothing and returns to the prompt, the scripts compile successfully.

Create the MySQL database and tables:

```powershell
python .\portfolio_db_setup\create_database.py
```

Load mock stock data (recommended for development):

```powershell
python .\portfolio_db_setup\seed_mock_data.py
```

Load specific symbols with mock data:

```powershell
python .\portfolio_db_setup\seed_mock_data.py --symbols AAPL MSFT NVDA
```

Load Yahoo Finance data (requires Python < 3.13):

```powershell
python .\portfolio_db_setup\seed_yahoo_data.py --symbols AAPL MSFT GOOGL --period 1y --interval 1d
```

Load top US and India stocks:

```powershell
python .\portfolio_db_setup\seed_top_stocks.py --market all --period 10y --interval 1d
```

Load one market only:

```powershell
python .\portfolio_db_setup\seed_top_stocks.py --market us --period 10y --interval 1d
python .\portfolio_db_setup\seed_top_stocks.py --market india --period 10y --interval 1d
```

**Note:** The mock data seeder (`seed_mock_data.py`) is recommended for development as it generates realistic data without external API calls. The Yahoo Finance loader (`seed_yahoo_data.py`) has compatibility issues with Python 3.13+. If a stock has only 5 years of Yahoo history and you request `10y`, Yahoo normally returns the available 5 years and the loader inserts those rows. If Yahoo returns no data for a symbol, the loader prints `0 price rows` or `failed` and continues with the next symbol.

Defaults: `localhost`, `3306`, `root`, empty password, database `portfolio_db`.

Override defaults:

```powershell
$env:DB_PASSWORD="your_root_password"
python .\portfolio_db_setup\seed_yahoo_data.py --symbols AAPL MSFT
```
