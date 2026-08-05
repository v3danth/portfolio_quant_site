"""Risk alerting, health scoring and email notifications.

Everything here is pure logic over the risk payload produced by
``app/services/analytics.build_portfolio_risk`` plus thin DB persistence via
``app/models/alerts``.

Health score (0-100) is a weighted composite of five risk sub-scores:

    sharpe_ratio            25%   >= 2.0 -> 100, <= -1.0 -> 0
    annualized_volatility   20%   <= 0.15 -> 100, >= 0.60 -> 0
    max_drawdown            20%   >= -0.05 -> 100, <= -0.50 -> 0
    value_at_risk_95        20%   <= 0.015 -> 100, >= 0.060 -> 0
    beta                    15%   0.7-1.3 -> 100, outside 0.3-1.7 -> 0

Missing metrics (e.g. no benchmark so beta is null) are simply dropped and
the remaining weights are renormalized. Bands: >= 80 Healthy, 60-79 Fair,
< 60 Abnormal.
"""
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Optional

import pandas as pd

from app.config import settings
from app.models import alerts as alerts_model
from app.models import analytics as analytics_model
from app.models import portfolio as portfolio_model
from app.models import stock as stock_model
from app.models import user as user_model
from app.services import analytics as analytics_service

# --- Health score weights & bands -----------------------------------------

HEALTH_WEIGHTS = {
    "sharpe_ratio": 0.25,
    "annualized_volatility": 0.20,
    "max_drawdown": 0.20,
    "value_at_risk_95": 0.20,
    "beta": 0.15,
}

BAND_HEALTHY = "Healthy"
BAND_FAIR = "Fair"
BAND_ABNORMAL = "Abnormal"

_SEVERITY_ORDER = {"warning": 1, "critical": 2}

# --- Hardcoded thresholds --------------------------------------------------

_PERCENT_METRICS = {"annualized_volatility", "max_drawdown", "value_at_risk_95"}

_RISK_RULES = [
    {"metric": "annualized_volatility", "op": ">", "threshold": 0.60, "severity": "critical",
     "message": "Annualized volatility is {value}, above the 60% critical threshold"},
    {"metric": "annualized_volatility", "op": ">", "threshold": 0.40, "severity": "warning",
     "message": "Annualized volatility is {value}, above the 40% warning threshold"},
    {"metric": "max_drawdown", "op": "<", "threshold": -0.35, "severity": "critical",
     "message": "Max drawdown is {value}, below the -35% critical threshold"},
    {"metric": "max_drawdown", "op": "<", "threshold": -0.20, "severity": "warning",
     "message": "Max drawdown is {value}, below the -20% warning threshold"},
    {"metric": "value_at_risk_95", "op": ">", "threshold": 0.05, "severity": "critical",
     "message": "95% daily VaR is {value}, above the 5% critical threshold"},
    {"metric": "value_at_risk_95", "op": ">", "threshold": 0.03, "severity": "warning",
     "message": "95% daily VaR is {value}, above the 3% warning threshold"},
    {"metric": "sharpe_ratio", "op": "<", "threshold": 0.0, "severity": "warning",
     "message": "Sharpe ratio is {value}, below 0 - poor risk-adjusted returns"},
    {"metric": "beta", "op": ">", "threshold": 1.5, "severity": "warning",
     "message": "Portfolio beta is {value}, above 1.5 - highly sensitive to the market"},
]

_HEALTH_RULES = [
    {"metric": "health_score", "op": "<", "threshold": 40.0, "severity": "critical",
     "message": "Portfolio health score is {value}, below the 40 critical threshold"},
    {"metric": "health_score", "op": "<", "threshold": 60.0, "severity": "warning",
     "message": "Portfolio health score is {value}, below the 60 warning threshold"},
]

# --- Health score components ----------------------------------------------

def sharpe_score(value: Optional[float]) -> Optional[float]:
    """Sharpe >= 2.0 scores 100; <= -1.0 scores 0; linear in between."""
    if value is None:
        return None
    if value >= 2.0:
        return 100.0
    if value <= -1.0:
        return 0.0
    return (value + 1.0) / 3.0 * 100.0


