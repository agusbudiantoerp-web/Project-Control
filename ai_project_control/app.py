from datetime import date
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Project Control System", page_icon="🏗️", layout="wide")

TEMPLATES = {
    "project_master.csv": (["project_id","project_name","client","location","project_type","planned_start","planned_finish","status_date","currency"],
                           ["PRJ-001","Demo Construction Project","Demo Client","Jakarta","Construction","2026-01-01","2026-12-31","2026-03-31","IDR"]),
    "wbs.csv": (["wbs_id","parent_wbs_id","wbs_name","description","responsible_party"],
                ["1.1","1","Foundation","Foundation works","Civil Team"]),
    "activities.csv": (["activity_id","wbs_id","activity_name","duration_days","planned_start","planned_finish","predecessor_ids","calendar_id","weight_pct"],
                       ["A100","1.1","Excavation","10","2026-01-05","2026-01-14","","CAL-01","5"]),
    "boq_budget.csv": (["boq_id","wbs_id","item_code","description","unit","budget_quantity","unit_rate","budget_amount"],
                       ["BOQ-001","1.1","CIV-001","Excavation","m3","1000","75000","75000000"]),
    "progress.csv": (["period_end","activity_id","boq_id","planned_quantity_to_date","actual_quantity_to_date","unit","evidence_reference","approved_by"],
                     ["2026-03-31","A100","BOQ-001","800","650","m3","DAILY-REPORT-001","Site Engineer"]),
    "actual_cost.csv": (["transaction_date","wbs_id","boq_id","cost_code","cost_category","vendor","description","amount","currency","document_reference"],
                        ["2026-03-31","1.1","BOQ-001","CIV-001","Material","Demo Vendor","Sample cost","25000000","IDR","INV-001"]),
    "risk_register.csv": (["risk_id","risk_description","cause","probability","cost_impact","schedule_impact_days","owner","response_strategy","mitigation_action","due_date","status"],
                          ["R-001","Heavy rain","Seasonal weather","0.3","50000000","5","Project Manager","Mitigate","Prepare drainage","2026-04-15","Open"]),
    "commitments.csv": (["commitment_id","commitment_date","wbs_id","vendor","contract_or_po","description","committed_amount","paid_amount","currency","status"],
                        ["COM-001","2026-02-01","1.1","Demo Vendor","PO-001","Equipment rental","100000000","25000000","IDR","Active"]),
}
REQUIRED = {
    "wbs.csv": ["wbs_id","wbs_name"],
    "activities.csv": ["activity_id","activity_name","duration_days"],
    "boq_budget.csv": ["boq_id","description","unit","budget_quantity","unit_rate"],
    "progress.csv": ["period_end","activity_id","actual_quantity_to_date"],
    "actual_cost.csv": ["transaction_date","amount","currency"],
    "risk_register.csv": ["risk_id","risk_description","probability"],
    "commitments.csv": ["commitment_id","committed_amount","currency"],
}

def parse_xer(raw: bytes):
    text = raw.decode("latin-1", errors="replace")
    tables, current, fields = {}, None, []
    for line in text.splitlines():
        if line.startswith("%T\t"):
            current = line.split("\t", 1)[1].strip()
            tables.setdefault(current, [])
            fields = []
        elif line.startswith("%F\t") and current:
            fields = line.split("\t")[1:]
        elif line.startswith("%R\t") and current and fields:
            values = line.split("\t")[1:]
            if len(values) == len(fields):
                tables[current].append(dict(zip(fields, values)))
    return {name: pd.DataFrame(rows) for name, rows in tables.items()}

st.title("🏗️ AI PROJECT CONTROL SYSTEM")
st.caption("Integrated Project Intelligence Platform | Phase 1 — Project Data Hub")
with st.sidebar:
    st.header("Project Workspace")
    project_code = st.text_input("Project code", "PRJ-001")
    project_name = st.text_input("Project name", "Demo Project")
    status_date = st.date_input("Status date", date.today())

st.info("Download a template, fill it with project data, then upload and validate it. Begin with synthetic data.")
overview, templates, imports, xer, guide = st.tabs(["Overview","Input Templates","Data Import","Primavera XER","User Guide"])

