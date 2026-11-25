"""Tests for resource capacity smoothing and shift-capacity comparison."""
import importlib
import sys
import types

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def engine(monkeypatch):
    core = types.ModuleType("core")

    def calculate_cpm(frame):
        result = frame.copy()
        result["total_float_days"] = result.get(
            "total_float_days", pd.Series([0] * len(result), index=result.index)
        )
        return result, {}

    core.calculate_cpm = calculate_cpm
    monkeypatch.setitem(sys.modules, "core", core)
    sys.modules.pop("ai_project_control.resource_optimization", None)
    return importlib.import_module("ai_project_control.resource_optimization")


def sample_data():
    activities = pd.DataFrame([
        {"activity_id": "A", "duration_days": 3, "total_float_days": 2},
        {"activity_id": "B", "duration_days": 2, "total_float_days": 0},
    ])
    resources = pd.DataFrame([{"rsrc_id": "R1", "capacity_per_day": 5.0}])
    assignments = pd.DataFrame([
        {"task_id": "A", "rsrc_id": "R1", "target_qty": 12,
         "target_start_date": "2026-01-01", "target_end_date": "2026-01-03"},
        {"task_id": "B", "rsrc_id": "R1", "target_qty": 10,
         "target_start_date": "2026-01-02", "target_end_date": "2026-01-03"},
    ])
    return activities, resources, assignments


def test_smoothing_reports_baseline_and_scenario_without_mutating_inputs(engine):
    activities, resources, assignments = sample_data()
    original = assignments.copy(deep=True)
    result = engine.simulate_resource_smoothing(activities, resources, assignments)
    assert result["available"] is True
    assert result["baseline_overloaded_days"] > 0
    assert "suggested_start" in result["scenario"].columns
    pd.testing.assert_frame_equal(assignments, original)


def test_smoothing_rejects_unknown_activity(engine):
    activities, resources, assignments = sample_data()
    assignments.loc[0, "task_id"] = "UNKNOWN"
    with pytest.raises(ValueError, match="unknown activities"):
        engine.simulate_resource_smoothing(activities, resources, assignments)


def test_smoothing_returns_unavailable_for_empty_inputs(engine):
    result = engine.simulate_resource_smoothing(
        pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    assert result["available"] is False


def test_shift_capacity_requires_explicit_one_shift_baseline(engine):
    _, resources, assignments = sample_data()
    with pytest.raises(ValueError, match="one-shift baseline"):
        engine.compare_shift_capacity_scenarios(resources, assignments, {2: 1.5})


def test_shift_capacity_does_not_invent_incremental_cost(engine):
    _, resources, assignments = sample_data()
    result = engine.compare_shift_capacity_scenarios(
        resources, assignments, {1: 1.0, 2: 1.5}
    )
    assert result["incremental_cost"].isna().all()
    assert result["overloaded_resource_days"].iloc[1] <= result["overloaded_resource_days"].iloc[0]
