"""Bridge EVM period snapshots into recovery effectiveness evaluation."""
from __future__ import annotations

from typing import Any

from .evm_engine import calculate_evm
from .recovery_effectiveness import evaluate_recovery_effectiveness


def evaluate_recovery_evm(
    project: dict[str, Any],
    *,
    before_progress_rows: list[dict[str, Any]],
    before_actual_cost_rows: list[dict[str, Any]],
    after_progress_rows: list[dict[str, Any]],
    after_actual_cost_rows: list[dict[str, Any]],
    before_period: str | None = None,
    after_period: str | None = None,
    approved_recovery_budget: Any = None,
    actual_recovery_cost: Any = None,
) -> dict[str, Any]:
    """Compare EVM snapshots and feed SPI/CPI into the recovery scorecard.

    The supplied row sets must represent comparable periods and consistent
    scope. Each calculate_evm call follows that engine's aggregation contract.
    """
    before = calculate_evm(
        project, before_progress_rows, before_actual_cost_rows,
        as_of_period=before_period,
    )
    after = calculate_evm(
        project, after_progress_rows, after_actual_cost_rows,
        as_of_period=after_period,
    )
    before_indicators = {
        "SPI": before["SPI"], "CPI": before["CPI"],
        "risk_score": None, "delayed_activity_count": None,
        "overdue_action_count": None,
    }
    after_indicators = {
        "SPI": after["SPI"], "CPI": after["CPI"],
        "risk_score": None, "delayed_activity_count": None,
        "overdue_action_count": None,
    }
    evaluation = evaluate_recovery_effectiveness(
        before_indicators, after_indicators,
        approved_recovery_budget=approved_recovery_budget,
        actual_recovery_cost=actual_recovery_cost,
        currency=project.get("currency"),
    )
    return {
        "project_id": before["project_id"],
        "before_evm": before,
        "after_evm": after,
        "recovery_effectiveness": evaluation,
        "status": (
            "ASSESSED" if before["SPI"] is not None and before["CPI"] is not None
            and after["SPI"] is not None and after["CPI"] is not None
            else "PARTIALLY_ASSESSED"
        ),
        "limitations": [
            "Risk, delay and action indicators are not inferred from EVM and remain unassessed.",
            "Before and after datasets must use consistent scope, currency, period definitions and cumulative/delta conventions.",
            "The EVM engine sums supplied rows; cumulative snapshots must be filtered to the intended snapshot before calling this bridge.",
            "EVM movement does not prove recovery actions caused the observed change.",
        ],
    }