with overview:
    st.subheader(project_name)
    a,b,c = st.columns(3)
    a.metric("Project code", project_code)
    b.metric("Status date", status_date.strftime("%d %b %Y"))
    c.metric("Input templates", len(TEMPLATES))
    st.markdown("### Platform modules")
    modules = [
        ("Project Data Hub","Import and validate source files"),
        ("Planning Engine","WBS, CPM, float, critical path and schedule quality"),
        ("Cost & EVM Engine","BOQ, budget, actual cost, PV, EV, AC, CPI and SPI"),
        ("Progress Engine","Physical progress and productivity"),
        ("Risk Engine","Risk register, PERT and Monte Carlo"),
        ("AI Prediction","Delay and cost forecasting after sufficient historical data"),
        ("Optimization Engine","Schedule crashing and resource optimization"),
        ("AI Reporting","Management reports, Excel, PDF and Telegram"),
    ]
    for title, detail in modules:
        with st.expander(title):
            st.write(detail)
            st.caption("Planned module — not activated in this initial scaffold.")

with templates:
    st.subheader("Download input templates")
    for name, (columns, row) in TEMPLATES.items():
        data = pd.DataFrame([row], columns=columns).to_csv(index=False).encode("utf-8-sig")
        st.download_button("Download " + name, data, file_name=name, mime="text/csv", key="dl_" + name)

with imports:
    st.subheader("CSV / Excel import and validation")
    selected = st.selectbox("Data type", list(TEMPLATES))
    upload = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx","xls"])
    if upload:
        try:
            frame = pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)
            st.write("Rows:", len(frame), "| Columns:", len(frame.columns))
            st.dataframe(frame.head(100), use_container_width=True)
            missing = [col for col in REQUIRED.get(selected, []) if col not in frame.columns]
            if frame.empty:
                st.warning("File has no data rows.")
            elif missing:
                st.error("Missing required columns: " + ", ".join(missing))
            else:
                st.success("Basic column check passed. Business values still require review.")
            st.download_button("Download preview CSV", frame.to_csv(index=False).encode("utf-8-sig"),
                               file_name="preview_" + selected, mime="text/csv")
        except Exception as exc:
            st.error("Could not read file: " + str(exc))

with xer:
    st.subheader("Primavera P6 XER — raw table inspection")
    upload = st.file_uploader("Upload Primavera P6 XER", type=["xer"])
    if upload:
        try:
            tables = parse_xer(upload.getvalue())
            if not tables:
                st.warning("No XER tables were detected. Check that this is a valid P6 XER export.")
            else:
                st.success("Read " + str(len(tables)) + " tables.")
                preferred = ["PROJECT","PROJWBS","TASK","TASKPRED","TASKRSRC","RSRC"]
                names = [x for x in preferred if x in tables] + [x for x in tables if x not in preferred]
                selected_table = st.selectbox("XER table", names)
                frame = tables[selected_table]
                st.write(selected_table, "|", len(frame), "rows")
                st.dataframe(frame.head(200), use_container_width=True)
                st.download_button("Export table to CSV", frame.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=selected_table.lower() + "_from_xer.csv", mime="text/csv")
        except Exception as exc:
            st.error("XER read failed: " + str(exc))

with guide:
    st.subheader("Recommended upload sequence")
    st.markdown("""
    1. Download and fill project_master.csv and wbs.csv.
    2. Fill activities.csv using the approved schedule.
    3. Fill boq_budget.csv using the approved cost baseline.
    4. Update progress.csv and actual_cost.csv each reporting period.
    5. Maintain risk_register.csv and commitments.csv.
    6. Upload one data type at a time and review the validation result.
    """)
    st.warning("The XER reader currently displays raw tables only. CPM, P6 calendar calculations, EVM, Monte Carlo and AI analysis are not yet connected.")
    st.markdown("Use YYYY-MM-DD dates, unique IDs, consistent units and currency. Do not replace unknown values with zero.")

st.divider()
st.caption("New application scaffold. Existing source projects remain unchanged.")
