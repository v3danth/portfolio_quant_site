"""Validates request payload values."""

from fastapi import HTTPException, status


def get_required_text(payload: dict, field: str) -> str:
    """Returns a required non-empty text field."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{field} is required.")
    return value.strip()


def get_positive_number(payload: dict, field: str) -> float:
    """Returns a required positive numeric field."""
    value = payload.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{field} must be greater than zero.")
    return float(value)


def get_integer(payload: dict, field: str) -> int:
    """Returns a required integer field."""
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{field} must be an integer.")
    return value


def get_optional_text(payload: dict, field: str) -> str | None:
    """Returns an optional text field."""
    value = payload.get(field)
    if value is not None and not isinstance(value, str):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{field} must be a string.")
    return value
