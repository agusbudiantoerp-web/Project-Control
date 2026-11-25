"""Reusable Streamlit project workspace dashboard component."""
from __future__ import annotations

from pathlib import Path
import math
from typing import Any

from .data_quality_validation import TABLE_KEYS
from .portfolio_executive_report import build_portfolio_executive_report
from .workspace_service import build_workspace_overview
from .project_store import ProjectStore
from .schedule_baseline_service import create_schedule_baseline, approve_schedule_baseline
from .streamlit_recovery_scenario_planner import render_recovery_scenario_planner
from .resource_loading_summary import build_resource_loading_summary
from .manpower_equipment_planner import build_manpower_equipment_plan
from .boq_schedule_resource_integration import build_boq_schedule_resource_integration
from .cost_forecast import build_cost_forecast
from .risk_cost_simulation import build_risk_cost_simulation
from .risk_adjusted_project_outlook import build_risk_adjusted_project_outlook
from .project_director_review import build_project_director_review
from .portfolio_command_center import build_portfolio_command_center
from .portfolio_workspace_intelligence import build_stored_portfolio_risk_resource_view
from .coo_portfolio_decision_brief import build_coo_portfolio_decision_brief
from .portfolio_cashflow_workspace import build_stored_portfolio_cashflow_view
from .workspace_config import get_workspace_database_path

def _finite_metric_display(value: Any) -> str:
    """Render missing or non-finite metrics as unavailable, never as 'nan'."""
    if value is None or isinstance(value, bool):
        return "Not available"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not available"
    return f"{number:,.2f}" if math.isfinite(number) else "Not available"


def _performance_display_value(summary: dict[str, Any], projects: list[dict[str, Any]]) -> Any:
    """Return the assessed score without treating a valid zero as missing."""
    if not summary.get("assessed_count") or not projects:
        return "Not assessed"
    score = projects[0].get("performance_score")
    if score is None or isinstance(score, bool):
        return "Not assessed"
    try:
        return score if math.isfinite(float(score)) else "Not assessed"
    except (TypeError, ValueError):
        return "Not assessed"

from .portfolio_monitoring import PortfolioMonitoringStore
from .project_recovery_intelligence import build_project_recovery_intelligence
from .recovery_execution import RecoveryPlanStore, evaluate_recovery_plan
from .recovery_effectiveness import evaluate_recovery_effectiveness
from .recovery_evm_bridge import evaluate_recovery_evm
from .schedule_cost_outlook import build_schedule_cost_outlook
from .schedule_risk_simulation import simulate_schedule_risk
from .risk_exposure_matrix import build_risk_exposure_matrix
from .risk_mitigation_store import RiskMitigationStore
from .risk_governance_bridge import build_risk_governance_view
from .recovery_resource_planner import estimate_resource_recovery
from .recovery_decision_engine import build_recovery_decision_brief
from .predictive_early_warning import forecast_project_control_trends
from .project_performance_history import ProjectPerformanceHistoryStore
import json
from .action_register_store import ActionRegisterStore
from .action_escalation import build_action_escalations
from .telegram_executive_reporting import (
    build_telegram_executive_message,
    send_telegram_executive_message,
)
from .integrated_executive_report import build_integrated_executive_report
from .executive_report_export import (
    build_executive_report_pdf,
    build_executive_report_xlsx,
)


