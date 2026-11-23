"""Reusable Streamlit project workspace dashboard component."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .data_quality_validation import TABLE_KEYS
from .portfolio_executive_report import build_portfolio_executive_report
from .workspace_service import build_workspace_overview


def render_project_workspace_dashboard(
    database_path: str | Path = ".project_control/project_control.sqlite3",
) -> dict[str, Any] | None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is required to render this component.") from exc

    st.subheader("Project Workspace")
    project_id = st.text_input("Project ID to open", key="pc_workspace_project_id").strip()
    if not project_id:
        st.info("Enter a Project ID to inspect its stored workspace.")
        return None
    try:
        result = build_workspace_overview(database_path, project_id)
    except (ValueError, OSError) as exc:
        st.warning(str(exc))
        return {"status": "NOT_AVAILABLE", "message": str(exc)}

    project = result["project"]
    st.markdown(f"### {project.get('project_name') or project_id}")
    st.caption(f"Project ID: {project_id}")
    summary = result["scorecard"]["summary"]
    a, b, c, d = st.columns(4)
    a.metric("Stored records", result["total_records"])
    b.metric("Validation errors", result["validation"]["error_count"])
    c.metric("Validation warnings", result["validation"]["warning_count"])
    d.metric("Performance", summary["assessed_count"] and result["scorecard"]["projects"][0]["performance_score"] or "Not assessed")

    st.markdown("#### Earned Value Management")
    evm = result["evm"]
    evm_cols = st.columns(4)
    for column, label, key in zip(evm_cols, ["PV", "EV", "AC", "BAC"], ["PV", "EV", "AC", "BAC"]):
        value = evm[key]
        column.metric(label, f"{value:,.2f}" if value is not None else "Not available")
    ratio_cols = st.columns(4)
    for column, label, key in zip(ratio_cols, ["SPI", "CPI", "EAC", "VAC"], ["SPI", "CPI", "EAC", "VAC"]):
        value = evm[key]
        column.metric(label, f"{value:,.2f}" if value is not None else "Not available")
    if evm["status"] != "ASSESSED":
        st.warning("EVM is incomplete: " + ", ".join(evm["data_gaps"]))
    st.caption("EAC uses BAC/CPI and assumes current cost efficiency continues. Review method limitations before using forecasts.")

    st.markdown("#### Schedule & Critical Path")
    schedule = result["schedule"]
    if schedule["status"] == "ASSESSED":
        st.metric("Calculated network duration (working days)", schedule["project_duration_days"])
        st.caption("Critical activities: " + ", ".join(schedule["critical_path"]))
        st.dataframe(schedule["activities"], use_container_width=True, hide_index=True)
    elif schedule["status"] == "NO_ACTIVITIES":
        st.info("No activity network is stored. Critical Path cannot yet be assessed.")
    else:
        st.error("Schedule network requires correction: " + "; ".join(schedule["issues"]))

    st.markdown("#### Schedule Delay Early Warning")
    forecast = result["schedule_forecast"]
    if forecast["status"] == "NO_ACTIVITIES":
        st.info("No activities available for schedule delay assessment.")
    else:
        f1, f2, f3 = st.columns(3)
        f1.metric("Delayed activities", len(forecast["delayed_activity_ids"]))
        f2.metric("Unassessed activities", len(forecast["unassessed_activity_ids"]))
        f3.metric(
            "Project delay (calendar days)",
            forecast["project_delay_days"] if forecast["project_delay_days"] is not None else "Not available",
        )
        if forecast["delayed_activity_ids"]:
            st.warning("Delayed / behind-progress activities: " + ", ".join(forecast["delayed_activity_ids"]))
        st.dataframe(forecast["activities"], use_container_width=True, hide_index=True)
        st.caption("Progress variance is percentage points, not a duration forecast. Finish-date delay requires explicit baseline and forecast dates.")

    st.markdown("#### Dataset inventory")
    inventory = [{"Dataset": name, "Records": count} for name, count in result["dataset_counts"].items()]
    st.dataframe(inventory, use_container_width=True, hide_index=True)

    validation = result["validation"]
    if validation["status"] == "INVALID":
        st.error(f"Workspace validation: {validation['status']}")
    elif validation["status"] == "VALID_WITH_WARNINGS":
        st.warning("Workspace validation has warnings.")
    else:
        st.success("Workspace validation passed.")
    if validation["issues"]:
        st.dataframe(validation["issues"], use_container_width=True, hide_index=True)

    st.markdown("#### Recent imports")
    if result["recent_imports"]:
        st.dataframe(result["recent_imports"], use_container_width=True, hide_index=True)
    else:
        st.info("No import events recorded.")

    with st.expander("View stored dataset records"):
        selected = st.selectbox("Dataset", list(TABLE_KEYS), key="pc_workspace_dataset")
        st.dataframe(result["workspace"][selected], use_container_width=True, hide_index=True)

    report = build_portfolio_executive_report(
        [result["scorecard"]["projects"][0]],
        status_date=__import__("datetime").date.today(),
        language="id",
    )
    st.download_button(
        "Download executive summary (Markdown)",
        data=report,
        file_name=f"{project_id}_executive_summary.md",
        mime="text/markdown",
    )
    return result