def volatility_score(value: Optional[float]) -> Optional[float]:
    """Vol <= 0.15 scores 100; >= 0.60 scores 0; linear in between."""
    if value is None:
        return None
    if value <= 0.15:
        return 100.0
    if value >= 0.60:
        return 0.0
    return (0.60 - value) / 0.45 * 100.0


def drawdown_score(value: Optional[float]) -> Optional[float]:
    """Drawdown >= -0.05 scores 100; <= -0.50 scores 0; linear in between."""
    if value is None:
        return None
    if value >= -0.05:
        return 100.0
    if value <= -0.50:
        return 0.0
    return (value + 0.50) / 0.45 * 100.0


def var_score(value: Optional[float]) -> Optional[float]:
    """95% VaR <= 0.015 scores 100; >= 0.060 scores 0; linear in between."""
    if value is None:
        return None
    if value <= 0.015:
        return 100.0
    if value >= 0.060:
        return 0.0
    return (0.060 - value) / 0.045 * 100.0


def beta_score(value: Optional[float]) -> Optional[float]:
    """Beta in 0.7-1.3 scores 100; outside 0.3-1.7 scores 0; linear edges."""
    if value is None:
        return None
    if 0.7 <= value <= 1.3:
        return 100.0
    if value <= 0.3 or value >= 1.7:
        return 0.0
    if value < 0.7:
        return (value - 0.3) / 0.4 * 100.0
    return (1.7 - value) / 0.4 * 100.0


_HEALTH_COMPONENTS = {
    "sharpe_ratio": sharpe_score,
    "annualized_volatility": volatility_score,
    "max_drawdown": drawdown_score,
    "value_at_risk_95": var_score,
    "beta": beta_score,
}


def band_for(score: float) -> str:
    """Map a health score to its label band."""
    if score >= 80:
        return BAND_HEALTHY
    if score >= 60:
        return BAND_FAIR
    return BAND_ABNORMAL


