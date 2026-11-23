import pytest

from ai_project_control.historical_ml_training import train_historical_kpi_models


def make_rows(count=20):
    rows = []
    for index in range(count):
        rows.append({
            "project_id": "P1" if index % 2 == 0 else "P2",
            "target_date": f"2026-{1 + index // 28:02d}-{1 + index % 28:02d}",
            "gap_days": 14,
            "feature_SPI": 1.0 - index * .005,
            "feature_CPI": .98 - index * .003,
            "feature_risk_score": 20 + index,
            "feature_delayed_activity_count": index // 5,
            "feature_overdue_action_count": index // 7,
            "target_SPI": .99 - index * .006,
            "target_CPI": .97 - index * .004,
            "target_risk_score": 22 + index * 1.2,
            "target_delayed_activity_count": index // 4,
            "target_overdue_action_count": index // 6,
        })
    return rows


def test_models_use_chronological_holdout_and_report_baseline():
    result = train_historical_kpi_models(make_rows())
    assert result["status"] == "EVALUATED"
    assert "Chronological" in result["split_method"]
    spi = next(row for row in result["metrics"] if row["target"] == "SPI")
    assert spi["status"] == "EVALUATED"
    assert spi["training_rows"] >= 8
    assert spi["test_rows"] >= 2
    assert spi["test_start_date"] > make_rows()[0]["target_date"]
    assert "SPI" in result["models"]


def test_missing_features_are_imputed_without_future_target_leakage():
    rows = make_rows()
    for row in rows:
        row["feature_CPI"] = None
    result = train_historical_kpi_models(rows)
    assert result["status"] == "EVALUATED"
    assert "target_CPI" not in result["feature_columns"]
    assert next(row for row in result["metrics"] if row["target"] == "CPI")["status"] == "EVALUATED"


def test_small_history_is_not_force_trained():
    result = train_historical_kpi_models(make_rows(6))
    assert result["status"] == "INSUFFICIENT_HISTORY"
    assert result["models"] == {}


def test_invalid_dataset_and_parameters_are_rejected():
    with pytest.raises(TypeError, match="list of dictionaries"):
        train_historical_kpi_models("not a dataset")
    with pytest.raises(ValueError, match="test_fraction"):
        train_historical_kpi_models(make_rows(), test_fraction=.05)
    with pytest.raises(ValueError, match="target_date"):
        train_historical_kpi_models([{"target_SPI": .9}])


def test_random_state_must_be_integer():
    with pytest.raises(ValueError, match="random_state"):
        train_historical_kpi_models(make_rows(), random_state=1.5)
