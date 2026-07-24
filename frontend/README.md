# Streamlit Frontend

A dark-mode Streamlit dashboard for the QPMS FastAPI backend: browse/trade
stocks, manage portfolios and holdings, and view real analytics (Sharpe ratio,
volatility, drawdown, wealth index) computed from real price history.

## Files

- `api_client.py` — HTTP client; one method per backend endpoint.
- `theme.py` — dark CSS + shared Plotly dark layout/colors.
- `utils.py` — formatting helpers + analytics math (ported from
  `backend/app/services/analytics.py`).
- `app.py` — the app itself: sidebar (user/portfolio picker) + five tabs
  (Dashboard, Trade, Stocks, Analytics, Transactions).

## Run

1. Start the backend:
   ```powershell
   cd backend
   uvicorn main:app --reload
   ```
2. In a separate terminal, launch Streamlit:
   ```powershell
   streamlit run frontend/app.py
   ```
3. Open the URL Streamlit prints (defaults to http://localhost:8501).

## Configuration

Override the backend URL if it isn't running on the default address (also
editable from the app's sidebar at runtime):

```powershell
$env:API_BASE_URL="http://127.0.0.1:8000"
```
