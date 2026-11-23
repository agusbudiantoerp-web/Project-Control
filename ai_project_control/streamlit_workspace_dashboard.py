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
from .risk_cost_simulation import build_risk_cost_simulation
from .project_director_review import build_project_director_review
from .portfolio_command_center import build_portfolio_command_center
from .portfolio_monitoring import PortfolioMonitoringStore
from .project_recovery_intelligence import build_project_recovery_intelligence
from .recovery_execution import RecoveryPlanStore, evaluate_recovery_plan
from .recovery_effectiveness import evaluate_recovery_effectiveness
from .recovery_evm_bridge import evaluate_recovery_evm
from .schedule_cost_outlook import build_schedule_cost_outlook
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
    database_path: str | Path = ".project_control/project_control.sqlite3",
) -> dict[str, Any] | None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is required to render this component.") from exc

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
                action_description = st.text_area("Description / expected evidence")
                action_actor = st.text_input("Created by (attribution)")
                create_submitted = st.form_submit_button("Save action")
            if create_submitted:
                try:
                    action_store.create(
                        title=action_title, owner=action_owner, due_date=action_due,
                        project_id=project_id, priority=action_priority,
                        description=action_description, created_by=action_actor,
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