def build_health_score(metrics: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Composite 0-100 score from a risk metrics dict.

    Returns ``{score, band, components}`` where components is the per-metric
    sub-score (0-100). Missing metrics are dropped and weights renormalized.
    Returns None when no metric is priceable.
    """
    if not metrics:
        return None
    components: dict[str, float] = {}
    weighted: list[tuple[float, float]] = []
    for metric, fn in _HEALTH_COMPONENTS.items():
        score = fn(metrics.get(metric))
        if score is not None:
            components[metric] = round(score, 1)
            weighted.append((HEALTH_WEIGHTS[metric], score))
    if not weighted:
        return None
    total_weight = sum(weight for weight, _ in weighted)
    composite = sum(weight * score for weight, score in weighted) / total_weight
    return {
        "score": round(composite, 1),
        "band": band_for(composite),
        "components": components,
    }

# --- Alert evaluation ------------------------------------------------------

def _format_value(metric: str, value: float) -> str:
    if metric in _PERCENT_METRICS:
        return f"{value * 100:.2f}%"
    return f"{value:.2f}"


def _build_alert(
    rule: dict[str, Any],
    category: str,
    portfolio_id: int,
    user_id: int,
    observed: float,
) -> dict[str, Any]:
    return {
        "portfolio_id": portfolio_id,
        "user_id": user_id,
        "category": category,
        "severity": rule["severity"],
        "metric": rule["metric"],
        "observed_value": observed,
        "threshold": rule["threshold"],
        "message": rule["message"].format(value=_format_value(rule["metric"], observed)),
    }


def _add_or_upgrade(
    alerts: list[dict[str, Any]],
    rule: dict[str, Any],
    category: str,
    portfolio_id: int,
    user_id: int,
    observed: float,
) -> None:
    """Append an alert, replacing a lower-severity one for the same metric."""
    existing = next((alert for alert in alerts if alert["metric"] == rule["metric"]), None)
    if existing is not None and _SEVERITY_ORDER[rule["severity"]] <= _SEVERITY_ORDER[existing["severity"]]:
        return
    if existing is not None:
        alerts.remove(existing)
    alerts.append(_build_alert(rule, category, portfolio_id, user_id, observed))


def evaluate_metrics(
    metrics: dict[str, Any],
    portfolio_id: int,
    user_id: int,
) -> list[dict[str, Any]]:
    """Flag risk metrics that crossed a hardcoded threshold.

    Only the most severe matching rule is emitted per metric, so a drawdown of
    -40% produces a single critical alert rather than a warning too.
    """
    alerts: list[dict[str, Any]] = []
    for rule in _RISK_RULES:
        observed = metrics.get(rule["metric"])
        if observed is None:
            continue
        matched = observed < rule["threshold"] if rule["op"] == "<" else observed > rule["threshold"]
        if matched:
            _add_or_upgrade(alerts, rule, "risk", portfolio_id, user_id, observed)
    return alerts


def evaluate_health(
    health_score: float,
    portfolio_id: int,
    user_id: int,
) -> list[dict[str, Any]]:
    """Flag a composite health score that fell below a band threshold."""
    alerts: list[dict[str, Any]] = []
    for rule in _HEALTH_RULES:
        if health_score < rule["threshold"]:
            _add_or_upgrade(alerts, rule, "health", portfolio_id, user_id, health_score)
    return alerts

# --- Email ------------------------------------------------------------------

def smtp_configured() -> bool:
    """True when SMTP credentials are present so email alerts are possible."""
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_alert_email(to_email: str, alerts: list[dict[str, Any]]) -> bool:
    """Send a summary email listing generated alerts.

    Raises on failure so the caller can log it. Email alerts are only sent
    when SMTP is configured in the environment.
    """
    if not smtp_configured():
        return False
    lines = [
        f"{a['severity'].upper()} | {a['category']} | {a['metric']}: {a['message']}"
        for a in alerts
    ]
    body = (
        "Your portfolio monitoring detected the following abnormal conditions:\n\n"
        + "\n".join(lines)
        + "\n\nThis is an automated alert from the QPMS system."
    )
    message = EmailMessage()
    message["Subject"] = f"QPMS Alert: {len(alerts)} abnormal condition(s) detected"
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)
    return True

# --- Orchestration ----------------------------------------------------------

def _load_benchmark(benchmark_symbol: str) -> pd.Series:
    benchmark_stock = stock_model.get_stock_by_symbol(benchmark_symbol)
    if benchmark_stock is None:
        return pd.Series(dtype="float64")
    return stock_model.get_close_series(benchmark_stock["stock_id"])


def _iter_portfolio_risk(
    user_id: int,
    lookback_days: int = 252,
    benchmark_symbol: str = "SPY",
    risk_free_rate: float = 0.0,
):
    """Yield (portfolio_row, risk_payload) for every portfolio of a user."""
    benchmark_close = _load_benchmark(benchmark_symbol)
    for portfolio in portfolio_model.get_portfolios_by_user(user_id):
        portfolio_id = portfolio["portfolio_id"]
        holdings = analytics_model.get_portfolio_holdings(portfolio_id)
        adj_closes, closes = analytics_model.get_portfolio_price_frames(portfolio_id)
        risk = analytics_service.build_portfolio_risk(
            portfolio_id,
            holdings,
            adj_closes,
            closes,
            benchmark_close=benchmark_close,
            benchmark_symbol=benchmark_symbol,
            lookback_days=lookback_days,
            risk_free_rate=risk_free_rate,
        )
        yield portfolio, risk


def _health_row(
    portfolio: dict[str, Any],
    risk: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Build a ``{score, band, components}`` row for a portfolio, or None if
    no metric could be scored."""
    metrics = risk.get("metrics")
    health = build_health_score(metrics)
    if health is None:
        return None
    return {
        "portfolio_id": portfolio["portfolio_id"],
        "name": portfolio.get("name"),
        "metrics": metrics,
        **health,
    }


def compute_health_scores(
    user_id: int,
    lookback_days: int = 252,
    benchmark_symbol: str = "SPY",
    risk_free_rate: float = 0.0,
) -> list[dict[str, Any]]:
    """Current composite health score for each of the user's portfolios."""
    rows: list[dict[str, Any]] = []
    for portfolio, risk in _iter_portfolio_risk(user_id, lookback_days, benchmark_symbol, risk_free_rate):
        row = _health_row(portfolio, risk)
        if row is not None:
            rows.append(row)
    return rows


def run_alert_check(
    user_id: int,
    send_email: bool = False,
    email_existing: bool = False,
    lookback_days: int = 252,
    benchmark_symbol: str = "SPY",
    risk_free_rate: float = 0.0,
) -> dict[str, Any]:
    """Evaluate every portfolio of a user, persist new alerts, optionally email.

    Deduplication: an alert is skipped when one for the same portfolio +
    category + metric was created in the last 24 hours (read state ignored, so a
    persistent condition re-alerts at most ~once a day).

    Args:
        send_email: attempt to email the alerts generated by this run.
        email_existing: when send_email is True but this run created no new
            alerts, email the user's currently-pending unread alerts instead.
            Both the manual "check & send now" endpoint and the periodic
            background task pass True, so anything missed gets emailed and the
            sent alerts are then marked read.
    """
    user = user_model.get_user_by_id(user_id)
    if user is None:
        return {
            "user_id": user_id,
            "portfolios_checked": 0,
            "alerts_created": 0,
            "emailed": False,
            "emails_sent": 0,
            "checked_at": datetime.now(timezone.utc),
            "alerts": [],
            "health_scores": [],
        }

    created: list[dict[str, Any]] = []
    health_scores: list[dict[str, Any]] = []
    portfolios_checked = 0

    for portfolio, risk in _iter_portfolio_risk(user_id, lookback_days, benchmark_symbol, risk_free_rate):
        portfolio_id = portfolio["portfolio_id"]
        portfolios_checked += 1
        metrics = risk.get("metrics") or {}

        row = _health_row(portfolio, risk)
        if row is not None:
            health_scores.append(row)

        pending = evaluate_metrics(metrics, portfolio_id, user_id)
        if row is not None:
            pending += evaluate_health(row["score"], portfolio_id, user_id)

        for alert in pending:
            if alerts_model.has_active_alert(user_id, portfolio_id, alert["category"], alert["metric"]):
                continue
            stored = alerts_model.get_alert(alerts_model.insert_alert(alert))
            created.append(stored)

    emailed = False
    emails_sent = 0
    if send_email and smtp_configured():
        to_email = (user.get("email") or "").strip()
        alerts_to_email = created
        if not alerts_to_email and email_existing:
            alerts_to_email = alerts_model.list_alerts(user_id, unread_only=True, limit=100)
        if alerts_to_email and to_email:
            try:
                send_alert_email(to_email, alerts_to_email)
                emailed = True
                emails_sent = 1
                # Emailing the alert counts as acknowledgement: mark them read
                # so the dashboard has no pending alerts left.
                for alert in alerts_to_email:
                    if alert.get("alert_id"):
                        alerts_model.mark_read(alert["alert_id"])
                        alert["is_read"] = True
            except Exception:
                logging.exception("Failed to email alerts to %s", to_email)

    return {
        "user_id": user_id,
        "portfolios_checked": portfolios_checked,
        "alerts_created": len(created),
        "emailed": emailed,
        "emails_sent": emails_sent,
        "checked_at": datetime.now(timezone.utc),
        "alerts": created,
        "health_scores": health_scores,
    }


def run_alert_check_for_all_users(send_email: bool = True) -> list[dict[str, Any]]:
    """Run the alert check for every user (used by the periodic background task).

    Behaves like the manual ``sendEmail=true`` trigger: emails the alerts created
    this run, and if none were created falls back to emailing any still-pending
    unread alerts so nothing missed gets left un-notified.
    """
    results: list[dict[str, Any]] = []
    for user in user_model.get_all_users():
        try:
            results.append(run_alert_check(int(user["user_id"]), send_email=send_email, email_existing=True))
        except Exception:
            logging.exception("Alert check failed for user %s", user.get("user_id"))
    return results
