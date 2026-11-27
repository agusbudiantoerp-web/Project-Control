"""Streamlit component for transparent, user-entered recovery scenario comparison."""
from __future__ import annotations

from typing import Any

from .recovery_scenario_comparator import compare_recovery_scenarios


def render_recovery_scenario_planner() -> dict[str, Any] | None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is required to render this component.") from exc

    st.subheader("Project Recovery Scenario Planner")
    st.caption("Enter estimates reviewed by the project team. This tool compares inputs; it does not predict or approve recovery feasibility.")
    current_duration = st.number_input(
        "Current forecast duration (days)", min_value=0.01, value=100.0, step=1.0,
        key="pc_recovery_current_duration",
    )
    target_duration = st.number_input(
        "Target duration (days; 0 means no target)", min_value=0.0, value=0.0, step=1.0,
        key="pc_recovery_target_duration",
    )
    scenario_count = st.number_input(
        "Number of scenarios", min_value=1, max_value=8, value=3, step=1,
        key="pc_recovery_scenario_count",
    )
    scenarios = []
    for index in range(int(scenario_count)):
        with st.expander(f"Scenario {index + 1}", expanded=index == 0):
            scenario_id = st.text_input("Scenario ID", value=f"S{index + 1}", key=f"pc_recovery_id_{index}")
            name = st.text_input("Scenario name", value="", key=f"pc_recovery_name_{index}")
            saving = st.number_input("Estimated days saved", min_value=0.0, value=0.0, step=1.0, key=f"pc_recovery_saving_{index}")
            cost = st.number_input("Incremental cost", min_value=0.0, value=0.0, step=1000.0, key=f"pc_recovery_cost_{index}")
            risk = st.number_input("Risk score (0–100)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key=f"pc_recovery_risk_{index}")
            scenarios.append({
                "scenario_id": scenario_id,
                "name": name,
                "duration_saving_days": saving,
                "incremental_cost": cost,
                "risk_score": risk,
            })

    if not st.button("Compare recovery scenarios", key="pc_recovery_compare"):
        return None
    if any(not str(row["name"]).strip() for row in scenarios):
        st.warning("Enter a name for every scenario before comparison.")
        return {"status": "INPUT_REQUIRED"}
    try:
        result = compare_recovery_scenarios(
            scenarios,
            current_forecast_duration_days=current_duration,
            target_duration_days=target_duration if target_duration > 0 else None,
        )
    except (TypeError, ValueError) as exc:
        st.error(str(exc))
        return {"status": "INVALID_INPUT", "message": str(exc)}

    st.markdown("#### Ranked scenario comparison")
    st.dataframe(result["scenarios"], use_container_width=True, hide_index=True)
    st.json(result["summary"])
    st.info(result["method"])
    st.warning("Before approval, validate resource capacity, CPM network effects, safety, quality, contract constraints, and cost authorization.")
    return result
