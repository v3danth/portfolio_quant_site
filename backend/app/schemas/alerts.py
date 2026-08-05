"""Alert request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.analytics import RiskMetrics


class AlertOut(BaseModel):
    """A single generated alert."""

    alert_id: int
    portfolio_id: Optional[int] = None
    user_id: int
    category: str  # "risk" | "health"
    severity: str  # "warning" | "critical"
    metric: str
    observed_value: Optional[float] = None
    threshold: Optional[float] = None
    message: str
    is_read: bool
    created_at: datetime


class HealthScoreOut(BaseModel):
    """Composite 0-100 portfolio health score plus its sub-scores."""

    portfolio_id: int
    name: Optional[str] = None
    score: float
    band: str  # "Healthy" | "Fair" | "Abnormal"
    components: dict[str, float]
    metrics: Optional[RiskMetrics] = None


class AlertsListResponse(BaseModel):
    """Alerts page payload: the alert rows plus unread count and health scores."""

    alerts: list[AlertOut]
    unread_count: int
    health_scores: list[HealthScoreOut]


class CheckResult(BaseModel):
    """Outcome of running an alert check for a user."""

    user_id: int
    portfolios_checked: int
    alerts_created: int
    emailed: bool
    emails_sent: int
    checked_at: datetime
    alerts: list[AlertOut]
    health_scores: list[HealthScoreOut]


class ReadResult(BaseModel):
    """Confirmation that an alert was marked as read."""

    alert_id: int
    is_read: bool
