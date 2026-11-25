import pytest

from ai_project_control.predictive_early_warning import forecast_project_control_trends


def snapshots():
    return [
        {"date": "2026-01-01", "project_id": "P1", "SPI": 1.02, "CPI": 1.01, "risk_score": 30},
        {"date": "2026-01-11", "project_id": "P1", "SPI": 0.99, "CPI": 1.00, "risk_score": 40},
        {"date": "2026-01-21", "project_id": "P1", "SPI": 0.96, "CPI": 0.99, "risk_score": 55},
    ]


def test_trend_forecast_flags_projected_spi_crossing():
    result = forecast_project_control_trends(snapshots(), horizon_days=30)
    project = result["projects"][0]
    spi = next(row for row in project["metrics"] if row["metric"] == "SPI")
    assert spi["status"] == "PROJECTED_THRESHOLD_CROSSING"
    assert spi["projected_value"] < spi["threshold"]
    assert project["attention_metric_count"] >= 1


def test_insufficient_metric_history_is_not_imputed():
    rows = snapshots()
    for row in rows[1:]:
        row.pop("CPI")
    result = forecast_project_control_trends(rows)
    cpi = next(row for row in result["projects"][0]["metrics"] if row["metric"] == "CPI")
    assert cpi["status"] == "INSUFFICIENT_HISTORY"
    assert cpi["forecast"] is None


def test_currently_adverse_kpi_is_flagged():
    rows = [
        {"date": "2026-01-01", "project_id": "P2", "CPI": .80},
        {"date": "2026-01-10", "project_id": "P2", "CPI": .82},
        {"date": "2026-01-20", "project_id": "P2", "CPI": .83},
    ]
    result = forecast_project_control_trends(rows)
    cpi = result["projects"][0]["metrics"][1]
    assert cpi["metric"] == "CPI"
    assert cpi["status"] == "CURRENTLY_ADVERSE"


def test_duplicate_dates_and_invalid_horizon_rejected():
    rows = snapshots()
    rows[2]["date"] = rows[1]["date"]
    with pytest.raises(ValueError, match="duplicate"):
        forecast_project_control_trends(rows)
    with pytest.raises(ValueError, match="horizon_days"):
        forecast_project_control_trends(snapshots(), horizon_days=0)


def test_empty_snapshots_returns_no_snapshots():
    assert forecast_project_control_trends([])["status"] == "NO_SNAPSHOTS"


def test_nonfinite_values_are_skipped_as_missing():
    rows = snapshots()
    for row in rows:
        row["risk_score"] = float("nan")
    result = forecast_project_control_trends(rows)
    risk = next(row for row in result["projects"][0]["metrics"] if row["metric"] == "risk_score")
    assert risk["status"] == "INSUFFICIENT_HISTORY"
