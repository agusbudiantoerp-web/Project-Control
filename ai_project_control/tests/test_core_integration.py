import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from core import calculate_cpm, calculate_evm, risk_analysis, validate_dataset


def test_cpm_forward_backward_pass_and_critical_path():
    activities = pd.DataFrame([
        {"activity_id": "A", "activity_name": "A", "wbs_id": "1", "duration_days": 5, "predecessor_ids": ""},
        {"activity_id": "B", "activity_name": "B", "wbs_id": "1", "duration_days": 3, "predecessor_ids": "A"},
        {"activity_id": "C", "activity_name": "C", "wbs_id": "1", "duration_days": 2, "predecessor_ids": "A"},
        {"activity_id": "D", "activity_name": "D", "wbs_id": "1", "duration_days": 4, "predecessor_ids": "B,C"},
    ])
    result, stats = calculate_cpm(activities)
    rows = result.set_index("activity_id")
    assert stats["project_duration"] == 12
    assert bool(rows.loc["A", "is_critical"])
    assert bool(rows.loc["B", "is_critical"])
    assert not bool(rows.loc["C", "is_critical"])
    assert bool(rows.loc["D", "is_critical"])
    assert rows.loc["C", "total_float_days"] == 1


def test_cpm_rejects_unknown_predecessor_and_cycle():
    bad = pd.DataFrame([
        {"activity_id": "A", "activity_name": "A", "wbs_id": "1", "duration_days": 1, "predecessor_ids": "MISSING"}
    ])
    try:
        calculate_cpm(bad)
    except ValueError as exc:
        assert "unknown predecessor" in str(exc)
    else:
        raise AssertionError("Unknown predecessor must fail validation")

    cycle = pd.DataFrame([
        {"activity_id": "A", "activity_name": "A", "wbs_id": "1", "duration_days": 1, "predecessor_ids": "B"},
        {"activity_id": "B", "activity_name": "B", "wbs_id": "1", "duration_days": 1, "predecessor_ids": "A"},
    ])
    try:
        calculate_cpm(cycle)
    except ValueError as exc:
        assert "cycle" in str(exc).lower()
    else:
        raise AssertionError("Precedence cycle must fail validation")


def test_activity_business_validation_checks_wbs_and_dates():
    activities = pd.DataFrame([{
        "activity_id": "A1", "wbs_id": "UNKNOWN", "activity_name": "Work",
        "duration_days": 2, "planned_start": "2026-02-10",
        "planned_finish": "2026-02-09", "predecessor_ids": "",
        "weight_pct": 100,
    }])
    issues = validate_dataset("activities.csv", activities, {
        "wbs.csv": pd.DataFrame([{"wbs_id": "1.1"}])
    })
    joined = " ".join(issues)
    assert "WBS tidak ditemukan" in joined
    assert "planned_finish" in joined


def test_evm_known_case():
    activities = pd.DataFrame([{
        "activity_id": "A1", "wbs_id": "1.1", "activity_name": "Work",
        "duration_days": 10, "planned_start": "2026-01-01",
        "planned_finish": "2026-01-10", "predecessor_ids": "",
        "weight_pct": 100,
    }])
    boq = pd.DataFrame([{
        "boq_id": "B1", "wbs_id": "1.1", "description": "Work",
        "unit": "m3", "budget_quantity": 100, "unit_rate": 10,
        "budget_amount": 1000,
    }])
    progress = pd.DataFrame([{
        "period_end": "2026-01-05", "activity_id": "A1", "boq_id": "B1",
        "planned_quantity_to_date": 50, "actual_quantity_to_date": 40,
    }])
    actual = pd.DataFrame([{"transaction_date": "2026-01-05", "amount": 300}])
    result = calculate_evm(pd.DataFrame(), activities, boq, progress, actual, "2026-01-05")
    assert result["BAC"] == 1000
    assert result["PV"] == 500
    assert result["EV"] == 400
    assert result["AC"] == 300
    assert result["SPI"] == 0.8
    assert np.isclose(result["CPI"], 4 / 3)


def test_risk_monte_carlo_is_reproducible_and_respects_certain_events():
    risks = pd.DataFrame([
        {"risk_id": "R1", "risk_description": "Certain", "probability": 1,
         "cost_impact": 100, "schedule_impact_days": 4},
        {"risk_id": "R2", "risk_description": "Impossible", "probability": 0,
         "cost_impact": 500, "schedule_impact_days": 10},
    ])
    ranked, stats, samples = risk_analysis(risks, iterations=1000, seed=7)
    assert stats["expected_cost_exposure"] == 100
    assert stats["expected_schedule_exposure_days"] == 4
    assert (samples["cost"] == 100).all()
    assert (samples["delay_days"] == 4).all()
    assert ranked.iloc[0]["risk_id"] == "R1"
