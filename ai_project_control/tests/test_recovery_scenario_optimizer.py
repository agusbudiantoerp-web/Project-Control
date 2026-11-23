import pandas as pd

from recovery_scenario_optimizer import optimize_recovery_scenarios


def _scenarios():
    return pd.DataFrame([
        {"scenario": "A", "actual_days_saved": 5, "incremental_cost": 500, "feasible": True},
        {"scenario": "B", "actual_days_saved": 8, "incremental_cost": 1200, "feasible": True},
        {"scenario": "C", "actual_days_saved": 3, "incremental_cost": 200, "feasible": True},
        {"scenario": "D", "actual_days_saved": 9, "incremental_cost": 5000, "feasible": True},
        {"scenario": "E", "actual_days_saved": 10, "incremental_cost": None, "feasible": True},
        {"scenario": "F", "actual_days_saved": 10, "incremental_cost": 100, "feasible": False},
    ])


def test_recommends_lowest_cost_per_day_within_constraints():
    result = optimize_recovery_scenarios(_scenarios(), budget_limit=1500, minimum_days_saved=4)
    assert result["recommended"]["scenario"] == "A"
    assert set(result["eligible"]["scenario"]) == {"A", "B"}


def test_pareto_frontier_excludes_dominated_options():
    result = optimize_recovery_scenarios(_scenarios())
    assert "A" in result["pareto"]["scenario"].tolist()
    assert "B" in result["pareto"]["scenario"].tolist()
    assert "C" in result["pareto"]["scenario"].tolist()
    assert "D" not in result["pareto"]["scenario"].tolist()


def test_unpriced_and_infeasible_scenarios_are_not_recommended():
    result = optimize_recovery_scenarios(_scenarios())
    assert "E" not in result["eligible"]["scenario"].tolist()
    assert "F" not in result["eligible"]["scenario"].tolist()


def test_budget_and_cost_per_day_limits_are_enforced():
    result = optimize_recovery_scenarios(
        _scenarios(), budget_limit=600, minimum_days_saved=1, maximum_cost_per_day=100
    )
    assert set(result["eligible"]["scenario"]) == {"A", "C"}


def test_source_scenarios_are_not_mutated():
    source = _scenarios()
    before = source.copy(deep=True)
    optimize_recovery_scenarios(source, budget_limit=1000)
    pd.testing.assert_frame_equal(source, before)
