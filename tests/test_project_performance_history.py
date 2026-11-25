import pytest

from ai_project_control.project_performance_history import ProjectPerformanceHistoryStore


def sample(project="P1", day="2026-01-01", **values):
    return {"project_id": project, "reporting_date": day, "currency": "IDR",
            "SPI": 1.0, "CPI": 1.0, "actual_cost": 100, **values}


def test_history_is_persisted_and_ordered(tmp_path):
    store = ProjectPerformanceHistoryStore(tmp_path / "history.sqlite3")
    store.save(sample(day="2026-01-15", SPI=.9))
    store.save(sample(day="2026-01-01", SPI=1.0))
    rows = store.list_snapshots(project_id="P1")
    assert [row["reporting_date"] for row in rows] == ["2026-01-01", "2026-01-15"]
    assert rows[0]["SPI"] == 1.0


def test_duplicate_project_reporting_date_is_rejected(tmp_path):
    store = ProjectPerformanceHistoryStore(tmp_path / "history.sqlite3")
    store.save(sample())
    with pytest.raises(ValueError, match="already exists"):
        store.save(sample(SPI=.8))


def test_next_snapshot_dataset_uses_only_prior_features_and_next_targets(tmp_path):
    store = ProjectPerformanceHistoryStore(tmp_path / "history.sqlite3")
    store.save(sample(day="2026-01-01", SPI=1.0, CPI=1.0, actual_cost=100))
    store.save(sample(day="2026-01-11", SPI=.9, CPI=.95, actual_cost=130))
    store.save(sample(day="2026-01-21", SPI=.85, CPI=.9, actual_cost=150))
    result = store.build_next_snapshot_dataset()
    assert result["status"] == "READY"
    assert result["row_count"] == 2
    first = result["rows"][0]
    assert first["feature_SPI"] == 1.0
    assert first["target_SPI"] == .9
    assert first["delta_actual_cost"] == 30


def test_currency_mismatch_pairs_are_not_pooled(tmp_path):
    store = ProjectPerformanceHistoryStore(tmp_path / "history.sqlite3")
    store.save(sample(day="2026-01-01", currency="IDR"))
    store.save({**sample(day="2026-01-11"), "currency": "USD"})
    result = store.build_next_snapshot_dataset()
    assert result["row_count"] == 0
    assert result["skipped_currency_mismatch_pairs"] == 1


def test_invalid_metric_and_date_are_rejected(tmp_path):
    store = ProjectPerformanceHistoryStore(tmp_path / "history.sqlite3")
    with pytest.raises(ValueError, match="SPI"):
        store.save(sample(SPI=float("nan")))
    with pytest.raises(ValueError, match="reporting_date"):
        store.save(sample(day="not-a-date"))


def test_insufficient_history_returns_empty_dataset_and_csv(tmp_path):
    store = ProjectPerformanceHistoryStore(tmp_path / "history.sqlite3")
    store.save(sample())
    result = store.build_next_snapshot_dataset()
    assert result["status"] == "INSUFFICIENT_HISTORY"
    assert result["rows"] == []
    assert store.export_dataset_csv() == ""


def test_dataset_requires_positive_minimum_gap(tmp_path):
    store = ProjectPerformanceHistoryStore(tmp_path / "history.sqlite3")
    with pytest.raises(ValueError, match="minimum_gap_days"):
        store.build_next_snapshot_dataset(minimum_gap_days=0)
