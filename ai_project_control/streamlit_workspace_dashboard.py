"""Reusable Streamlit project workspace dashboard component."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .data_quality_validation import TABLE_KEYS
from .portfolio_executive_report import build_portfolio_executive_report
from .workspace_service import build_workspace_overview
from .streamlit_recovery_scenario_planner import render_recovery_scenario_planner
from .resource_loading_summary import build_resource_loading_summary
from .manpower_equipment_planner import build_manpower_equipment_plan
from .boq_schedule_resource_integration import build_boq_schedule_resource_integration
from .cost_forecast import build_cost_forecast


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

    st.markdown("#### Cost Forecast Scenarios")
    try:
        cost_forecast = build_cost_forecast(evm)
        if cost_forecast["status"] == "INSUFFICIENT_DATA":
            st.info("Cost forecast belum dapat dihitung. Lengkapi PV, EV, AC, BAC, dan mata uang proyek.")
            st.caption("Data gaps: " + ", ".join(cost_forecast["data_gaps"]))
        elif cost_forecast["status"] == "REVIEW_REQUIRED":
            st.warning("Earned Value melebihi BAC. Periksa baseline, pengukuran progres, dan perubahan lingkup sebelum membuat forecast.")
        else:
            st.caption(f"Mata uang: {cost_forecast['currency']} | CPI: {cost_forecast['cpi']} | SPI: {cost_forecast['spi']}")
            st.dataframe(cost_forecast["scenarios"], use_container_width=True, hide_index=True)
            st.caption("Tiga skenario EAC adalah estimasi berbasis kinerja, bukan komitmen biaya atau anggaran revisi yang disetujui.")
    except (TypeError, ValueError) as exc:
        st.error("Cost forecast data needs correction: " + str(exc))


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

    st.markdown("#### Resource Loading & Capacity")
    try:
        resource_result = build_resource_loading_summary(result["workspace"]["resources"])
        if resource_result["status"] == "NO_DATA":
            st.info("No resource loading records are stored. Import resource_id, period, planned_units, actual_units, and capacity_units to assess capacity.")
        else:
            r1, r2, r3 = st.columns(3)
            r1.metric("Resource-period rows", len(resource_result["rows"]))
            r2.metric("Overloaded rows", resource_result["overloaded_count"])
            r3.metric("Unassessed rows", resource_result["unassessed_count"])
            st.dataframe(resource_result["rows"], use_container_width=True, hide_index=True)
            st.caption("Utilization is calculated only where demand and positive capacity are complete. Missing capacity is unassessed, not zero.")
            if resource_result["overloaded_count"]:
                st.warning("Resource demand exceeds declared capacity in one or more periods. Review assignments and approved working calendars before changing the baseline.")
            if resource_result["unassessed_count"]:
                st.info("Some resource-period records cannot be assessed because demand or capacity data is incomplete.")
    except (TypeError, ValueError) as exc:
        st.error("Resource loading data needs correction: " + str(exc))

    st.markdown("#### Manpower & Equipment Planning")
    try:
        planning_result = build_manpower_equipment_plan(result["workspace"]["resources"])
        if planning_result["status"] == "NO_DATA":
            st.info("No manpower/equipment records are stored yet. Add resource_type, resource_id, period, unit, planned_units, actual_units, and capacity_units to assess the plan.")
        else:
            p1, p2, p3 = st.columns(3)
            p1.metric("Resource-period records", len(planning_result["rows"]))
            p2.metric("Overloaded records", planning_result["overloaded_count"])
            p3.metric("Unassessed records", planning_result["unassessed_count"])
            st.dataframe(planning_result["type_summary"], use_container_width=True, hide_index=True)
            st.dataframe(planning_result["rows"], use_container_width=True, hide_index=True)
            st.caption("Manpower and equipment remain separated by resource type and unit. The planner does not infer shifts, productivity, overtime, or labor cost.")
            if planning_result["overloaded_count"]:
                st.warning("Some manpower/equipment periods exceed declared capacity. Validate rosters, equipment availability, maintenance, and working calendars before approving changes.")
            if planning_result["unassessed_count"]:
                st.info("Some records are not assessable because demand or positive capacity data is incomplete.")
    except (TypeError, ValueError) as exc:
        st.error("Manpower/equipment data needs correction: " + str(exc))

    st.markdown("#### BOQ – Schedule – Resource Integration")
    try:
        integration = build_boq_schedule_resource_integration(
            result["workspace"]["boq"],
            result["workspace"]["activities"],
            result["workspace"]["resources"],
        )
        if integration["status"] == "NO_LINKED_ACTIVITIES":
            st.info("Belum ada aktivitas yang dapat dihubungkan. Isi activity_id yang sama pada BOQ, Activities, dan Resources untuk membangun keterkaitan.")
        elif integration["status"] == "INVALID_SCHEDULE":
            st.error("Integrasi dihentikan karena jaringan jadwal tidak valid: " + "; ".join(integration["issues"]))
        else:
            i1, i2, i3 = st.columns(3)
            i1.metric("Linked activity rows", len(integration["rows"]))
            i2.metric("Unlinked BOQ items", len(integration["unlinked_boq"]))
            i3.metric("Unlinked resource records", len(integration["unlinked_resources"]))
            st.dataframe(integration["rows"], use_container_width=True, hide_index=True)
            if integration["unlinked_boq"]:
                st.warning("BOQ items without a valid activity_id: " + ", ".join(integration["unlinked_boq"]))
            if integration["unlinked_resources"]:
                st.warning("Resource records without a valid activity_id: " + ", ".join(integration["unlinked_resources"]))
            st.caption("BOQ units and resource units are not added across unlike measures. CPM dates are relative working-day offsets, not calendar dates. No productivity or resource demand is inferred.")
    except (TypeError, ValueError) as exc:
        st.error("BOQ/schedule/resource integration data needs correction: " + str(exc))

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

    with st.expander("Recovery Scenario Planner", expanded=False):
        render_recovery_scenario_planner()

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
