"""Unit tests for the alert service (health scoring + threshold evaluation).

These are pure-function tests; no database is touched.
"""
import pytest

from app.services import alerts as alert_service


# --- Health score components -------------------------------------------------

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2.0, 100.0),
        (0.0, pytest.approx(33.33, abs=0.01)),
        (-1.0, 0.0),
        (-3.0, 0.0),
        (1.0, pytest.approx(66.67, abs=0.01)),
    ],
)
def test_sharpe_score(value, expected):
    assert alert_service.sharpe_score(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.15, 100.0),
        (0.30, pytest.approx(66.67, abs=0.01)),
        (0.60, 0.0),
        (0.90, 0.0),
    ],
)
def test_volatility_score(value, expected):
    assert alert_service.volatility_score(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-0.05, 100.0),
        (-0.25, pytest.approx(55.56, abs=0.01)),
        (-0.50, 0.0),
        (-0.80, 0.0),
    ],
)
def test_drawdown_score(value, expected):
    assert alert_service.drawdown_score(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.015, 100.0),
        (0.035, pytest.approx(55.56, abs=0.01)),
        (0.060, 0.0),
        (0.10, 0.0),
    ],
)
def test_var_score(value, expected):
    assert alert_service.var_score(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.7, 100.0),
        (1.3, 100.0),
        (0.5, pytest.approx(50.0, abs=0.01)),
        (1.5, pytest.approx(50.0, abs=0.01)),
        (0.3, 0.0),
        (1.7, 0.0),
        (2.5, 0.0),
    ],
)
def test_beta_score(value, expected):
    assert alert_service.beta_score(value) == expected


# --- Composite health score ---------------------------------------------------

HEALTHY_METRICS = {
    "annualized_return": 0.25,
    "annualized_volatility": 0.15,
    "sharpe_ratio": 2.0,
    "max_drawdown": -0.05,
    "value_at_risk_95": 0.015,
    "value_at_risk_99": 0.04,
    "beta": 1.0,
}

BAD_METRICS = {
    "annualized_volatility": 0.70,
    "sharpe_ratio": -1.5,
    "max_drawdown": -0.60,
    "value_at_risk_95": 0.08,
    "beta": 2.0,
}


def test_health_score_healthy_portfolio_scores_100():
    health = alert_service.build_health_score(HEALTHY_METRICS)
    assert health["score"] == 100.0
    assert health["band"] == alert_service.BAND_HEALTHY
    assert set(health["components"]) == set(alert_service.HEALTH_WEIGHTS)


def test_health_score_abnormal_portfolio_scores_zero():
    health = alert_service.build_health_score(BAD_METRICS)
    assert health["score"] == 0.0
    assert health["band"] == alert_service.BAND_ABNORMAL


def test_health_score_renormalizes_when_beta_missing():
    metrics = dict(HEALTHY_METRICS)
    metrics.pop("beta")
    health = alert_service.build_health_score(metrics)
    assert health["score"] == 100.0
    assert "beta" not in health["components"]


def test_health_score_none_when_no_metrics():
    assert alert_service.build_health_score(None) is None
    assert alert_service.build_health_score({}) is None
    assert (
        alert_service.build_health_score(
            {
                "annualized_return": None,
                "annualized_volatility": None,
                "sharpe_ratio": None,
                "max_drawdown": None,
                "value_at_risk_95": None,
                "value_at_risk_99": None,
                "beta": None,
            }
        )
        is None
    )


# --- Threshold evaluation ------------------------------------------------------

def test_evaluate_metrics_flags_abnormal_portfolio():
    alerts = alert_service.evaluate_metrics(BAD_METRICS, portfolio_id=7, user_id=1)
    by_metric = {alert["metric"]: alert for alert in alerts}
    assert set(by_metric) == {
        "annualized_volatility",
        "sharpe_ratio",
        "max_drawdown",
        "value_at_risk_95",
        "beta",
    }
    assert by_metric["annualized_volatility"]["severity"] == "critical"
    assert by_metric["annualized_volatility"]["threshold"] == 0.60
    assert by_metric["max_drawdown"]["severity"] == "critical"
    assert by_metric["value_at_risk_95"]["severity"] == "critical"
    assert by_metric["sharpe_ratio"]["severity"] == "warning"
    assert by_metric["beta"]["severity"] == "warning"
    assert all(alert["portfolio_id"] == 7 for alert in alerts)
    assert all(alert["user_id"] == 1 for alert in alerts)


def test_evaluate_metrics_emits_only_most_severe_rule_per_metric():
    metrics = dict(BAD_METRICS)
    metrics["annualized_volatility"] = 0.50  # only crosses the warning threshold
    alerts = alert_service.evaluate_metrics(metrics, portfolio_id=1, user_id=1)
    vol_alerts = [alert for alert in alerts if alert["metric"] == "annualized_volatility"]
    assert len(vol_alerts) == 1
    assert vol_alerts[0]["severity"] == "warning"
    assert vol_alerts[0]["threshold"] == 0.40


def test_evaluate_metrics_ignores_healthy_portfolio():
    alerts = alert_service.evaluate_metrics(HEALTHY_METRICS, portfolio_id=1, user_id=1)
    assert alerts == []


def test_evaluate_metrics_ignores_missing_metrics():
    alerts = alert_service.evaluate_metrics({}, portfolio_id=1, user_id=1)
    assert alerts == []


