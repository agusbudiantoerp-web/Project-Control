import pytest

from ai_project_control.portfolio_monitoring import (
    PortfolioMonitoringStore,
    compare_portfolio_snapshots,
)


def test_detects_adverse_spi_cpi_risk_and_delay_changes():
    before = [{"project_id": "P1", "SPI": 1.0, "CPI": 1.0, "risk_score": 20, "delayed_activity_count": 1}]
    after = [{"project_id": "P1", "SPI": 0.9, "CPI": 0.9, "risk_score": 30, "delayed_activity_count": 2}]
    result = compare_portfolio_snapshots(before, after, material_change=0.05)
    assert result["status"] == "CHANGES_DETECTED"
    assert {row["metric"] for row in result["changes"]} == {"SPI", "CPI", "risk_score", "delayed_activity_count"}


def test_ignores_improvements_and_small_changes():
    before = [{"project_id": "P1", "SPI": 0.9, "CPI": 0.9, "risk_score": 50}]
    after = [{"project_id": "P1", "SPI": 1.0, "CPI": 1.0, "risk_score": 49}]
    assert compare_portfolio_snapshots(before, after)["status"] == "NO_MATERIAL_ADVERSE_CHANGE"


def test_reports_added_and_removed_projects():
    result = compare_portfolio_snapshots([{"project_id": "OLD"}], [{"project_id": "NEW"}])
    assert [(r["project_id"], r["change"]) for r in result["changes"]] == [("NEW", "ADDED"), ("OLD", "REMOVED")]


def test_missing_metrics_are_not_treated_as_zero():
    result = compare_portfolio_snapshots([{"project_id": "P1"}], [{"project_id": "P1", "SPI": 0.5}])
    assert result["change_count"] == 0


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        compare_portfolio_snapshots([], [], material_change=1.1)


def test_store_persists_and_compares_snapshots(tmp_path):
    store = PortfolioMonitoringStore(tmp_path / "monitor.sqlite3")
    first = store.compare_with_previous([{"project_id": "P1", "SPI": 1.0}], captured_at="2026-11-22")
    second = store.compare_with_previous([{"project_id": "P1", "SPI": 0.8}], captured_at="2026-11-23")
    assert first["previous_snapshot_available"] is False
    assert second["previous_snapshot_available"] is True
    assert second["change_count"] == 1


def test_snapshot_rejects_duplicate_or_missing_project_ids(tmp_path):
    store = PortfolioMonitoringStore(tmp_path / "monitor.sqlite3")
    with pytest.raises(ValueError):
        store.save_snapshot([{"project_id": "P1"}, {"project_id": "P1"}])
