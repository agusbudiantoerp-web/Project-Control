"""Portfolio COO cockpit reading all projects saved in the local workspace."""
import json
import os
import streamlit as st

from ai_project_control.portfolio_workspace_service import build_saved_portfolio_report
from ai_project_control.executive_report_export import build_executive_report_pdf, build_executive_report_xlsx

st.set_page_config(page_title="Saved Portfolio COO Cockpit", page_icon="🏢", layout="wide")
st.title("Saved Portfolio — COO Executive Cockpit")
st.caption("Ringkasan lintas proyek yang sudah tersimpan dalam workspace SQLite lokal.")
database_path = os.getenv("PROJECT_CONTROL_DB", ".project_control/project_control.sqlite3")
with st.form("portfolio_cockpit_form"):
    period = st.text_input("As-of period (optional)", placeholder="YYYY-MM")
    language = st.selectbox("Report language", ["id", "en"], format_func=lambda x: "Bahasa Indonesia" if x == "id" else "English")
    as_of_date = st.text_input("Governance as-of date (optional)", placeholder="YYYY-MM-DD")
    submitted = st.form_submit_button("Load saved portfolio")
if submitted:
    try:
        result = build_saved_portfolio_report(database_path, as_of_period=period.strip() or None, language=language, as_of_date=as_of_date.strip() or None)
        summary = result["scorecard"]["summary"]
        st.subheader("Portfolio overview")
        cols = st.columns(5)
        for col, label, value in zip(cols, ("Projects", "Assessed", "Insufficient data", "RED", "AMBER"),
                                     (summary["project_count"], summary["assessed_count"], summary["insufficient_data_count"], summary["red_count"], summary["amber_count"])):
            col.metric(label, value)
        st.subheader("Project scorecard")
        st.dataframe(result["scorecard"]["projects"], use_container_width=True, hide_index=True)
        st.subheader("Budget at completion by currency")
        st.dataframe([{"Currency": k, "BAC total": v} for k, v in summary["budget_by_currency"].items()],
                     use_container_width=True, hide_index=True)
        st.subheader("Project detail")
        for project in result["projects"]:
            with st.expander(f"{project['project_name']} ({project['project_id']}) — {project['status']}"):
                if "evm" in project:
                    st.json({"EVM": project["evm"], "Source counts": project["source_counts"], "Validation": project["validation"]})
                else:
                    st.warning(project.get("error", "Data not assessed"))
        st.subheader("Integrated schedule and cost outlook")
        outlooks = result["schedule_cost_outlooks"]
        for item in outlooks:
            with st.expander(f"Outlook — {item['project_name']} ({item['project_id']}) — {item['status']}"):
                if item["status"] == "NOT_RUN":
                    st.info(item["reason"])
                else:
                    cost = item.get("cost_forecast", {})
                    schedule = item.get("schedule_forecast", {})
                    st.json({
                        "management_attention": item.get("management_attention", {}),
                        "cost_forecast": cost,
                        "schedule_summary": {
                            "status": schedule.get("status"),
                            "project_baseline_finish_date": schedule.get("project_baseline_finish_date"),
                            "project_forecast_finish_date": schedule.get("project_forecast_finish_date"),
                            "project_delay_days": schedule.get("project_delay_days"),
                            "delayed_activity_ids": schedule.get("delayed_activity_ids", []),
                            "unassessed_activity_ids": schedule.get("unassessed_activity_ids", []),
                        },
                    })
                    if schedule.get("activities"):
                        st.dataframe(schedule["activities"], use_container_width=True, hide_index=True)
                    st.caption("Cost forecasts are deterministic EVM scenarios; schedule forecasts use explicit activity dates. They are not a probabilistic joint forecast or an approved baseline.")
        st.subheader("Cross-project shared resource intelligence")
        shared = result["portfolio_resource_intelligence"]
        rcols = st.columns(4)
        for col, label, value in zip(
            rcols, ("Projects scanned", "Shared resource periods", "Overloaded periods", "Unassessed resources"),
            (shared["project_count"], shared["shared_resource_period_count"],
             shared["shared_resource_conflict_count"], len(shared["unassessed_resources"])),
        ):
            col.metric(label, value)
        if shared["shared_resource_conflicts"]:
            st.dataframe(shared["shared_resource_conflicts"], use_container_width=True, hide_index=True)
        else:
            st.info("No confirmed cross-project resource overloads in the supplied records.")
        with st.expander("Cross-project risk exposure (currency-separated)"):
            st.dataframe(
                [{"Currency": currency, "Expected exposure": amount}
                 for currency, amount in shared["expected_exposure_by_currency"].items()],
                use_container_width=True, hide_index=True,
            )
            if shared["unassessed_risks"]:
                st.dataframe(shared["unassessed_risks"], use_container_width=True, hide_index=True)
        st.caption("Shared capacity is only assessed when resource ID, period, unit and declared capacity match exactly across projects. Risk impact must be monetary to interpret exposure by currency.")
        st.subheader("Portfolio health trends")
        trend = result["health_monitoring"]
        hcols = st.columns(4)
        for col, label, value in zip(hcols, ("Projects with snapshots", "Trend assessed", "No baseline", "Data conflicts"),
                                     (trend["summary"]["project_count"], trend["summary"]["trend_assessed_count"],
                                      trend["summary"]["no_baseline_count"], trend["summary"]["data_conflict_count"])):
            col.metric(label, value)
        st.caption(trend["method"])
        if trend["projects"]:
            st.dataframe(trend["projects"], use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada snapshot kesehatan proyek. Tren tidak disimpulkan tanpa snapshot historis.")
        st.subheader("Risk governance overview")
        gov = result["risk_governance_summary"]
        gcols = st.columns(5)
        for col, label, value in zip(gcols, ("Registered risks", "Need attention", "Overdue actions", "Blocked actions", "No mitigation"), (gov["risk_count"], gov["risks_requiring_attention"], gov["overdue_action_count"], gov["blocked_action_count"], gov["risks_without_mitigation"])):
            col.metric(label, value)
        for item in result["risk_governance"]:
            with st.expander(f"Risk governance — {item['project_name']} ({item['project_id']})"):
                st.dataframe(item["rows"], use_container_width=True, hide_index=True)
                st.caption(f"Orphan linked actions: {item['orphan_action_count']} | Orphan mitigations: {item['orphan_mitigation_count']}")
        st.subheader("Risk exposure ranking")
        for item in result["risk_exposure_matrices"]:
            with st.expander(f"Risk matrix — {item['project_name']} ({item['project_id']})"):
                if item["risks"]:
                    st.dataframe(item["risks"], use_container_width=True, hide_index=True)
                else:
                    st.info("No risk records supplied.")
                st.json({"priority_summary": item["priority_summary"], "critical_activity_risk_count": item["critical_activity_risk_count"], "unlinked_activity_count": item["unlinked_activity_count"], "unlinked_wbs_count": item["unlinked_wbs_count"]})
        report = result["executive_report"]
        st.subheader("Executive report preview")
        st.markdown(report)
        c1, c2 = st.columns(2)
        c1.download_button("Download portfolio PDF", data=build_executive_report_pdf(report),
                           file_name="portfolio_executive_report.pdf", mime="application/pdf")
        c2.download_button("Download portfolio Excel", data=build_executive_report_xlsx(report),
                           file_name="portfolio_executive_report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download portfolio JSON", data=json.dumps(result, indent=2, ensure_ascii=False, default=str),
                           file_name="portfolio_executive_report.json", mime="application/json")
        with st.expander("Methodology and limitations"):
            st.json(result["limitations"])
    except (TypeError, ValueError, OSError) as exc:
        st.error("Portfolio could not be loaded: " + str(exc))
