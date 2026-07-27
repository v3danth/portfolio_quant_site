"""Thin HTTP client for the QPMS FastAPI backend.

One method per endpoint actually registered in ``backend/app/__init__.py``.
Every method raises ``APIError`` on network failure or a non-2xx response so
callers only ever need to catch one exception type.
"""
import os
from typing import Any, Optional

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


class APIError(RuntimeError):
    """Raised when the backend cannot be reached or returns an error."""


class ApiClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=10.0)

    def close(self) -> None:
        self.client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self.client.request(method, path, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("detail", exc.response.text)
            except ValueError:
                detail = exc.response.text or str(exc)
            raise APIError(str(detail)) from exc
        except httpx.RequestError as exc:
            raise APIError(f"Unable to reach backend at {self.base_url}: {exc}") from exc

        if not response.content:
            return None
        return response.json()

    # --- Meta ---------------------------------------------------------

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    # --- Users ----------------------------------------------------------

    def list_users(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/users")

    def get_user(self, user_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/users/{user_id}")

    # --- Portfolios -------------------------------------------------------

    def list_portfolios(self, user_id: int) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/portfolios", params={"userId": user_id})

    def get_portfolio(self, portfolio_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/portfolios/{portfolio_id}")

    def create_portfolio(self, user_id: int, name: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/portfolios",
            json={"user_id": user_id, "name": name},
        )

    def delete_portfolio(self, portfolio_id: int) -> None:
        self._request("DELETE", f"/api/v1/portfolios/{portfolio_id}")

    # --- Holdings ---------------------------------------------------------

    def list_holdings(self, portfolio_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/portfolios/{portfolio_id}/holdings")

    def buy_stock(
        self, portfolio_id: int, symbol: str, quantity: float, price: Optional[float] = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"symbol": symbol, "quantity": quantity}
        if price is not None and price > 0:
            payload["price"] = price
        return self._request("POST", f"/api/v1/portfolios/{portfolio_id}/holdings", json=payload)

    def sell_stock(
        self,
        portfolio_id: int,
        stock_id: int,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if quantity is not None:
            params["quantity"] = quantity
        if price is not None and price > 0:
            params["price"] = price
        return self._request(
            "DELETE", f"/api/v1/portfolios/{portfolio_id}/holdings/{stock_id}", params=params
        )

    # --- Stocks -------------------------------------------------------

    def list_stocks(
        self,
        search: Optional[str] = None,
        sector: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if search:
            params["search"] = search
        if sector:
            params["sector"] = sector
        return self._request("GET", "/api/v1/stocks", params=params)

    def get_stock(self, stock_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/stocks/{stock_id}")

    def get_stock_prices(self, stock_id: int, interval: str = "1d") -> list[dict[str, Any]]:
        return self._request(
            "GET", f"/api/v1/stocks/{stock_id}/prices", params={"interval": interval}
        )

    def get_stock_quote(self, stock_id: int) -> Optional[dict[str, Any]]:
        try:
            return self._request("GET", f"/api/v1/stocks/{stock_id}/quote")
        except APIError:
            return None

    # --- Transactions -------------------------------------------------------

    def list_transactions(
        self,
        portfolio_id: int,
        trans_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        if "limit" in kwargs:
            limit = kwargs.pop("limit")
        if "offset" in kwargs:
            offset = kwargs.pop("offset")
        if kwargs:
            unexpected = ", ".join(sorted(kwargs.keys()))
            raise TypeError(f"Unexpected keyword argument(s): {unexpected}")

        params: dict[str, Any] = {"limit": 100 if limit is None else limit, "offset": 0 if offset is None else offset}
        if trans_type:
            params["transType"] = trans_type
        return self._request(
            "GET", f"/api/v1/portfolios/{portfolio_id}/transactions", params=params
        )