def test_evaluate_health_bands():
    assert alert_service.evaluate_health(50.0, portfolio_id=1, user_id=1)[0]["severity"] == "warning"
    assert alert_service.evaluate_health(50.0, portfolio_id=1, user_id=1)[0]["category"] == "health"
    assert alert_service.evaluate_health(30.0, portfolio_id=1, user_id=1)[0]["severity"] == "critical"


def test_evaluate_health_emits_single_alert_per_score():
    alerts = alert_service.evaluate_health(30.0, portfolio_id=1, user_id=1)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical"


def test_evaluate_health_ignores_healthy_score():
    assert alert_service.evaluate_health(70.0, portfolio_id=1, user_id=1) == []


# --- Message formatting ---------------------------------------------------------

def test_percent_metrics_are_formatted_as_percentages():
    alerts = alert_service.evaluate_metrics(BAD_METRICS, portfolio_id=1, user_id=1)
    dd_alert = next(alert for alert in alerts if alert["metric"] == "max_drawdown")
    assert "-60.00%" in dd_alert["message"]


# --- Email + auto mark-as-read ---------------------------------------------------

def _patch_alert_check_services(monkeypatch, *, mark_read_impl=None, send_raises=False):
    """Wire run_alert_check's DB/email dependencies to fakes for one abnormal portfolio."""
    created = []

    def fake_insert(alert):
        created.append(alert)
        return len(created)

    def fake_get(alert_id):
        return {
            "alert_id": alert_id,
            "portfolio_id": 2,
            "user_id": 1,
            "category": "risk",
            "severity": "warning",
            "metric": "annualized_volatility",
            "observed_value": 0.5,
            "threshold": 0.4,
            "message": "vol up",
            "is_read": False,
            "created_at": None,
        }

    def fake_send(to_email, alerts):
        if send_raises:
            raise RuntimeError("smtp boom")
        return True

    monkeypatch.setattr(alert_service, "smtp_configured", lambda: True)
    monkeypatch.setattr(alert_service, "send_alert_email", fake_send)
    monkeypatch.setattr(
        alert_service,
        "_iter_portfolio_risk",
        lambda user_id, *a, **k: [
            ({"portfolio_id": 2, "name": "My Portfolio"}, {"metrics": BAD_METRICS})
        ],
    )
    monkeypatch.setattr(
        alert_service.user_model, "get_user_by_id", lambda uid: {"user_id": 1, "email": "a@b.com"}
    )
    monkeypatch.setattr(alert_service.alerts_model, "has_active_alert", lambda *a: False)
    monkeypatch.setattr(alert_service.alerts_model, "insert_alert", fake_insert)
    monkeypatch.setattr(alert_service.alerts_model, "get_alert", fake_get)
    marked: list[int] = []

    def fake_mark_read(alert_id):
        marked.append(alert_id)
        return True

    monkeypatch.setattr(alert_service.alerts_model, "mark_read", mark_read_impl or fake_mark_read)
    return marked


def test_successful_email_marks_sent_alerts_as_read(monkeypatch):
    marked = _patch_alert_check_services(monkeypatch)
    result = alert_service.run_alert_check(1, send_email=True)
    assert result["emailed"] is True
    assert result["emails_sent"] == 1
    assert result["alerts_created"] > 0
    assert marked == [a["alert_id"] for a in result["alerts"]]
    assert all(a["is_read"] is True for a in result["alerts"])


def test_failed_email_leaves_alerts_unread(monkeypatch):
    marked = _patch_alert_check_services(monkeypatch, send_raises=True)
    result = alert_service.run_alert_check(1, send_email=True)
    assert result["emailed"] is False
    assert result["emails_sent"] == 0
    assert marked == []


def test_email_existing_fallback_emails_pending_unread(monkeypatch):
    marked = _patch_alert_check_services(monkeypatch)
    pending = [
        {
            "alert_id": 42,
            "portfolio_id": 2,
            "user_id": 1,
            "category": "risk",
            "severity": "warning",
            "metric": "beta",
            "observed_value": 1.6,
            "threshold": 1.5,
            "message": "beta up",
            "is_read": False,
            "created_at": None,
        }
    ]
    # healthy metrics -> this run creates nothing, so it must email existing unread
    monkeypatch.setattr(
        alert_service,
        "_iter_portfolio_risk",
        lambda user_id, *a, **k: [
            ({"portfolio_id": 2, "name": "My Portfolio"}, {"metrics": HEALTHY_METRICS})
        ],
    )
    monkeypatch.setattr(alert_service.alerts_model, "list_alerts", lambda uid, **k: pending)

    result = alert_service.run_alert_check(1, send_email=True, email_existing=True)
    assert result["alerts_created"] == 0
    assert result["emailed"] is True
    assert result["emails_sent"] == 1
    assert marked == [42]


def test_background_check_emails_like_manual_trigger(monkeypatch):
    """The periodic task must pass email_existing=True (same as the manual endpoint)."""
    calls: list[tuple] = []

    def fake_run(user_id, **kwargs):
        calls.append((user_id, kwargs))
        return {"user_id": user_id, "alerts_created": 0, "emailed": False}

    monkeypatch.setattr(alert_service, "run_alert_check", fake_run)
    monkeypatch.setattr(
        alert_service.user_model, "get_all_users", lambda: [{"user_id": 1}, {"user_id": 2}]
    )

    results = alert_service.run_alert_check_for_all_users()
    assert len(results) == 2
    assert all(kwargs.get("email_existing") is True for _, kwargs in calls)
    assert all(kwargs.get("send_email") is True for _, kwargs in calls)
