"""Persisted project financial-control view backed by the local workspace."""
import json
import streamlit as st

from ai_project_control.financial_workspace_service import build_stored_project_financial_control
from ai_project_control.executive_report_export import build_executive_report_pdf, build_executive_report_xlsx
from ai_project_control.workspace_config import get_workspace_database_path

st.set_page_config(page_title="Saved Project Financial Control", page_icon="📊", layout="wide")
st.title("Saved Project Financial Control")
st.caption("Analisis EVM dan skenario biaya dari data proyek yang sudah diimpor dan disimpan di workspace lokal.")
database_path = get_workspace_database_path()
st.info("Halaman ini membaca data tersimpan. Impor data terlebih dahulu melalui Project Workspace. Tidak ada data yang diubah oleh halaman ini.")
with st.form("saved_financial_control_form"):
    project_id = st.text_input("Project ID", placeholder="Contoh: PROJECT-001")
    period = st.text_input("As-of period (optional)", placeholder="YYYY-MM")
    threshold = st.number_input("Budget variance warning threshold (%)", min_value=0.0, value=5.0, step=0.5)
    submitted = st.form_submit_button("Load saved project and calculate")
if submitted:
    try:
        result = build_stored_project_financial_control(
            database_path, project_id, as_of_period=period.strip() or None,
            warning_threshold_pct=threshold,
        )
        evm = result["evm"]
        st.subheader(result["project_name"])
        st.caption(f"Project: {result['project_id']} | Currency: {result['currency'] or 'Not defined'}")
        if result["data_validation"]["status"] != "VALID":
            st.warning("Workspace data validation: " + result["data_validation"]["status"])
        metrics = st.columns(4)
        for col, key in zip(metrics, ("PV", "EV", "AC", "BAC")):
            value = evm.get(key)
            col.metric(key, "Not assessed" if value is None else f"{value:,.2f}")
        metrics2 = st.columns(4)
        for col, key in zip(metrics2, ("SPI", "CPI", "EAC", "VAC")):
            value = evm.get(key)
            col.metric(key, "Not assessed" if value is None else f"{value:,.2f}")
        if evm["status"] != "ASSESSED":
            st.warning("EVM requires review. Missing/invalid data: " + ", ".join(evm["data_gaps"]))
        st.subheader("Cost forecast scenarios")
        if result["cost_forecast"]["scenarios"]:
            st.dataframe(result["cost_forecast"]["scenarios"], use_container_width=True, hide_index=True)
        else:
            st.info("Cost scenarios not assessed: " + ", ".join(result["cost_forecast"].get("data_gaps", [])))
        for alert in result["management_alerts"]:
            st.warning(alert["severity"] + ": " + alert["code"])
        with st.expander("Source counts, validation and limitations"):
            st.json({"source_counts": result["source_counts"], "validation": result["data_validation"],
                     "limitations": result["limitations"]})
        report_lines = [
            "# Saved Project Financial Control",
            "",
            f"Project: {result['project_name']} ({result['project_id']})",
            f"Reporting period: {period.strip() or 'All available periods'}",
            f"Currency: {result['currency'] or 'Not defined'}",
            "",
            "## Earned Value Management",
            *[f"- {key}: {evm.get(key) if evm.get(key) is not None else 'Not assessed'}"
              for key in ("PV", "EV", "AC", "BAC", "SPI", "CPI", "EAC", "ETC", "VAC")],
            "",
            "## Cost forecast scenarios",
            *[f"- {row.get('scenario', 'Scenario')}: EAC={row.get('EAC')}, variance={row.get('variance_pct')}%"
              for row in result["cost_forecast"].get("scenarios", [])],
            "",
            "## Data quality and limitations",
            f"- Workspace validation: {result['data_validation']['status']}",
            *[f"- {item}" for item in result["limitations"]],
            "- This report is decision support and does not authorize budget or baseline changes.",
        ]
        report_text = "\nfrom ai_project_control.ui_theme import apply_project_control_theme\napply_project_control_theme("Saved Project Financial Control", "EVM performance, cost outlook and financial governance from validated workspace records.", "FINANCIAL INTELLIGENCE / PROJECT LEVEL")\n".join(report_lines) + "\n"
        export_col1, export_col2 = st.columns(2)
        export_col1.download_button(
            "Download executive report (PDF)",
            data=build_executive_report_pdf(report_text),
            file_name=f"{result['project_id']}_financial_control.pdf",
            mime="application/pdf",
        )
        export_col2.download_button(
            "Download executive report (Excel)",
            data=build_executive_report_xlsx(report_text),
            file_name=f"{result['project_id']}_financial_control.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button("Download saved financial control JSON",
            data=json.dumps(result, indent=2, ensure_ascii=False, default=str),
            file_name=f"{result['project_id']}_financial_control.json", mime="application/json")
    except (TypeError, ValueError, OSError) as exc:
        st.error("Tidak dapat menghitung data proyek tersimpan: " + str(exc))
