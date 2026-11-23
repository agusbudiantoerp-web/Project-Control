import pytest

from ai_project_control.portfolio_health_monitoring import build_health_monitoring


def test_single_snapshot_is_no_baseline_not_assumed_healthy():
    result = build_health_monitoring([
        {"project_id": "P1", "snapshot_date": "2026-11-01", "SPI": 1.0, "CPI": 1.0}
    ])
    row = result["projects"][0]
    assert row["status"] == "NO_BASELINE"
    assert result["summary"]["no_baseline_count"] == 1


def test_two_snapshots_calculate_metric_changes_and_signals():
    result = build_health_monitoring([
        {"project_id": "P1", "project_name": "Bridge", "snapshot_date": "2026-11-01",
         "SPI": 1.0, "CPI": 0.98, "risk_score": 30},
        {"project_id": "P1", "project_name": "Bridge", "snapshot_date": "2026-11-15",
         "SPI": 0.94, "CPI": 1.01, "risk_score": 42},
    ])
    row = result["projects"][0]
    assert row["status"] == "TREND_ASSESSED"
    assert row["changes"] == {"SPI": -0.06, "CPI": 0.03, "risk_score": 12.0}
    assert any("SPI deteriorated" in signal for signal in row["signals"])
    assert any("Risk score increased" in signal for signal in row["signals"])


def test_missing_metric_is_not_fabricated():
    result = build_health_monitoring([
        {"project_id": "P1", "snapshot_date": "2026-11-01", "SPI": 1.0},
        {"project_id": "P1", "snapshot_date": "2026-11-15", "CPI": 0.9},
    ])
    changes = result["projects"][0]["changes"]
    assert changes == {"SPI": None, "CPI": None, "risk_score": None}
    assert result["projects"][0]["status"] == "INSUFFICIENT_DATA"


def test_duplicate_project_date_is_flagged_as_conflict():
    result = build_health_monitoring([
        {"project_id": "P1", "snapshot_date": "2026-11-01", "SPI": 1.0},
        {"project_id": "P1", "snapshot_date": "2026-11-01", "SPI": 0.8},
    ])
    assert result["projects"][0]["status"] == "DATA_CONFLICT"
    assert result["summary"]["data_conflict_count"] == 1


@pytest.mark.parametrize("snapshot_date", ["", "yesterday", "2026-13-01"])
def test_invalid_snapshot_date_is_rejected(snapshot_date):
    with pytest.raises(ValueError, match="snapshot_date"):
        build_health_monitoring([
            {"project_id": "P1", "snapshot_date": snapshot_date}
        ])


def test_missing_project_id_is_rejected():
    with pytest.raises(ValueError, match="project_id"):
        build_health_monitoring([{"snapshot_date": "2026-11-01"}])
