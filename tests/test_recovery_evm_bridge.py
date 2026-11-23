from ai_project_control.recovery_evm_bridge import evaluate_recovery_evm


def rows(period, pv, ev, ac):
    return (
        [{"project_id": "P1", "period": period, "planned_value": pv, "earned_value": ev}],
        [{"project_id": "P1", "period": period, "actual_cost": ac}],
    )


def test_evm_bridge_compares_spi_cpi_before_and_after_recovery():
    bp, bc = rows("2026-01", 100, 70, 100)
    ap, ac = rows("2026-02", 100, 95, 100)
    result = evaluate_recovery_evm(
        {"project_id": "P1", "BAC": 1000, "currency": "IDR"},
        before_progress_rows=bp, before_actual_cost_rows=bc,
        after_progress_rows=ap, after_actual_cost_rows=ac,
        approved_recovery_budget=200, actual_recovery_cost=150,
    )
    assert result["status"] == "ASSESSED"
    assert result["before_evm"]["SPI"] == .7
    assert result["after_evm"]["SPI"] == .95
    assert result["recovery_effectiveness"]["comparisons"]["SPI"]["status"] == "IMPROVED"
    assert result["recovery_effectiveness"]["comparisons"]["CPI"]["status"] == "UNCHANGED"
    assert result["recovery_effectiveness"]["recovery_cost"]["status"] == "WITHIN_BUDGET"


def test_bridge_keeps_non_evm_indicators_unassessed():
    bp, bc = rows("2026-01", 100, 80, 100)
    ap, ac = rows("2026-02", 100, 90, 100)
    result = evaluate_recovery_evm(
        {"project_id": "P1", "BAC": 1000},
        before_progress_rows=bp, before_actual_cost_rows=bc,
        after_progress_rows=ap, after_actual_cost_rows=ac,
    )
    comparisons = result["recovery_effectiveness"]["comparisons"]
    assert comparisons["risk_score"]["status"] == "UNASSESSED"
    assert comparisons["delayed_activity_count"]["status"] == "UNASSESSED"


def test_bridge_reports_partial_assessment_when_evm_inputs_missing():
    result = evaluate_recovery_evm(
        {"project_id": "P1", "BAC": 1000},
        before_progress_rows=[], before_actual_cost_rows=[],
        after_progress_rows=[], after_actual_cost_rows=[],
    )
    assert result["status"] == "PARTIALLY_ASSESSED"
