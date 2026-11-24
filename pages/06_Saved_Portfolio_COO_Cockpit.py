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
    submitted = st.form_submit_button("Load saved portfolio")
if submitted:
    try:
        result = build_saved_portfolio_report(database_path, as_of_period=period.strip() or None, language=language)
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
