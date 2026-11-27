import pandas as pd

from integrated_recovery_impact import build_integrated_recovery_impact


def _scenarios():
    return pd.DataFrame([
        {"scenario":"Base+3d","actual_days_saved":3,"incremental_cost":300,"feasible":True},
        {"scenario":"Base+5d","actual_days_saved":5,"incremental_cost":700,"feasible":True},
        {"scenario":"Invalid","actual_days_saved":0,"incremental_cost":100,"feasible":False},
    ])


def test_missing_resource_and_risk_are_not_assumed_clear():
    result = build_integrated_recovery_impact(_scenarios())
    assert result["available"]
    assert set(result["comparison"]["resource_assessment_status"]) == {"NOT ASSESSED"}
    assert set(result["comparison"]["risk_assessment_status"]) == {"NOT ASSESSED"}


def test_resource_constraint_is_linked_by_scenario():
    resource = pd.DataFrame([
        {"scenario":"Base+3d","resource_feasible":True,"resource_shortfall":0},
        {"scenario":"Base+5d","resource_feasible":False,"resource_shortfall":4},
    ])
    result = build_integrated_recovery_impact(_scenarios(), resource_assessment=resource)
    rows = result["comparison"].set_index("scenario")
    assert rows.loc["Base+5d","overall_review_status"] == "HOLD — resource feasibility issue"
    assert rows.loc["Base+3d","resource_assessment_status"] == "FEASIBLE"


def test_risk_delta_requires_explicit_baseline_and_residual_values():
    risk = pd.DataFrame([
        {"scenario":"Base+3d","baseline_expected_risk_cost":1000,
         "residual_expected_risk_cost":700,"baseline_expected_risk_days":8,
         "residual_expected_risk_days":5}
    ])
    result = build_integrated_recovery_impact(_scenarios(), risk_assessment=risk)
    row = result["comparison"].set_index("scenario").loc["Base+3d"]
    assert row["risk_cost_change"] == -300
    assert row["risk_days_change"] == -3


def test_missing_risk_residual_is_not_interpreted_as_savings():
    risk = pd.DataFrame([{"scenario":"Base+3d","baseline_expected_risk_cost":1000}])
    result = build_integrated_recovery_impact(_scenarios(), risk_assessment=risk)
    row = result["comparison"].set_index("scenario").loc["Base+3d"]
    assert pd.isna(row["risk_cost_change"])
    assert row["risk_assessment_status"] == "NOT ASSESSED"


def test_source_frames_are_not_mutated():
    source = _scenarios()
    before = source.copy(deep=True)
    build_integrated_recovery_impact(source)
    pd.testing.assert_frame_equal(source, before)
