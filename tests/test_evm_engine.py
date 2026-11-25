import pytest

from ai_project_control.evm_engine import calculate_evm


def test_calculates_core_evm_and_forecast_metrics():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1000, "currency": "IDR"},
        [{"project_id": "P1", "period": "2026-01", "planned_value": 500, "earned_value": 400},
         {"project_id": "P1", "period": "2026-02", "planned_value": 300, "earned_value": 300}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 500},
         {"project_id": "P1", "period": "2026-02", "actual_cost": 300}],
    )
    assert result["PV"] == 800
    assert result["EV"] == 700
    assert result["AC"] == 800
    assert result["SV"] == -100
    assert result["CV"] == -100
    assert result["SPI"] == 0.88
    assert result["CPI"] == 0.88
    assert result["EAC"] == 1142.86
    assert result["VAC"] == -142.86
    assert result["status"] == "ASSESSED"


def test_period_cutoff_excludes_future_records():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1000},
        [{"project_id": "P1", "period": "2026-01", "planned_value": 100, "earned_value": 80},
         {"project_id": "P1", "period": "2026-02", "planned_value": 100, "earned_value": 90}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 100},
         {"project_id": "P1", "period": "2026-02", "actual_cost": 110}],
        as_of_period="2026-01",
    )
    assert result["PV"] == 100
    assert result["EV"] == 80
    assert result["AC"] == 100


def test_missing_data_is_not_coerced_to_zero():
    result = calculate_evm({"project_id": "P1", "BAC": 1000}, [], [])
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["PV"] is None
    assert result["EV"] is None
    assert result["AC"] is None
    assert set(result["data_gaps"]) == {"PV", "EV", "AC"}


def test_nonpositive_denominators_do_not_create_ratios():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1000},
        [{"project_id": "P1", "period": "2026-01", "planned_value": 0, "earned_value": 50}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 0}],
    )
    assert result["SPI"] is None
    assert result["CPI"] is None
    assert "PV_MUST_BE_POSITIVE_FOR_SPI" in result["data_gaps"]
    assert "AC_MUST_BE_POSITIVE_FOR_CPI" in result["data_gaps"]


def test_other_projects_are_excluded():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1000},
        [{"project_id": "P2", "period": "2026-01", "planned_value": 50, "earned_value": 40}],
        [{"project_id": "P2", "period": "2026-01", "actual_cost": 50}],
    )
    assert result["PV"] is None
    assert result["AC"] is None


def test_invalid_numeric_values_remain_data_gaps():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1000},
        [{"project_id": "P1", "period": "2026-01", "planned_value": "unknown", "earned_value": 50}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 40}],
    )
    assert result["PV"] is None
    assert result["status"] == "INSUFFICIENT_DATA"


def test_missing_project_id_rejected():
    with pytest.raises(ValueError):
        calculate_evm({}, [], [])


@pytest.mark.parametrize("bac", [0, -100])
def test_nonpositive_bac_blocks_evm_forecast(bac):
    result = calculate_evm(
        {"project_id": "P1", "BAC": bac},
        [{"project_id": "P1", "period": "2026-01", "planned_value": 100, "earned_value": 80}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 90}],
    )
    assert result["EAC"] is None
    assert result["VAC"] is None
    assert result["status"] == "INSUFFICIENT_DATA"
    assert "BAC_MUST_BE_POSITIVE_FOR_FORECAST" in result["data_gaps"]


def test_boolean_financial_values_are_not_treated_as_numeric():
    result = calculate_evm(
        {"project_id": "P1", "BAC": True},
        [{"project_id": "P1", "period": "2026-01", "planned_value": 100, "earned_value": 80}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 90}],
    )
    assert result["BAC"] is None
    assert result["EAC"] is None


def test_negative_or_overflowing_evm_source_amounts_remain_unassessed():
    negative = calculate_evm(
        {"project_id": "P1", "BAC": 1000},
        [{"project_id": "P1", "period": "2026-01", "planned_value": 100,
          "earned_value": -10}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 90}],
    )
    assert negative["EV"] is None
    assert negative["status"] == "INSUFFICIENT_DATA"

    overflow = calculate_evm(
        {"project_id": "P1", "BAC": 1e308},
        [
            {"project_id": "P1", "period": "2026-01", "planned_value": 1e308,
             "earned_value": 1e308},
            {"project_id": "P1", "period": "2026-02", "planned_value": 1e308,
             "earned_value": 1e308},
        ],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 1e308}],
    )
    assert overflow["PV"] is None
    assert overflow["status"] == "INSUFFICIENT_DATA"


def test_overflowing_evm_indices_are_unassessed():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1e308},
        [{"project_id": "P1", "period": "2026-01",
          "planned_value": 1e-308, "earned_value": 1e308}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 1e-308}],
    )
    assert result["SPI"] is None
    assert result["CPI"] is None
    assert result["EAC"] is None
    assert "SPI_EXCEEDS_SUPPORTED_NUMERIC_RANGE" in result["data_gaps"]
    assert "CPI_EXCEEDS_SUPPORTED_NUMERIC_RANGE" in result["data_gaps"]


def test_actual_cost_currency_mismatch_blocks_evm_cost_metrics():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1000, "currency": "IDR"},
        [{"project_id": "P1", "period": "2026-01",
          "planned_value": 100, "earned_value": 80, "currency": "IDR"}],
        [{"project_id": "P1", "period": "2026-01",
          "actual_cost": 90, "currency": "USD"}],
    )
    assert result["AC"] is None
    assert result["CPI"] is None
    assert result["EAC"] is None
    assert "ACTUAL_COST_CURRENCY_MISMATCH" in result["data_gaps"]
    assert result["status"] == "INSUFFICIENT_DATA"


def test_progress_currency_mismatch_blocks_pv_and_ev():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1000, "currency": "IDR"},
        [{"project_id": "P1", "period": "2026-01",
          "planned_value": 100, "earned_value": 80, "currency": "USD"}],
        [{"project_id": "P1", "period": "2026-01",
          "actual_cost": 90, "currency": "IDR"}],
    )
    assert result["PV"] is None
    assert result["EV"] is None
    assert result["SPI"] is None
    assert "PROGRESS_CURRENCY_MISMATCH" in result["data_gaps"]
    assert result["status"] == "INSUFFICIENT_DATA"


def test_evm_currency_comparison_is_case_insensitive_and_missing_currency_remains_assumption():
    result = calculate_evm(
        {"project_id": "P1", "BAC": 1000, "currency": "IDR"},
        [{"project_id": "P1", "period": "2026-01",
          "planned_value": 100, "earned_value": 80, "currency": "idr"}],
        [{"project_id": "P1", "period": "2026-01", "actual_cost": 90}],
    )
    assert result["PV"] == 100
    assert result["EV"] == 80
    assert result["AC"] == 90
    assert result["status"] == "ASSESSED"