def render_project_workspace_dashboard(
    database_path: str | Path | None = None,
    project_id: str | None = None,
) -> dict[str, Any] | None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is required to render this component.") from exc

    if database_path is None:
        database_path = get_workspace_database_path()
    portfolio: dict[str, Any] = {"projects": []}
    portfolio_intelligence: dict[str, Any] = {"top_risks": [], "shared_resource_conflicts": [], "expected_exposure_by_currency": {}, "risk_count_unassessed": 0, "unassessed_resources": []}
    portfolio_actions: dict[str, Any] = {"actions": [], "summary": {"action_count": 0, "open_count": 0, "in_progress_count": 0, "blocked_count": 0, "overdue_count": 0}}

    st.subheader("Project Portfolio Command Center")
    try:
        portfolio = build_portfolio_command_center(database_path)
        if portfolio["status"] == "NO_PROJECTS":
            st.info("Belum ada proyek tersimpan di workspace lokal ini.")
        else:
            summary = portfolio["performance_scorecard"]["summary"]
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Projects", portfolio["project_count"])
            p2.metric("P1 priority", portfolio["decision_summary"]["p1_count"])
            p3.metric("P2 priority", portfolio["decision_summary"]["p2_count"])
            p4.metric("Insufficient EVM data", summary["insufficient_data_count"])
            st.dataframe(portfolio["projects"], use_container_width=True, hide_index=True)
            st.caption("Budget totals by currency: " + " | ".join(
                f"{currency} {amount:,.2f}"
                for currency, amount in portfolio["budget_by_currency"].items()
            ))
            if portfolio["status"] == "INSUFFICIENT_DATA":
                st.warning("Sebagian proyek belum memiliki SPI/CPI yang cukup. Proyek tersebut tetap ditampilkan sebagai UNASSESSED.")
            with st.expander("Portfolio governance and limitations"):
                for limitation in portfolio["limitations"]:
                    st.write("• " + limitation)
    except (TypeError, ValueError, OSError) as exc:
        st.warning("Portfolio command center unavailable: " + str(exc))

    st.subheader("Portfolio-wide Risk & Shared Resource Intelligence")
    try:
        portfolio_intelligence = build_stored_portfolio_risk_resource_view(database_path)
        ri1, ri2, ri3, ri4 = st.columns(4)
        ri1.metric("Assessed risks", portfolio_intelligence["risk_count_assessed"])
        ri2.metric("Unassessed risks", portfolio_intelligence["risk_count_unassessed"])
        ri3.metric("Shared resource periods", portfolio_intelligence["shared_resource_period_count"])
        ri4.metric("Cross-project overloads", portfolio_intelligence["shared_resource_conflict_count"])
        if portfolio_intelligence["expected_exposure_by_currency"]:
            st.caption("Expected exposure by currency: " + " | ".join(
                f"{currency} {amount:,.2f}"
                for currency, amount in portfolio_intelligence["expected_exposure_by_currency"].items()
            ))
        if portfolio_intelligence["top_risks"]:
            st.markdown("**Highest expected risk exposures (separated by currency)**")
            st.dataframe(portfolio_intelligence["top_risks"], use_container_width=True, hide_index=True)
        if portfolio_intelligence["shared_resource_conflicts"]:
            st.markdown("**Cross-project shared-resource capacity checks**")
            st.dataframe(portfolio_intelligence["shared_resource_conflicts"], use_container_width=True, hide_index=True)
        if portfolio_intelligence["unassessed_risks"] or portfolio_intelligence["unassessed_resources"]:
            with st.expander("Unassessed portfolio records"):
                st.write("Risks")
                st.dataframe(portfolio_intelligence["unassessed_risks"], use_container_width=True, hide_index=True)
                st.write("Resources")
                st.dataframe(portfolio_intelligence["unassessed_resources"], use_container_width=True, hide_index=True)
        with st.expander("Portfolio risk/resource limitations"):
            for limitation in portfolio_intelligence["limitations"]:
                st.write("• " + limitation)
    except (TypeError, ValueError, OSError, KeyError) as portfolio_intelligence_error:
        st.warning("Portfolio risk/resource intelligence unavailable: " + str(portfolio_intelligence_error))

    st.subheader("Portfolio Change Monitoring")
    try:
        current_projects = portfolio.get("projects", []) if isinstance(portfolio, dict) else []
        st.caption("Snapshot disimpan hanya saat tombol ditekan. Perbandingan menggunakan snapshot sebelumnya pada database workspace lokal.")
        if st.button("Capture & compare portfolio snapshot", key="pc_capture_monitor_snapshot"):
            monitoring = PortfolioMonitoringStore(database_path)
            monitoring_result = monitoring.compare_with_previous(current_projects)
            st.metric("Adverse changes detected", monitoring_result["change_count"])
            if monitoring_result["changes"]:
                st.dataframe(monitoring_result["changes"], use_container_width=True, hide_index=True)
                st.warning("Perubahan ini adalah sinyal untuk ditinjau, bukan diagnosis penyebab atau instruksi mengubah baseline.")
            elif monitoring_result["previous_snapshot_available"]:
                st.success("Tidak ada perubahan adverse material dibanding snapshot sebelumnya.")
            else:
                st.info("Snapshot pertama tersimpan. Ambil snapshot berikutnya untuk mulai membandingkan perubahan.")
            with st.expander("Monitoring limitations"):
                for limitation in monitoring_result["limitations"]:
                    st.write("• " + limitation)
    except (TypeError, ValueError, OSError) as monitor_error:
        st.warning("Portfolio monitoring unavailable: " + str(monitor_error))

    st.subheader("Portfolio-wide Executive Actions")
    try:
        portfolio_actions = ActionRegisterStore(database_path).list_portfolio()
        pa = portfolio_actions["summary"]
        pa1, pa2, pa3, pa4 = st.columns(4)
        pa1.metric("Total actions", pa["action_count"])
        pa2.metric("Open / In progress", pa["open_count"] + pa["in_progress_count"])
        pa3.metric("Blocked", pa["blocked_count"])
        pa4.metric("Overdue", pa["overdue_count"])
        if portfolio_actions["actions"]:
            st.dataframe(portfolio_actions["actions"], use_container_width=True, hide_index=True)
        else:
            st.info("No portfolio-wide executive actions recorded yet.")
    except (TypeError, ValueError, OSError) as exc:
        st.warning("Portfolio action register unavailable: " + str(exc))

    st.subheader("COO Executive Portfolio Decision Brief")
    try:
        coo_brief = build_coo_portfolio_decision_brief(
            portfolio, portfolio_intelligence, portfolio_actions
        )
        cb1, cb2, cb3, cb4 = st.columns(4)
        cb1.metric("Projects requiring review", coo_brief["projects_requiring_review"])
        cb2.metric("Overdue executive actions", coo_brief["executive_action_summary"].get("overdue_count", 0))
        cb3.metric("Shared resource conflicts", len(coo_brief["shared_resource_conflicts"]))
        cb4.metric("Unassessed risks", coo_brief["unassessed_risk_count"])
        if coo_brief["projects_for_review"]:
            st.dataframe(coo_brief["projects_for_review"], use_container_width=True, hide_index=True)
        st.markdown("**Recommended management reviews**")
        for recommendation in coo_brief["recommended_management_reviews"]:
            st.write("• " + recommendation)
        with st.expander("COO decision brief governance notes"):
            for note in coo_brief["governance_notes"]:
                st.caption("• " + note)
    except (TypeError, ValueError, KeyError) as coo_error:
        st.warning("COO executive brief unavailable: " + str(coo_error))

    st.subheader("Portfolio Cost & Cashflow Intelligence")
    try:
        cashflow_view = build_stored_portfolio_cashflow_view(database_path)
        cf1, cf2, cf3 = st.columns(3)
        cf1.metric("Projects with cost data", cashflow_view["project_count_assessed"])
        cf2.metric("Projects over supplied budget", cashflow_view["projects_over_budget"])
        cf3.metric("Projects with unassessed finance", cashflow_view["project_count_unassessed"])
        if cashflow_view["totals_by_currency"]:
            st.markdown("**Portfolio cost totals by currency**")
            st.dataframe([
                {"Currency": currency, **values}
                for currency, values in cashflow_view["totals_by_currency"].items()
            ], use_container_width=True, hide_index=True)
        if cashflow_view["projects"]:
            st.dataframe(cashflow_view["projects"], use_container_width=True, hide_index=True)
        if cashflow_view["unassessed_projects"]:
            with st.expander("Projects with incomplete financial data"):
                st.dataframe(cashflow_view["unassessed_projects"], use_container_width=True, hide_index=True)
        with st.expander("Cashflow methodology and limitations"):
            for limitation in cashflow_view["limitations"]:
                st.caption("• " + limitation)
    except (TypeError, ValueError, OSError, KeyError) as cashflow_error:
        st.warning("Portfolio cost/cashflow intelligence unavailable: " + str(cashflow_error))

    st.subheader("Project Recovery Intelligence")
    try:
        recovery_projects = portfolio.get("projects", []) if isinstance(portfolio, dict) else []
        recovery_result = build_project_recovery_intelligence(
            recovery_projects,
            actions=portfolio_actions.get("actions", []),
        )
        ri1, ri2, ri3 = st.columns(3)
        ri1.metric("Projects assessed", recovery_result["project_count"])
        ri2.metric("Critical review", recovery_result["critical_review_count"])
        ri3.metric("Recovery review", recovery_result["recovery_review_count"])
        if recovery_result["projects"]:
            st.dataframe(recovery_result["projects"], use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada proyek untuk dinilai.")
        with st.expander("Recovery intelligence methodology and limitations"):
            for limitation in recovery_result["limitations"]:
                st.write("• " + limitation)
    except (TypeError, ValueError) as recovery_error:
        st.warning("Project recovery intelligence unavailable: " + str(recovery_error))

    st.subheader("Historical Project Performance & Dataset Builder")
    try:
        history_store = ProjectPerformanceHistoryStore(database_path)
        with st.expander("Record a dated KPI snapshot", expanded=False):
            st.caption("Simpan data aktual per tanggal pelaporan. Satu proyek hanya boleh memiliki satu snapshot per tanggal. Jangan masukkan data perkiraan sebagai realisasi.")
            default_history_json = """{
  "project_id": "PROJECT-001",
  "reporting_date": "2026-11-24",
  "currency": "IDR",
  "SPI": 0.98,
  "CPI": 0.96,
  "risk_score": 45,
  "delayed_activity_count": 2,
  "overdue_action_count": 1,
  "planned_value": 1000000000,
  "earned_value": 980000000,
  "actual_cost": 1020000000,
  "remaining_work_units": 2500,
  "daily_productivity": 125
}"""
            with st.form("pc_history_snapshot_form"):
                history_json = st.text_area("Actual project snapshot JSON", value=default_history_json, height=220, key="pc_history_snapshot_json")
                save_history = st.form_submit_button("Save historical snapshot")
            if save_history:
                try:
                    saved_history = history_store.save(json.loads(history_json))
                    st.success("Snapshot saved: " + saved_history["project_id"] + " / " + saved_history["reporting_date"])
                except (TypeError, ValueError, KeyError) as history_error:
                    st.error("Snapshot was not saved: " + str(history_error))
        history_rows = history_store.list_snapshots()
        h1, h2 = st.columns(2)
        h1.metric("Stored KPI snapshots", len(history_rows))
        h2.metric("Projects with history", len({row["project_id"] for row in history_rows}))
        if history_rows:
            st.dataframe(history_rows, use_container_width=True, hide_index=True)
        if st.button("Evaluate historical KPI ML baselines", key="pc_train_historical_kpi_models"):
            try:
                training_dataset = history_store.build_next_snapshot_dataset()
                training_result = train_historical_kpi_models(training_dataset["rows"])
                st.metric("Model evaluation status", training_result["status"])
                if training_result["metrics"]:
                    st.dataframe(training_result["metrics"], use_container_width=True, hide_index=True)
                st.caption(training_result.get("model_family", "No model trained"))
                with st.expander("Model evaluation limitations"):
                    for limitation in training_result["limitations"]:
                        st.write("• " + limitation)
                if training_result["status"] == "INSUFFICIENT_HISTORY":
                    st.info("Histori proyek belum cukup untuk melatih dan mengevaluasi model secara bertanggung jawab.")
            except (TypeError, ValueError, RuntimeError) as training_error:
                st.error("Historical KPI model evaluation unavailable: " + str(training_error))
        if st.button("Build next-snapshot learning dataset", key="pc_build_history_dataset"):
            dataset_result = history_store.build_next_snapshot_dataset()
            st.metric("Usable next-snapshot rows", dataset_result["row_count"])
            st.caption(dataset_result["target_definition"])
            if dataset_result["rows"]:
                st.dataframe(dataset_result["rows"], use_container_width=True, hide_index=True)
                st.download_button(
                    "Download learning dataset CSV",
                    data=history_store.export_dataset_csv(),
                    file_name="project_performance_learning_dataset.csv",
                    mime="text/csv",
                    key="pc_download_history_dataset",
                )
            else:
                st.info("Belum ada dua snapshot berurutan dengan mata uang yang sama untuk membentuk satu baris dataset.")
            with st.expander("Dataset governance and limitations"):
                for limitation in dataset_result["limitations"]:
                    st.write("• " + limitation)
    except (TypeError, ValueError, OSError) as history_error:
        st.warning("Project performance history unavailable: " + str(history_error))

    st.subheader("Predictive Project Early Warning")
    with st.expander("Forecast KPI trend from dated project snapshots", expanded=False):
        st.caption("Masukkan minimal tiga snapshot bertanggal untuk setiap KPI yang ingin diproyeksikan. Data contoh di bawah hanya format input, bukan data proyek aktual.")
        if st.button("Run forecast from saved historical KPI snapshots", key="pc_forecast_saved_history"):
            try:
                saved_rows = ProjectPerformanceHistoryStore(database_path).list_snapshots()
                saved_snapshots = [
                    {
                        "date": row["reporting_date"],
                        "project_id": row["project_id"],
                        **{metric: row.get(metric) for metric in (
                            "SPI", "CPI", "risk_score", "delayed_activity_count",
                            "overdue_action_count",
                        )},
                    }
                    for row in saved_rows
                ]
                saved_forecast = forecast_project_control_trends(saved_snapshots, horizon_days=30)
                st.metric("Projects assessed from stored history", saved_forecast["project_count"])
                for saved_project in saved_forecast["projects"]:
                    st.markdown("**Project: " + saved_project["project_id"] + "**")
                    st.metric("Signals requiring attention", saved_project["attention_metric_count"])
                    st.dataframe(saved_project["metrics"], use_container_width=True, hide_index=True)
                if saved_forecast["status"] == "NO_SNAPSHOTS":
                    st.info("Belum ada histori KPI tersimpan.")
                with st.expander("Saved-history forecast limitations"):
                    for limitation in saved_forecast["limitations"]:
                        st.write("• " + limitation)
            except (TypeError, ValueError, KeyError, OSError) as saved_forecast_error:
                st.error("Forecast from stored history unavailable: " + str(saved_forecast_error))

        default_trend_json = """[
  {"date":"2026-10-01","project_id":"PROJECT-001","SPI":1.02,"CPI":1.01,"risk_score":25,"delayed_activity_count":0,"overdue_action_count":0},
  {"date":"2026-10-15","project_id":"PROJECT-001","SPI":0.99,"CPI":0.98,"risk_score":35,"delayed_activity_count":1,"overdue_action_count":0},
  {"date":"2026-11-01","project_id":"PROJECT-001","SPI":0.96,"CPI":0.95,"risk_score":55,"delayed_activity_count":2,"overdue_action_count":1}
]"""
        with st.form("pc_predictive_early_warning_form"):
            trend_horizon = st.selectbox("Forecast horizon (calendar days)", [7, 14, 30, 60, 90], index=2, key="pc_trend_horizon")
            trend_json = st.text_area("Dated KPI snapshots JSON", value=default_trend_json, height=190, key="pc_trend_snapshots")
            run_trend_forecast = st.form_submit_button("Run predictive early warning")
        if run_trend_forecast:
            try:
                trend_snapshots = json.loads(trend_json)
                trend_result = forecast_project_control_trends(
                    trend_snapshots, horizon_days=int(trend_horizon),
                )
                st.metric("Projects assessed", trend_result["project_count"])
                for project_trend in trend_result["projects"]:
                    st.markdown("**Project: " + project_trend["project_id"] + "**")
                    st.metric("KPI signals requiring attention", project_trend["attention_metric_count"])
                    st.dataframe(project_trend["metrics"], use_container_width=True, hide_index=True)
                with st.expander("Forecast method and limitations"):
                    st.caption(trend_result["method"])
                    for limitation in trend_result["limitations"]:
                        st.write("• " + limitation)
            except (TypeError, ValueError, KeyError) as trend_error:
                st.error("Predictive early warning input needs correction: " + str(trend_error))

    st.subheader("Resource-Based Recovery Estimator")
    with st.expander("Estimate additional manpower/equipment impact", expanded=False):
        st.caption("Masukkan produktivitas dan biaya berdasarkan estimasi yang sudah divalidasi tim proyek. Hasil ini adalah estimasi work-package, bukan simulasi CPM.")
        with st.form("pc_resource_recovery_estimator_form"):
            rr1, rr2 = st.columns(2)
            with rr1:
                rr_work = st.number_input("Remaining work units", min_value=0.01, value=1000.0, step=100.0)
                rr_base_rate = st.number_input("Current productivity per working day", min_value=0.01, value=50.0, step=5.0)
                rr_crews = st.number_input("Additional crews", min_value=0, value=0, step=1)
                rr_crew_rate = st.number_input("Productivity per additional crew/day", min_value=0.0, value=0.0, step=1.0)
            with rr2:
                rr_equipment = st.number_input("Additional equipment units", min_value=0, value=0, step=1)
                rr_equipment_rate = st.number_input("Productivity per additional equipment/day", min_value=0.0, value=0.0, step=1.0)
                rr_efficiency = st.number_input("Added-resource efficiency factor (0–1)", min_value=0.01, max_value=1.0, value=0.8, step=0.05)
                rr_days_week = st.number_input("Working days per week", min_value=1, max_value=7, value=5, step=1)
            rr_base_cost = st.number_input("Current daily cost", min_value=0.0, value=0.0, step=100000.0)
            rr_crew_cost = st.number_input("Daily cost per additional crew", min_value=0.0, value=0.0, step=100000.0)
            rr_equipment_cost = st.number_input("Daily cost per additional equipment", min_value=0.0, value=0.0, step=100000.0)
            rr_currency = st.text_input("Cost currency", value="IDR", key="pc_rr_currency")
            run_resource_estimate = st.form_submit_button("Calculate resource recovery")
        if run_resource_estimate:
            try:
                rr_result = estimate_resource_recovery(
                    remaining_work_units=rr_work,
                    current_daily_productivity=rr_base_rate,
                    additional_crew_count=rr_crews,
                    productivity_per_additional_crew=rr_crew_rate,
                    additional_equipment_count=rr_equipment,
                    productivity_per_additional_equipment=rr_equipment_rate,
                    efficiency_factor=rr_efficiency,
                    current_daily_cost=rr_base_cost,
                    additional_crew_daily_cost=rr_crew_cost,
                    additional_equipment_daily_cost=rr_equipment_cost,
                    working_days_per_week=rr_days_week,
                    currency=rr_currency,
                )
                base_days = rr_result["baseline"]["duration_working_days"]
                recovery_days = rr_result["recovery"]["duration_working_days"]
                m1, m2, m3 = st.columns(3)
                m1.metric("Baseline duration (working days)", base_days)
                m2.metric("Recovery duration (working days)", recovery_days, delta=round(recovery_days - base_days, 2))
                m3.metric("Estimated days saved", rr_result["recovery"]["days_saved"])
                st.json(rr_result["recovery"])
                st.caption(f"Estimated incremental cost: {rr_result['currency']} {rr_result['recovery']['incremental_cost_vs_baseline']:,.2f}")
                with st.expander("Assumptions and limitations"):
                    for assumption in rr_result["assumptions"]:
                        st.write("• " + assumption)
            except (TypeError, ValueError) as rr_error:
                st.error("Resource recovery estimate failed: " + str(rr_error))

    st.subheader("Recovery Execution Tracker")
    try:
        recovery_store = RecoveryPlanStore(database_path)
        available_recovery_projects = portfolio.get("projects", []) if isinstance(portfolio, dict) else []
        project_options = {
            str(row.get("project_id")): str(row.get("project_name") or row.get("project_id"))
            for row in available_recovery_projects if row.get("project_id")
        }
        if project_options:
            selected_recovery_project = st.selectbox(
                "Project for recovery tracking", list(project_options.keys()),
                format_func=lambda key: project_options[key], key="pc_recovery_project_select",
            )
            with st.expander("Create a recovery plan"):
                with st.form("pc_create_recovery_plan_form"):
                    plan_title = st.text_input("Recovery plan title")
                    plan_owner = st.text_input("Accountable owner")
                    plan_start = st.date_input("Plan start date")
                    plan_target_finish = st.date_input("Recovery target finish")
                    plan_baseline_finish = st.date_input("Approved baseline finish")
                    first_milestone_name = st.text_input("First milestone")
                    first_milestone_due = st.date_input("First milestone due date")
                    first_milestone_target = st.number_input("Milestone target progress (%)", min_value=0.0, max_value=100.0, value=100.0, step=5.0)
                    create_plan_clicked = st.form_submit_button("Create recovery plan")
                if create_plan_clicked:
                    try:
                        if not plan_title.strip() or not plan_owner.strip() or not first_milestone_name.strip():
                            raise ValueError("Title, owner and milestone name are required.")
                        recovery_store.create(
                            project_id=selected_recovery_project, title=plan_title,
                            owner=plan_owner, start_date=plan_start,
                            target_finish=plan_target_finish, baseline_finish=plan_baseline_finish,
                            milestones=[{
                                "milestone_id": "M1", "name": first_milestone_name,
                                "due_date": first_milestone_due, "target_percent": first_milestone_target,
                                "owner": plan_owner,
                            }],
                        )
                        st.success("Recovery plan created. Refresh the dashboard to load it.")
                    except (TypeError, ValueError, OSError) as create_error:
                        st.error("Recovery plan not created: " + str(create_error))
            existing_plans = recovery_store.list_project(selected_recovery_project)
            if existing_plans:
                plan_labels = {row["plan_id"]: row["title"] for row in existing_plans}
                selected_plan_id = st.selectbox(
                    "Recovery plan", list(plan_labels.keys()),
                    format_func=lambda key: plan_labels[key], key="pc_recovery_plan_select",
                )
                selected_plan = recovery_store.get(selected_plan_id)
                plan = selected_plan["plan"]
                evaluation = evaluate_recovery_plan(plan)
                r1, r2, r3 = st.columns(3)
                r1.metric("Milestones", evaluation["milestone_count"])
                r2.metric("Completed", evaluation["completed_count"])
                r3.metric("Overdue", evaluation["overdue_count"])
                st.metric("Average progress gap (percentage points)", evaluation["progress_gap_percentage_points"])
                st.dataframe(plan["milestones"], use_container_width=True, hide_index=True)
                with st.expander("Record milestone progress"):
                    milestone_labels = {m["milestone_id"]: m["name"] for m in plan["milestones"]}
                    milestone_id = st.selectbox("Milestone", list(milestone_labels.keys()),
                                                format_func=lambda key: milestone_labels[key], key="pc_recovery_milestone")
                    actual_percent = st.number_input("Actual progress (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0, key="pc_recovery_actual")
                    milestone_status = st.selectbox("Milestone status", ["NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETED"], key="pc_recovery_status")
                    changed_by = st.text_input("Recorded by", key="pc_recovery_actor")
                    progress_note = st.text_area("Evidence / progress note", key="pc_recovery_note")
                    if st.button("Save recovery progress", key="pc_save_recovery_progress"):
                        try:
                            recovery_store.update_milestone(
                                selected_plan_id, milestone_id, actual_percent=actual_percent,
                                status=milestone_status, changed_by=changed_by, note=progress_note,
                            )
                            st.success("Progress and audit event saved. Refresh the dashboard to view the updated plan.")
                        except (KeyError, TypeError, ValueError, OSError) as update_error:
                            st.error("Progress not saved: " + str(update_error))
                with st.expander("Recovery progress audit history"):
                    st.dataframe(selected_plan["events"], use_container_width=True, hide_index=True)
                with st.expander("Tracker limitations"):
                    for limitation in evaluation["limitations"]:
                        st.write("• " + limitation)
            else:
                st.info("Belum ada recovery plan untuk proyek ini. Buat rencana dengan milestones yang disetujui melalui modul recovery plan.")
        else:
            st.info("Tambahkan proyek ke workspace sebelum menggunakan recovery tracker.")
    except (TypeError, ValueError, OSError) as tracker_error:
        st.warning("Recovery execution tracker unavailable: " + str(tracker_error))

    st.subheader("Recovery Effectiveness Scorecard")
    with st.expander("Compare project indicators before and after recovery"):
        with st.form("pc_recovery_effectiveness_form"):
            st.caption("Masukkan indikator dari dua periode pelaporan yang sebanding. Nilai 0 adalah angka valid; ganti nilai awal sesuai data aktual sebelum menghitung.")
            before_col, after_col = st.columns(2)
            with before_col:
                st.markdown("**Before recovery**")
                before_spi = st.number_input("SPI before", min_value=0.0, value=0.0, step=0.01, key="pc_eff_b_spi")
                before_cpi = st.number_input("CPI before", min_value=0.0, value=0.0, step=0.01, key="pc_eff_b_cpi")
                before_risk = st.number_input("Risk score before", min_value=0.0, value=0.0, step=1.0, key="pc_eff_b_risk")
                before_delay = st.number_input("Delayed activities before", min_value=0, value=0, step=1, key="pc_eff_b_delay")
                before_overdue = st.number_input("Overdue actions before", min_value=0, value=0, step=1, key="pc_eff_b_overdue")
            with after_col:
                st.markdown("**After recovery**")
                after_spi = st.number_input("SPI after", min_value=0.0, value=0.0, step=0.01, key="pc_eff_a_spi")
                after_cpi = st.number_input("CPI after", min_value=0.0, value=0.0, step=0.01, key="pc_eff_a_cpi")
                after_risk = st.number_input("Risk score after", min_value=0.0, value=0.0, step=1.0, key="pc_eff_a_risk")
                after_delay = st.number_input("Delayed activities after", min_value=0, value=0, step=1, key="pc_eff_a_delay")
                after_overdue = st.number_input("Overdue actions after", min_value=0, value=0, step=1, key="pc_eff_a_overdue")
            approved_budget = st.number_input("Approved recovery budget", min_value=0.0, value=0.0, step=1000000.0, key="pc_eff_budget")
            actual_recovery_cost = st.number_input("Actual recovery cost", min_value=0.0, value=0.0, step=1000000.0, key="pc_eff_cost")
            recovery_currency = st.text_input("Currency (e.g. IDR)", value="IDR", key="pc_eff_currency")
            assess_effectiveness = st.form_submit_button("Evaluate recovery effectiveness")
        if assess_effectiveness:
            before_values = {"SPI": before_spi, "CPI": before_cpi,
                             "risk_score": before_risk,
                             "delayed_activity_count": before_delay,
                             "overdue_action_count": before_overdue}
            after_values = {"SPI": after_spi, "CPI": after_cpi,
                            "risk_score": after_risk,
                            "delayed_activity_count": after_delay,
                            "overdue_action_count": after_overdue}
            try:
                effectiveness = evaluate_recovery_effectiveness(
                    before_values, after_values,
                    approved_recovery_budget=approved_budget,
                    actual_recovery_cost=actual_recovery_cost,
                    currency=recovery_currency,
                )
                st.metric("Recovery indicator outcome", effectiveness["status"])
                st.json(effectiveness["indicator_summary"])
                st.dataframe(
                    [{"Indicator": key, **value} for key, value in effectiveness["comparisons"].items()],
                    use_container_width=True, hide_index=True,
                )
                st.json(effectiveness["recovery_cost"])
                for limitation in effectiveness["limitations"]:
                    st.caption("• " + limitation)
            except (TypeError, ValueError) as effectiveness_error:
                st.error("Effectiveness assessment failed: " + str(effectiveness_error))

    st.subheader("EVM-Based Recovery Comparison")
    with st.expander("Compare before/after recovery using EVM"):
        st.caption("Masukkan PV, EV, dan AC untuk masing-masing periode. Nilai kosong akan tetap tidak dinilai. Pastikan data memakai scope, mata uang, dan konvensi periode yang konsisten.")
        with st.form("pc_recovery_evm_comparison_form"):
            evm_project_id = st.text_input("Project ID", key="pc_evm_bridge_project_id")
            evm_bac = st.text_input("Budget at Completion (BAC)", key="pc_evm_bridge_bac")
            evm_currency = st.text_input("Currency", value="IDR", key="pc_evm_bridge_currency")
            before_period = st.text_input("Before period (optional)", key="pc_evm_bridge_before_period")
            after_period = st.text_input("After period (optional)", key="pc_evm_bridge_after_period")
            b1, b2 = st.columns(2)
            with b1:
                st.markdown("**Before recovery**")
                b_pv = st.text_input("PV before", key="pc_evm_b_pv")
                b_ev = st.text_input("EV before", key="pc_evm_b_ev")
                b_ac = st.text_input("AC before", key="pc_evm_b_ac")
            with b2:
                st.markdown("**After recovery**")
                a_pv = st.text_input("PV after", key="pc_evm_a_pv")
                a_ev = st.text_input("EV after", key="pc_evm_a_ev")
                a_ac = st.text_input("AC after", key="pc_evm_a_ac")
            recovery_budget_input = st.text_input("Approved recovery budget (optional)", key="pc_evm_recovery_budget")
            recovery_cost_input = st.text_input("Actual recovery cost (optional)", key="pc_evm_recovery_cost")
            run_evm_bridge = st.form_submit_button("Evaluate EVM recovery")
        if run_evm_bridge:
            try:
                def _optional_number(raw, label):
                    if not str(raw).strip():
                        return None
                    try:
                        return float(raw)
                    except (TypeError, ValueError):
                        raise ValueError(label + " must be numeric or blank.")
                project_input = {"project_id": evm_project_id, "BAC": _optional_number(evm_bac, "BAC"), "currency": evm_currency}
                before_progress = [{"project_id": evm_project_id, "period": before_period or "before",
                                    "planned_value": _optional_number(b_pv, "PV before"),
                                    "earned_value": _optional_number(b_ev, "EV before")}]
                before_cost = [{"project_id": evm_project_id, "period": before_period or "before",
                                "actual_cost": _optional_number(b_ac, "AC before")}]
                after_progress = [{"project_id": evm_project_id, "period": after_period or "after",
                                   "planned_value": _optional_number(a_pv, "PV after"),
                                   "earned_value": _optional_number(a_ev, "EV after")}]
                after_cost = [{"project_id": evm_project_id, "period": after_period or "after",
                               "actual_cost": _optional_number(a_ac, "AC after")}]
                bridge = evaluate_recovery_evm(
                    project_input, before_progress_rows=before_progress,
                    before_actual_cost_rows=before_cost, after_progress_rows=after_progress,
                    after_actual_cost_rows=after_cost,
                    approved_recovery_budget=_optional_number(recovery_budget_input, "Recovery budget"),
                    actual_recovery_cost=_optional_number(recovery_cost_input, "Recovery cost"),
                    before_period=before_period or None, after_period=after_period or None,
                )
                st.metric("EVM comparison status", bridge["status"])
                st.write("**Before recovery**")
                st.json(bridge["before_evm"])
                st.write("**After recovery**")
                st.json(bridge["after_evm"])
                st.write("**Recovery effectiveness**")
                st.json(bridge["recovery_effectiveness"])
                for limitation in bridge["limitations"]:
                    st.caption("• " + limitation)
            except (TypeError, ValueError) as bridge_error:
                st.error("EVM recovery evaluation failed: " + str(bridge_error))

    st.subheader("Executive Report Export")
    try:
        portfolio_data = locals().get("portfolio", {})
        report_projects = portfolio_data.get("projects", []) if isinstance(portfolio_data, dict) else []
        report_records = [
            {
                "project_id": row.get("project_id"),
                "project_name": row.get("project_name"),
                "SPI": row.get("SPI"),
                "CPI": row.get("CPI"),
                "portfolio_status": row.get("priority", row.get("portfolio_status")),
            }
            for row in report_projects
        ]
        report_decisions = {
            "decisions": [
                {
                    "project_name": row.get("project_name"),
                    "priority": row.get("priority"),
                    "evidence_points": row.get("evidence_points"),
                    "recommended_action": row.get("recommended_action"),
                }
                for row in report_projects
            ],
            "summary": portfolio_data.get("decision_summary", {}),
        }
        from datetime import date
        executive_report_text = build_integrated_executive_report(
            portfolio_records=report_records,
            status_date=date.today(),
            director_decisions=report_decisions,
            action_register=portfolio_actions,
        )
        st.caption("Laporan dibuat dari data workspace lokal yang tersedia. Bagian yang datanya tidak tersedia akan ditandai, bukan diperkirakan.")
        ex1, ex2 = st.columns(2)
        ex1.download_button(
            "Unduh Executive Report (Excel)",
            data=build_executive_report_xlsx(executive_report_text),
            file_name="project_control_executive_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="pc_download_exec_xlsx",
        )
        ex2.download_button(
            "Unduh Executive Report (PDF)",
            data=build_executive_report_pdf(executive_report_text),
            file_name="project_control_executive_report.pdf",
            mime="application/pdf",
            key="pc_download_exec_pdf",
        )
    except (TypeError, ValueError, OSError, ImportError) as report_error:
        st.warning("Executive report export belum tersedia: " + str(report_error))

    st.subheader("Governance Escalation Review")
    try:
        escalation_result = build_action_escalations(portfolio_actions["actions"])
        es1, es2, es3 = st.columns(3)
        es1.metric("Escalations", escalation_result["summary"]["escalation_count"])
        es2.metric("Project Director", escalation_result["summary"]["director_count"])
        es3.metric("Project Manager", escalation_result["summary"]["manager_count"])
        if escalation_result["escalations"]:
            st.dataframe(escalation_result["escalations"], use_container_width=True, hide_index=True)
            st.warning("Escalation rows are review recommendations only. No Telegram/email notification or status change is triggered.")
        else:
            st.success("No action escalation is currently indicated by the recorded due dates and statuses.")
        with st.expander("Escalation rules and limitations"):
            for limitation in escalation_result["limitations"]:
                st.write("• " + limitation)

        with st.expander("Telegram Executive Notification", expanded=False):
            st.caption("Pengiriman hanya dilakukan setelah tombol ditekan. Simpan TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di environment secrets aplikasi; jangan tulis token di source code.")
            try:
                import os
                bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
                chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
                if not bot_token or not chat_id:
                    st.info("Telegram belum dikonfigurasi. Tambahkan TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID pada environment secrets untuk mengaktifkan pengiriman.")
                else:
                    report_message = build_telegram_executive_message(
                        project_name="Project Portfolio",
                        status_date=escalation_result["as_of"],
                        action_register=portfolio_actions,
                    )
                    st.text_area("Preview pesan Telegram", report_message, height=180, disabled=True)
                    if st.button("Kirim ringkasan Telegram sekarang", key="pc_send_telegram_exec"):
                        try:
                            send_telegram_executive_message(
                                bot_token=bot_token, chat_id=chat_id, message=report_message
                            )
                            st.success("Pesan Telegram berhasil dikirim.")
                        except Exception:
                            st.error("Pengiriman Telegram gagal. Periksa koneksi aplikasi, token, chat ID, dan log server; token tidak ditampilkan.")
            except (TypeError, ValueError) as config_error:
                st.warning("Telegram notification belum tersedia: " + str(config_error))
    except (TypeError, ValueError) as exc:
        st.warning("Governance escalation review unavailable: " + str(exc))

    st.subheader("Project Workspace")
    if project_id is None:
        project_id = st.text_input("Project ID to open", key="pc_workspace_project_id").strip()
    else:
        project_id = str(project_id).strip()
        if project_id:
            st.caption("Project ID: " + project_id)
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
    d.metric("Performance", _performance_display_value(summary, result["scorecard"]["projects"]))

    st.markdown("#### Earned Value Management")
    evm = result["evm"]
    evm_cols = st.columns(4)
    for column, label, key in zip(evm_cols, ["PV", "EV", "AC", "BAC"], ["PV", "EV", "AC", "BAC"]):
        value = evm[key]
        column.metric(label, _finite_metric_display(value))
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


    st.markdown("#### Approved Schedule Baseline & Change Control")
    baseline_rows = result["workspace"].get("schedule_baselines", [])
    change_rows = result["workspace"].get("schedule_changes", [])
    active_baseline = result.get("active_schedule_baseline")
    variance = result.get("schedule_variance", {})
    if active_baseline:
        st.caption(
            f"Active approved baseline: {active_baseline.get('baseline_id')} "
            f"| Version {active_baseline.get('version', 1)} "
            f"| Approved by {active_baseline.get('approved_by') or 'Not recorded'}"
        )
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Schedule variance", variance.get("status", "Not assessed"))
        v2.metric("Added activities", variance.get("added_count", 0))
        v3.metric("Removed activities", variance.get("removed_count", 0))
        v4.metric("Changed activities", variance.get("changed_count", 0))
        if variance.get("changed_activities"):
            st.dataframe(variance["changed_activities"], use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada approved schedule baseline. Draft tidak digunakan sebagai pembanding resmi.")

    with st.expander("Capture and approve schedule baseline", expanded=False):
        st.caption("Baseline menyimpan snapshot jadwal saat ini. Draft harus ditinjau dan disetujui sebelum dipakai sebagai pembanding.")
        with st.form("pc_capture_schedule_baseline_form"):
            baseline_id_input = st.text_input("Baseline ID", key="pc_baseline_id")
            baseline_name_input = st.text_input("Baseline name", key="pc_baseline_name")
            baseline_creator_input = st.text_input("Prepared by", key="pc_baseline_creator")
            capture_baseline = st.form_submit_button("Capture current schedule as draft")
        if capture_baseline:
            try:
                if any(str(row.get("baseline_id", "")) == baseline_id_input.strip()
                       for row in baseline_rows):
                    raise ValueError("Baseline ID already exists. Use a new ID to preserve the recorded snapshot.")
                new_baseline = create_schedule_baseline(
                    project_id, baseline_id_input, result["workspace"]["activities"],
                    baseline_name=baseline_name_input, created_by=baseline_creator_input,
                    version=max([int(row.get("version", 0) or 0) for row in baseline_rows] + [0]) + 1,
                )
                ProjectStore(database_path).save_dataset(
                    project_id, "schedule_baselines", [new_baseline], mode="upsert"
                )
                st.success("Draft baseline saved. Review and approve it before treating it as the control baseline.")
                st.rerun()
            except (TypeError, ValueError, OSError) as baseline_error:
                st.error("Baseline was not saved: " + str(baseline_error))

        draft_baselines = [
            row for row in baseline_rows if str(row.get("status", "")).upper() == "DRAFT"
        ]
        if draft_baselines:
            draft_ids = [str(row.get("baseline_id")) for row in draft_baselines]
            with st.form("pc_approve_schedule_baseline_form"):
                selected_draft = st.selectbox("Draft baseline to approve", draft_ids)
                approver = st.text_input("Approved by", key="pc_baseline_approver")
                approve_baseline = st.form_submit_button("Approve selected baseline")
            if approve_baseline:
                try:
                    selected_record = next(row for row in draft_baselines
                                           if str(row.get("baseline_id")) == selected_draft)
                    approved_record = approve_schedule_baseline(selected_record, approver)
                    ProjectStore(database_path).save_dataset(
                        project_id, "schedule_baselines", [approved_record], mode="upsert"
                    )
                    st.success("Baseline approved and recorded.")
                    st.rerun()
                except (TypeError, ValueError, OSError, StopIteration) as approval_error:
                    st.error("Baseline approval failed: " + str(approval_error))

    if change_rows:
        st.markdown("**Schedule change register**")
        st.dataframe(change_rows, use_container_width=True, hide_index=True)
    st.caption("Schedule variance is a comparison to the latest approved baseline; it does not automatically approve scope, budget, or contract changes.")

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

    st.markdown("#### Integrated Schedule & Cost Outlook")
    try:
        integrated_outlook = build_schedule_cost_outlook(
            evm, result["workspace"]["activities"],
            as_of_date=__import__("datetime").date.today(),
        )
        st.caption("Combined decision-support view from current EVM and activity records; it does not change the approved baseline.")
        o1, o2, o3 = st.columns(3)
        o1.metric("Outlook status", integrated_outlook["status"])
        delay_days = integrated_outlook["management_attention"]["project_delay_days"]
        o2.metric("Project finish variance (calendar days)", delay_days if delay_days is not None else "Not assessed")
        o3.metric("Over-budget cost scenarios", len(integrated_outlook["management_attention"]["cost_scenarios_over_budget"]))
        if integrated_outlook["cost_forecast"]["scenarios"]:
            st.dataframe(integrated_outlook["cost_forecast"]["scenarios"], use_container_width=True, hide_index=True)
        else:
            st.info("Cost outlook is not assessed. Data gaps: " + ", ".join(integrated_outlook["cost_forecast"].get("data_gaps", [])))
        if integrated_outlook["management_attention"]["delayed_activity_ids"]:
            st.warning("Activities requiring schedule review: " + ", ".join(integrated_outlook["management_attention"]["delayed_activity_ids"]))
        if integrated_outlook["management_attention"]["unassessed_activity_ids"]:
            st.info("Activities without enough schedule evidence: " + ", ".join(integrated_outlook["management_attention"]["unassessed_activity_ids"]))
        with st.expander("Integrated outlook assumptions and limitations"):
            for limitation in integrated_outlook["limitations"]:
                st.write("• " + limitation)
    except (TypeError, ValueError) as outlook_error:
        st.warning("Integrated schedule and cost outlook unavailable: " + str(outlook_error))

    st.markdown("#### Monte Carlo Schedule Risk Forecast")
    mc_result = None
    mc_activities = []
    mc_risks = []
    mc_start = None
    mc_iterations = 10000
    mc_seed = 42
    with st.expander("Simulate P50 / P80 / P90 project finish dates", expanded=False):
        st.caption("Masukkan network aktivitas dan risk register dalam format JSON. Durasi dan dampak risiko menggunakan hari kalender; semua risiko diasumsikan independen.")
        default_activity_json = """[
  {"activity_id":"A1","predecessors":[],"duration_min_days":8,"duration_most_likely_days":10,"duration_max_days":12},
  {"activity_id":"A2","predecessors":["A1"],"duration_min_days":4,"duration_most_likely_days":5,"duration_max_days":7},
  {"activity_id":"A3","predecessors":[],"duration_min_days":6,"duration_most_likely_days":7,"duration_max_days":9}
]"""
        default_risk_json = """[
  {"risk_id":"R1","activity_id":"A2","probability":0.3,"delay_min_days":2,"delay_most_likely_days":4,"delay_max_days":8}
]"""
        with st.form("pc_schedule_risk_monte_carlo_form"):
            mc_start = st.date_input("Project start date", key="pc_mc_schedule_start")
            mc_iterations = st.selectbox("Simulation iterations", [1000, 5000, 10000, 25000, 50000], index=2, key="pc_mc_schedule_iterations")
            mc_seed = st.number_input("Random seed (for reproducibility)", min_value=0, max_value=2147483647, value=42, step=1, key="pc_mc_schedule_seed")
            mc_activities_json = st.text_area("Activity network JSON", value=default_activity_json, height=180, key="pc_mc_schedule_activities")
            mc_risks_json = st.text_area("Activity-linked risk JSON", value=default_risk_json, height=140, key="pc_mc_schedule_risks")
            run_schedule_mc = st.form_submit_button("Run schedule Monte Carlo")
        if run_schedule_mc:
            try:
                mc_activities = json.loads(mc_activities_json)
                mc_risks = json.loads(mc_risks_json)
                mc_result = simulate_schedule_risk(
                    mc_activities, mc_risks, mc_start,
                    iterations=int(mc_iterations), seed=int(mc_seed),
                )
                st.metric("Simulation status", mc_result["status"])
                if mc_result["status"] == "ASSESSED":
                    q1, q2, q3 = st.columns(3)
                    q1.metric("P50 finish", mc_result["finish_date"]["p50"])
                    q2.metric("P80 finish", mc_result["finish_date"]["p80"])
                    q3.metric("P90 finish", mc_result["finish_date"]["p90"])
                    st.write("**Duration percentiles (calendar days)**")
                    st.json(mc_result["duration_days"])
                    st.write("**Probability by selected percentile dates**")
                    st.json(mc_result["probability_finish_by"])
                    st.caption(f"Activities: {mc_result['activity_count']} | Linked risks: {mc_result['risk_count']} | Iterations: {mc_result['iterations']} | Seed: {mc_result['seed']}")
                for limitation in mc_result.get("limitations", []):
                    st.caption("• " + limitation)
            except (json.JSONDecodeError, TypeError, ValueError) as mc_error:
                st.error("Schedule Monte Carlo input invalid: " + str(mc_error))

    st.markdown("#### Resource Loading & Capacity")
    resource_result = None
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

    st.markdown("#### Risk Register & Monte Carlo Cost Contingency")
    risk_result = None
    try:
        risk_rows = result["workspace"]["risk"]
        base_cost = evm.get("BAC")
        project_currency = str(project.get("currency", "")).strip().upper()
        if not risk_rows:
            st.info("Risk register kosong. Ini bukan bukti bahwa proyek tidak memiliki risiko. Masukkan risk_id, probability (0–1), cost_impact_min, cost_impact_most_likely, cost_impact_max, risk_type, dan currency.")
        elif base_cost is None:
            st.warning("BAC belum tersedia; simulasi contingency belum dapat dijalankan.")
        else:
            risk_result = build_risk_cost_simulation(
                risk_rows, base_cost, project_currency, iterations=10000, seed=42
            )
            if risk_result["status"] == "INSUFFICIENT_DATA":
                st.warning(risk_result["reason"])
            else:
                q1, q2, q3, q4 = st.columns(4)
                q1.metric("P50 Cost", f"{risk_result['currency']} {risk_result['p50_cost']:,.2f}")
                q2.metric("P80 Cost", f"{risk_result['currency']} {risk_result['p80_cost']:,.2f}")
                q3.metric("P90 Cost", f"{risk_result['currency']} {risk_result['p90_cost']:,.2f}")
                q4.metric("P80 Contingency", f"{risk_result['currency']} {risk_result['p80_contingency']:,.2f}")
                st.metric("Probability of cost exceeding base", f"{risk_result['probability_over_base']:.2f}%")
                st.dataframe(risk_result["risk_register"], use_container_width=True, hide_index=True)
                st.caption("Monte Carlo uses independent risk events and triangular cost-impact distributions. P80 contingency is a scenario estimate, not an approved reserve.")
                with st.expander("Simulation assumptions and limitations"):
                    for limitation in risk_result["limitations"]:
                        st.write("• " + limitation)
    except (TypeError, ValueError) as exc:
        st.error("Risk register data needs correction: " + str(exc))

    st.markdown("#### Combined Risk-Adjusted Cost & Schedule Outlook")
    if mc_result and mc_result.get("status") == "ASSESSED" and risk_result and risk_result.get("status") == "ASSESSED":
        try:
            combined_outlook = build_risk_adjusted_project_outlook(
                base_cost=evm["BAC"],
                currency=project_currency,
                cost_risks=risk_rows,
                activities=mc_activities,
                schedule_risks=mc_risks,
                project_start_date=mc_start,
                iterations=int(mc_iterations),
                seed=int(mc_seed),
            )
            st.caption("Combined executive view of two separate marginal simulations. This is not a correlated joint forecast.")
            if combined_outlook["status"] == "ASSESSED":
                summary = combined_outlook["executive_summary"]
                co1, co2, co3, co4 = st.columns(4)
                cost_currency = combined_outlook["cost_outlook"].get("currency", project_currency)
                schedule_duration = combined_outlook["schedule_outlook"]["duration_days"]["p80"]
                co1.metric("Cost P80", f"{cost_currency} {summary['cost_p80']:,.2f}")
                co2.metric("P80 contingency", f"{cost_currency} {summary['p80_contingency']:,.2f}")
                co3.metric("Schedule P80 finish", summary["finish_p80"])
                co4.metric("Schedule P80 duration", f"{schedule_duration:,.1f} calendar days")
            else:
                st.info("Combined outlook is partial: " + combined_outlook["status"])
            with st.expander("Combined outlook governance and interpretation"):
                for note in combined_outlook["interpretation"] + combined_outlook.get("governance", []):
                    st.write("• " + note)
        except (TypeError, ValueError, KeyError) as combined_error:
            st.warning("Combined risk-adjusted outlook unavailable: " + str(combined_error))
    else:
        st.info("Jalankan schedule Monte Carlo dan pastikan simulasi biaya serta jadwal berstatus ASSESSED untuk melihat ringkasan gabungan.")

    st.markdown("#### Risk Exposure Matrix & Mitigation Intelligence")
    try:
        exposure_result = build_risk_exposure_matrix(
            result["workspace"]["risk"],
            activities=result["workspace"]["activities"],
            wbs=result["workspace"]["wbs"],
        )
        if exposure_result["status"] == "NO_RISKS":
            st.info("Risk register belum berisi data. Tidak ada risiko tercatat bukan berarti proyek bebas risiko.")
        else:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Critical risks", exposure_result["priority_summary"]["CRITICAL"])
            r2.metric("High risks", exposure_result["priority_summary"]["HIGH"])
            r3.metric("Critical-activity risks", exposure_result["critical_activity_risk_count"])
            r4.metric("Unlinked activity/WBS", exposure_result["unlinked_activity_count"] + exposure_result["unlinked_wbs_count"])
            st.dataframe(exposure_result["risks"], use_container_width=True, hide_index=True)
            with st.expander("Risk probability × impact matrix"):
                st.json(exposure_result["matrix"])
            with st.expander("Methodology and limitations"):
                for limitation in exposure_result["caveats"]:
                    st.write("• " + limitation)
    except (TypeError, ValueError, KeyError) as exposure_error:
        st.warning("Risk exposure matrix unavailable: " + str(exposure_error))

    st.markdown("#### Risk Mitigation Execution Tracker")
    try:
        mitigation_store = RiskMitigationStore(database_path)
        saved_mitigations = mitigation_store.list_project(project_id)
        known_risks = result["workspace"]["risk"]
        risk_ids = sorted({
            str(row.get("risk_id", "")).strip()
            for row in known_risks
            if str(row.get("risk_id", "")).strip()
        })
        if not risk_ids:
            st.info("Tambahkan risk_id pada risk register sebelum mencatat mitigasi.")
        else:
            with st.expander("Create or update mitigation for a registered risk", expanded=False):
                with st.form("pc_risk_mitigation_form"):
                    mitigation_risk_id = st.selectbox("Linked risk ID", risk_ids)
                    mitigation_action = st.text_area("Mitigation action / deliverable")
                    mitigation_owner = st.text_input("Mitigation owner")
                    mitigation_due = st.date_input("Mitigation due date")
                    mitigation_status = st.selectbox(
                        "Execution status",
                        ["PLANNED", "IN_PROGRESS", "IMPLEMENTED", "VERIFIED", "CANCELLED"],
                    )
                    residual_probability = st.number_input(
                        "Residual probability (0–1)", min_value=0.0, max_value=1.0,
                        value=0.2, step=0.05, format="%.2f",
                    )
                    residual_impact = st.number_input(
                        "Residual impact (same unit as the risk register)",
                        min_value=0.0, value=0.0, step=1.0,
                    )
                    mitigation_evidence = st.text_area("Evidence / verification reference")
                    mitigation_actor = st.text_input("Updated by (attribution)")
                    mitigation_submitted = st.form_submit_button("Save mitigation record")
                if mitigation_submitted:
                    try:
                        mitigation_store.save(
                            project_id=project_id, risk_id=mitigation_risk_id,
                            mitigation_action=mitigation_action, owner=mitigation_owner,
                            due_date=mitigation_due, status=mitigation_status,
                            residual_probability=residual_probability,
                            residual_impact=residual_impact, evidence=mitigation_evidence,
                            updated_by=mitigation_actor,
                        )
                        st.success("Mitigation record saved in the local workspace.")
                        st.rerun()
                    except (TypeError, ValueError, OSError) as mitigation_error:
                        st.error("Mitigation record not saved: " + str(mitigation_error))
        if saved_mitigations:
            today = __import__("datetime").date.today().isoformat()
            for item in saved_mitigations:
                if item["risk_id"] not in risk_ids:
                    item["risk_link_status"] = "RISK_NOT_IN_CURRENT_REGISTER"
                else:
                    item["risk_link_status"] = "MATCHED"
                item["overdue"] = (
                    item["due_date"] < today
                    and item["status"] not in {"VERIFIED", "CANCELLED"}
                )
            st.dataframe(saved_mitigations, use_container_width=True, hide_index=True)
            overdue_mitigations = sum(bool(item["overdue"]) for item in saved_mitigations)
            st.metric("Overdue mitigation actions", overdue_mitigations)
            with st.expander("Mitigation change history (append-only)"):
                mitigation_events = mitigation_store.list_events(project_id)
                st.dataframe(mitigation_events, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada rencana mitigasi tersimpan untuk proyek ini.")

        risk_governance = build_risk_governance_view(
            known_risks,
            ActionRegisterStore(database_path).list_project(project_id)["actions"],
            saved_mitigations,
        )
        gv1, gv2, gv3, gv4 = st.columns(4)
        gv1.metric("Risks needing governance attention", risk_governance["risks_requiring_attention"])
        gv2.metric("Overdue linked actions", risk_governance["overdue_action_count"])
        gv3.metric("Blocked linked actions", risk_governance["blocked_action_count"])
        gv4.metric("Risks without mitigation", risk_governance["risks_without_mitigation"])
        st.dataframe(risk_governance["rows"], use_container_width=True, hide_index=True)
        with st.expander("Risk governance data quality"):
            st.write("Orphan executive actions: " + str(risk_governance["orphan_action_count"]))
            st.write("Orphan mitigation records: " + str(risk_governance["orphan_mitigation_count"]))
            for note in risk_governance["limitations"]:
                st.caption("• " + note)

        st.caption("Residual exposure dihitung dari residual probability × residual impact. Status VERIFIED tetap memerlukan pemeriksaan bukti oleh pejabat berwenang; catatan pengguna bukan autentikasi.")
    except (TypeError, ValueError, OSError) as mitigation_error:
        st.warning("Risk mitigation tracker unavailable: " + str(mitigation_error))

    st.markdown("#### Executive Recovery Decision Brief")
    try:
        decision_risks = build_risk_exposure_matrix(
            result["workspace"]["risk"],
            activities=result["workspace"]["activities"],
            wbs=result["workspace"]["wbs"],
        )
        decision_brief = build_recovery_decision_brief(
            evm=evm,
            risk_exposure=decision_risks,
        )
        st.caption("Ringkasan evidence dan review prompt untuk Project Manager / Project Director; bukan persetujuan otomatis.")
        d1, d2, d3 = st.columns(3)
        d1.metric("Decision brief status", decision_brief["status"])
        d2.metric("Signals requiring review", decision_brief["signal_count"])
        d3.metric("Missing inputs", len(decision_brief["missing_inputs"]))
        if decision_brief["signals"]:
            st.dataframe(decision_brief["signals"], use_container_width=True, hide_index=True)
        st.markdown("**Recommended management reviews**")
        for recommendation in decision_brief["recommendations"]:
            st.write("• " + recommendation)
        if decision_brief["missing_inputs"]:
            st.warning("Additional evidence needed: " + ", ".join(decision_brief["missing_inputs"]))
        with st.expander("Decision gates and limitations"):
            for gate in decision_brief["decision_gates"]:
                st.write("• " + gate)
            for limitation in decision_brief["limitations"]:
                st.caption("• " + limitation)
    except (TypeError, ValueError, KeyError) as decision_error:
        st.warning("Executive recovery decision brief unavailable: " + str(decision_error))

    st.markdown("#### Project Director Decision Review")
    try:
        director_review = build_project_director_review(
            project,
            evm,
            risk_simulation=risk_result,
            resource_summary=resource_result,
            schedule_forecast=result["schedule_forecast"],
        )
        st.caption("Review priority: " + director_review["status"] + " | This is a decision-support screen, not an approval.")
        s1, s2, s3 = st.columns(3)
        s1.metric("Attention signals", director_review["summary"]["attention_count"])
        s2.metric("Unassessed signals", director_review["summary"]["unassessed_count"])
        s3.metric("Monitor signals", director_review["summary"]["monitor_count"])
        st.dataframe(director_review["signals"], use_container_width=True, hide_index=True)
        st.markdown("**Recommended management action**")
        st.write(director_review["decision"]["recommended_action"])
        if director_review["decision"]["data_gaps"]:
            st.warning("Decision matrix data gaps: " + ", ".join(director_review["decision"]["data_gaps"]))
        with st.expander("Governance and decision limitations"):
            for limitation in director_review["governance"]:
                st.write("• " + limitation)
    except (TypeError, ValueError, KeyError) as exc:
        st.error("Project Director review could not be prepared: " + str(exc))

    st.markdown("#### Executive Action Register & Governance")
    try:
        action_store = ActionRegisterStore(database_path)
        action_register = action_store.list_project(project_id)
        action_summary = action_register["summary"]
        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("Open actions", action_summary["open_count"])
        ac2.metric("In progress", action_summary["in_progress_count"])
        ac3.metric("Blocked", action_summary["blocked_count"])
        ac4.metric("Overdue", action_summary["overdue_count"])

        with st.expander("Create executive action", expanded=False):
            with st.form("pc_create_executive_action"):
                action_title = st.text_input("Action title")
                action_owner = st.text_input("Responsible owner")
                action_due = st.date_input("Due date")
                action_priority = st.selectbox("Priority", ["P1", "P2", "P3"], index=1)
                action_risk_ids = sorted({
                    str(row.get("risk_id", "")).strip()
                    for row in result["workspace"]["risk"]
                    if str(row.get("risk_id", "")).strip()
                })
                action_risk_id = st.selectbox("Linked risk (optional)", [""] + action_risk_ids)
                action_description = st.text_area("Description / expected evidence")
                action_actor = st.text_input("Created by (attribution)")
                create_submitted = st.form_submit_button("Save action")
            if create_submitted:
                try:
                    action_store.create(
                        title=action_title, owner=action_owner, due_date=action_due,
                        project_id=project_id, priority=action_priority,
                        description=action_description, created_by=action_actor,
                        risk_id=action_risk_id or None,
                    )
                    st.success("Action saved to the local SQLite register.")
                    st.rerun()
                except (TypeError, ValueError) as exc:
                    st.error("Action not saved: " + str(exc))

        if action_register["actions"]:
            st.dataframe(action_register["actions"], use_container_width=True, hide_index=True)
            with st.expander("Update action status and append audit event"):
                action_options = {
                    f"{row['action_id']} — {row['title']} ({row['status']})": row
                    for row in action_register["actions"]
                    if row["status"] not in {"COMPLETED", "CANCELLED"}
                }
                if action_options:
                    selected_label = st.selectbox("Action", list(action_options), key="pc_action_transition_select")
                    selected_action = action_options[selected_label]
                    allowed = {
                        "OPEN": ["IN_PROGRESS", "BLOCKED", "CANCELLED"],
                        "IN_PROGRESS": ["BLOCKED", "COMPLETED", "CANCELLED"],
                        "BLOCKED": ["IN_PROGRESS", "CANCELLED"],
                    }.get(selected_action["status"], [])
                    with st.form("pc_transition_executive_action"):
                        target_status = st.selectbox("New status", allowed)
                        changed_by = st.text_input("Changed by (attribution)")
                        transition_note = st.text_area("Decision / progress note")
                        transition_submitted = st.form_submit_button("Record status change")
                    if transition_submitted:
                        try:
                            action_store.transition(
                                selected_action["action_id"], new_status=target_status,
                                changed_by=changed_by, note=transition_note,
                            )
                            st.success("Status updated and audit event appended.")
                            st.rerun()
                        except (KeyError, TypeError, ValueError) as exc:
                            st.error("Status change not saved: " + str(exc))
                else:
                    st.info("No actions remain eligible for status transition.")
            with st.expander("Action audit history"):
                st.dataframe(action_register["events"], use_container_width=True, hide_index=True)
        else:
            st.info("No executive actions recorded for this project yet.")
        st.caption("Workspace-local SQLite persistence. Actor names are attribution only, not authenticated identities; protect the workspace file and apply access control before multi-user deployment.")
    except (TypeError, ValueError, OSError) as exc:
        st.warning("Executive Action Register unavailable: " + str(exc))

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
