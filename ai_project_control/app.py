from datetime import date
import json
import math
import pandas as pd
import streamlit as st
import plotly.express as px
import requests

from dashboard_metrics import forecast_completion_date
from core import (TEMPLATES, REQUIRED, init_db, save_dataset, load_dataset, list_datasets,
                  parse_xer, xer_to_frames, validate_dataset, calculate_cpm, calculate_evm,
                  calculate_progress, risk_analysis, optimize_crash, export_workbook, calculate_xer_cpm, calculate_dcma14, calculate_schedule_pert, add_earned_schedule_metrics, parse_xer_with_pyp6xer, calculate_milestones, calculate_change_impact, calculate_resource_load, generate_pdf_report, send_telegram_document, predict_project_trend, calculate_calendar_schedule, analyze_commitments, build_cost_cashflow, render_pdf_page, analyze_drawing_page_gemini, takeoff_to_boq_draft, export_project_backup, import_project_backup, validate_project_datasets)

st.set_page_config(page_title="AI Project Control System", page_icon="🏗️", layout="wide")
init_db()

st.markdown("""
<style>
.block-container{padding-top:1.3rem;padding-bottom:2rem}
div[data-testid="stMetric"]{background:rgba(80,110,145,.08);padding:14px;border-radius:12px}
.small-muted{color:#8391a5;font-size:.88rem}
</style>
""", unsafe_allow_html=True)

st.title("🏗️ AI PROJECT CONTROL SYSTEM")
st.caption("Integrated Project Intelligence Platform | Integrated V1")
with st.sidebar:
    st.header("Project Workspace")
    project_id = st.text_input("Project code", "PRJ-001").strip() or "PRJ-001"
    saved_master=load_dataset(project_id,"project_master.csv")
    saved_name=str(saved_master.iloc[0].get("project_name","")) if not saved_master.empty else ""
    project_name = st.text_input("Project name", saved_name or "Demo Construction Project")
    saved_status=pd.to_datetime(saved_master.iloc[0].get("status_date"),errors="coerce").date() if not saved_master.empty else date.today()
    status_date = st.date_input("Status date", saved_status if pd.notna(saved_status) else date.today())
    st.divider()
    st.caption("Local project database")
    st.caption("Data is stored on this computer in project_control.db")
    stored = list_datasets(project_id)
    st.write(f"Datasets saved: **{len(stored)}**")

def ds(name):
    return load_dataset(project_id,name)

def show_df(df, height=320):
    if df is not None and not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True, height=height)
    else:
        st.info("Belum ada data. Impor dataset pada tab Project Data Hub.")

def metric_row(items):
    cols=st.columns(len(items))
    for c,(label,value) in zip(cols,items):
        if isinstance(value,float) and math.isnan(value): value="—"
        elif isinstance(value,float): value=f"{value:,.2f}"
        c.metric(label,value)

overview, hub, planning, cost, progress_tab, risk_tab, optimization, xer_tab, resources_tab, milestones_tab, drawing_tab, ai_advisor, reports, guide = st.tabs([
    "Overview","Project Data Hub","Planning & CPM","Cost & EVM","Progress","Risk & Monte Carlo",
    "Optimization","Primavera XER","Resources & Manpower","Milestones & Change","Drawing to BOQ","AI Advisor","Reports","User Guide"
])

with overview:
    master=ds("project_master.csv")
    wbs=ds("wbs.csv"); acts=ds("activities.csv"); boq=ds("boq_budget.csv")
    risks=ds("risk_register.csv")
    st.subheader(project_name)
    metric_row([("Project code",project_id),("Status date",status_date.strftime("%d %b %Y")),
                ("Activities",len(acts)),("WBS elements",len(wbs)),("BOQ items",len(boq))])
    st.markdown("### Integrated platform modules")
    modules=[
      ("Project Data Hub","CSV / Excel import, validation, project dataset storage"),
      ("Planning Engine","CPM, critical path, early/late dates, total float, Gantt"),
      ("Cost & EVM Engine","BOQ budget, PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC, TCPI"),
      ("Progress Engine","Physical quantities, reporting period, weighted progress"),
      ("Risk Engine","Risk exposure and Monte Carlo cost / schedule scenarios"),
      ("Optimization Engine","Minimum-cost schedule crashing where crash data is supplied"),
      ("Primavera XER","PyP6Xer P6 object model, calendars, resources and DCMA14"),
      ("Resources & Manpower","Resource assignments, planned loading and capacity screening"),
      ("Milestones & Change Control","Milestone slippage and approved / pending change impact"),
      ("Drawing to BOQ","Gemini vision takeoff draft from PDF drawings with manual review"),
      ("AI Project Advisor","Optional Groq / Gemini analysis and prioritized action recommendations"),
      ("AI Reporting","Integrated Excel management workbook and CSV exports"),
    ]
    cols=st.columns(2)
    for i,(name,desc) in enumerate(modules):
        with cols[i%2]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(desc)
    st.markdown("### Data readiness")
    readiness=pd.DataFrame([{"Dataset":n,"Rows":len(ds(n)),"Status":"Loaded" if not ds(n).empty else "Not loaded"} for n in TEMPLATES])
    show_df(readiness,250)
    st.caption("AI prediction requires a sufficient history of approved reporting periods. It is not fabricated from a single synthetic snapshot.")

with hub:
    st.subheader("Project Data Hub")
    st.write("Download templates, import CSV/Excel, validate relationships and save data into the local project database.")
    c1,c2=st.columns([1,1])
    with c1:
        for name,(columns,row) in TEMPLATES.items():
            data=pd.DataFrame(columns=[*columns]).to_csv(index=False).encode("utf-8-sig")
            st.download_button(f"⬇️ Template {name}",data,file_name=name,mime="text/csv",key="template_"+name)
    with c2:
        selected=st.selectbox("Dataset type",list(TEMPLATES),key="hub_dataset")
        upload=st.file_uploader("Upload CSV or Excel",type=["csv","xlsx","xls"],key="hub_upload")
        if upload:
            try:
                frame=pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)
                project_snapshot={n:ds(n) for n in TEMPLATES}
                project_snapshot[selected]=frame
                issues=validate_project_datasets(project_snapshot).get(selected,[])
                cross_issues=validate_project_datasets(project_snapshot)
                st.write(f"Rows: **{len(frame)}** | Columns: **{len(frame.columns)}**")
                show_df(frame,300)
                if issues:
                    for issue in issues: st.error(issue)
                elif cross_issues:
                    st.warning("Dataset ini lolos validasi lokal, tetapi ada masalah pada dataset proyek lain:")
                    for dataset_name, findings in cross_issues.items():
                        for issue in findings: st.error(f"{dataset_name}: {issue}")
                    if st.button("Save dataset with other-dataset warnings",type="secondary"):
                        save_dataset(project_id,selected,frame)
                        st.warning(f"{selected} saved. Resolve the listed project-wide validation issues before relying on reports.")
                        st.rerun()
                else:
                    st.success("Project-wide dataset validation passed.")
                    if st.button("Save dataset to project",type="primary"):
                        save_dataset(project_id,selected,frame)
                        st.success(f"{selected} saved for {project_id}.")
                        st.rerun()
            except Exception as exc: st.exception(exc)
    st.divider()
    st.markdown("#### Project backup & restore")
    backup_bytes=export_project_backup(project_id)
    st.download_button("Download full project backup (.zip)",backup_bytes,
      f"{project_id}_AI_Project_Control_Backup.zip","application/zip")
    backup_upload=st.file_uploader("Restore project from backup ZIP",type=["zip"],key="restore_project_zip")
    if backup_upload and st.button("Restore backup into this project",type="secondary"):
        try:
            restored=import_project_backup(project_id,backup_upload.getvalue())
            st.success(f"Restored {len(restored)} datasets: {', '.join(restored)}")
            st.rerun()
        except Exception as exc: st.error(f"Backup restore failed: {exc}")
    st.divider()
    st.markdown("#### Currently saved project data")
    for name in TEMPLATES:
        frame=ds(name)
        with st.expander(f"{name} — {len(frame)} rows"):
            show_df(frame,230)
            if not frame.empty:
                st.download_button(f"Export {name}",frame.to_csv(index=False).encode("utf-8-sig"),
                  file_name=name,mime="text/csv",key="export_"+name)

with planning:
    st.subheader("Planning Engine — CPM / Critical Path")
    activities=ds("activities.csv")
    if not activities.empty:
        try:
            cpm,stats=calculate_cpm(activities)
            metric_row([("Project duration (working periods)",stats["project_duration"]),
                        ("Activities",int(stats["n_activities"])),("Critical activities",int(stats["n_critical"]))])
            st.markdown("#### Activity schedule calculation")
            show_df(cpm,500)
            chart=cpm.copy()
            chart["start"]=chart["early_start_day"]
            chart["finish"]=chart["early_finish_day"]
            fig=px.timeline(chart,x_start="start",x_end="finish",y="activity_name",color="is_critical",
                hover_data=["activity_id","wbs_id","total_float_days"],title="CPM early-start schedule (relative working periods)")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig,use_container_width=True)
            st.download_button("Download CPM results CSV",cpm.to_csv(index=False).encode("utf-8-sig"),
                "cpm_results.csv","text/csv")
            calendar_data=ds("calendars.csv")
            if not calendar_data.empty and "calendar_id" in activities.columns:
                st.markdown("#### Working calendar date check")
                try:
                    calendar_schedule=calculate_calendar_schedule(activities,calendar_data)
                    date_check=cpm[["activity_id","early_start_day","early_finish_day","total_float_days","is_critical"]].merge(
                        calendar_schedule,on="activity_id",how="left")
                    show_df(date_check,350)
                    st.download_button("Download calendar date check CSV",
                        date_check.to_csv(index=False).encode("utf-8-sig"),
                        "calendar_date_check.csv","text/csv")
                    st.caption("Calendar dates are a separate date-arithmetic check. They are not yet fed back into CPM network passes or Primavera P6 constraints.")
                except Exception as cal_exc:
                    st.error(f"Working calendar validation: {cal_exc}")
            else:
                st.info("Impor calendars.csv dengan calendar_id, workdays_per_week, hours_per_day dan holidays untuk mengaktifkan pemeriksaan tanggal kalender.")
        except Exception as exc: st.error(f"CPM calculation needs correction: {exc}")
    else: st.info("Impor activities.csv terlebih dahulu.")
    st.warning("CSV CPM uses FS predecessor logic and relative working periods. The calendar date check applies weekly 5/6/7-day patterns and listed holidays, but does not yet alter CPM network passes. XER adapter supports FS, SS, FF and SF with lag; full P6 calendars, constraints and resource levelling remain outside this calculation. Primavera P6 remains the schedule authority.")

with cost:
    st.subheader("Cost & EVM Engine")
    master=ds("project_master.csv"); activities=ds("activities.csv"); boq=ds("boq_budget.csv")
    prog=ds("progress.csv"); actual=ds("actual_cost.csv")
    if not boq.empty and not activities.empty:
        try:
            evm=calculate_evm(master,activities,boq,prog,actual,status_date)
            evm=add_earned_schedule_metrics(evm,master,activities,status_date)
            metric_row([(k,f"{v:,.2f}" if pd.notna(v) else "—") for k,v in evm.items() if k in ["BAC","PV","EV","AC"]])
            metric_row([(k,f"{v:,.3f}" if pd.notna(v) else "—") for k,v in evm.items() if k in ["SPI","CPI","EAC","ETC","VAC","TCPI"]])
            if "SPI(t)" in evm:
                st.markdown("#### Earned Schedule — time performance")
                metric_row([(k,f"{evm[k]:,.2f}" if pd.notna(evm[k]) else "—")
                    for k in ["ES","SV(t)","SPI(t)","IEAC(t)"] if k in evm])
                st.caption("ES = earned schedule time; SV(t) = time variance; SPI(t) = time efficiency; IEAC(t) = duration forecast using earned schedule.")
            st.caption(f"Weighted earned value progress: {evm['physical_progress_pct']:.2f}%")
            if not master.empty and {"planned_start","planned_finish"}.issubset(master.columns) and pd.notna(evm["SPI"]):
                forecast=forecast_completion_date(evm["SPI"],str(master.iloc[0]["planned_start"]),str(master.iloc[0]["planned_finish"]))
                if forecast is not None:
                    st.metric("SPI-based forecast finish",forecast.strftime("%d %b %Y"))
                else:
                    st.caption("Finish forecast unavailable: SPI must be positive.")
            chart=pd.DataFrame({"Metric":["PV","EV","AC"],"Amount":[evm["PV"],evm["EV"],evm["AC"]]})
            st.plotly_chart(px.bar(chart,x="Metric",y="Amount",title="Planned Value vs Earned Value vs Actual Cost"),use_container_width=True)
        except Exception as exc: st.error(f"EVM cannot be calculated: {exc}")
    else:
        st.info("Impor activities.csv dan boq_budget.csv untuk mengaktifkan EVM.")
    st.divider()
    st.markdown("#### Purchase Commitments & Outstanding Exposure")
    commitments=ds("commitments.csv")
    try:
        project_currency=str(master.iloc[0]["currency"]) if not master.empty and "currency" in master else None
        commitment_detail,commitment_stats=analyze_commitments(commitments,status_date,project_currency)
        metric_row([
            ("Active commitments",commitment_stats["commitment_count"]),
            ("Committed total",f"{commitment_stats['committed_total']:,.2f}"),
            ("Paid against commitments",f"{commitment_stats['paid_total']:,.2f}"),
            ("Outstanding commitment",f"{commitment_stats['outstanding_total']:,.2f}")
        ])
        if not commitment_detail.empty:
            show_df(commitment_detail,300)
            st.download_button("Download commitment reconciliation CSV",
                commitment_detail.to_csv(index=False).encode("utf-8-sig"),
                "commitment_reconciliation.csv","text/csv")
        st.caption("Commitment paid amounts are reconciliation only. They are not added to actual cost (AC), preventing double counting. Cancelled, rejected and void commitments are excluded.")
    except Exception as exc:
        st.error(f"Commitment reconciliation needs correction: {exc}")
    st.divider()
    st.markdown("#### Monthly Cash Flow & Cost Forecast")
    try:
        cashflow, cash_stats, _ = build_cost_cashflow(
            master, activities, boq, actual, commitments, status_date, prog)
        metric_row([
            ("Baseline Budget (BAC)",f"{cash_stats['BAC']:,.2f}"),
            ("Actual Cost to Date",f"{cash_stats['actual_to_date']:,.2f}"),
            ("Forecast at Completion",f"{cash_stats['forecast_at_completion']:,.2f}"),
            ("Remaining Forecast",f"{cash_stats['remaining_forecast']:,.2f}")
        ])
        st.caption(cash_stats["forecast_method"])
        if cash_stats["unallocated_remaining"]>0:
            st.warning(f"Remaining forecast {cash_stats['unallocated_remaining']:,.2f} is unallocated because no future project months remain.")
        if not cashflow.empty:
            st.plotly_chart(px.bar(cashflow,x="period",y=["baseline_cost","actual_cost","remaining_forecast"],
                title="Monthly Baseline, Actual and Remaining Forecast Cost",barmode="group"),
                use_container_width=True)
            st.plotly_chart(px.line(cashflow,x="period",
                y=["cumulative_baseline","cumulative_actual","cumulative_forecast"],
                markers=True,title="Cumulative Project Cost Curve"),use_container_width=True)
            st.download_button("Download monthly cash flow CSV",
                cashflow.to_csv(index=False).encode("utf-8-sig"),
                "monthly_project_cashflow.csv","text/csv")
    except Exception as exc:
        st.error(f"Cash flow forecast needs correction: {exc}")
    st.markdown("#### EVM definitions")
    st.caption("CV = EV − AC | SV = EV − PV | CPI = EV / AC | SPI = EV / PV | EAC = BAC / CPI | ETC = EAC − AC | VAC = BAC − EAC.")

with progress_tab:
    st.subheader("Progress Intelligence")
    activities=ds("activities.csv"); prog=ds("progress.csv"); boq_progress=ds("boq_budget.csv")
    if not activities.empty:
        if prog.empty:
            st.info("Progress belum dilaporkan. Impor progress.csv dengan actual_quantity_to_date dan BOQ references.")
        else:
            try:
                latest_progress,progress_stats=calculate_progress(activities,prog,boq_progress)
                if progress_stats["weighted_progress_pct"] is not None:
                    metric_row([("Weighted physical progress",f"{progress_stats['weighted_progress_pct']:.2f}%"),
                      ("Activities reported",f"{progress_stats['reported_activities']} / {progress_stats['total_activities']}"),
                      ("Activities not reported",progress_stats["unreported_activities"])])
                else:
                    st.warning("BOQ budget belum tersedia; hanya kuantitas aktual yang dapat ditampilkan. Weighted progress memerlukan BOQ quantity dan activity weights.")
                st.caption(f"Latest reporting date: {progress_stats['status_date']}")
                show_df(latest_progress,350)
                st.caption("Progress is calculated from cumulative actual BOQ quantities against approved budget quantities, allocated to activities by WBS weight share.")
                if "period_end" in prog:
                    p=prog.copy(); p["period_end"]=pd.to_datetime(p["period_end"],errors="coerce")
                    st.plotly_chart(px.line(p.sort_values("period_end"),x="period_end",y="actual_quantity_to_date",
                        color="activity_id",markers=True,title="Reported cumulative quantity by activity"),use_container_width=True)
            except Exception as exc: st.error(f"Progress calculation needs review: {exc}")
    else: st.info("Import activity schedule first.")

with risk_tab:
    st.subheader("Risk Engine — Expected Exposure & Monte Carlo")
    risks=ds("risk_register.csv")
    if not risks.empty:
        iterations=st.slider("Simulation iterations",1000,50000,10000,1000)
        try:
            ranked,stats,samples=risk_analysis(risks,iterations)
            if not ds("activities.csv").empty:
                schedule_pert,pert_stats,pert_meta=calculate_schedule_pert(ds("activities.csv"),iterations)
                st.markdown("#### PERT schedule uncertainty (activity three-point estimate)")
                metric_row([("PERT expected duration",pert_stats["expected_duration"]),
                  ("Schedule P50",pert_stats["mc_p50"]),("Schedule P80",pert_stats["mc_p80"]),
                  ("Schedule P95",pert_stats["mc_p95"])])
                show_df(schedule_pert,300)
            else:
                st.info("Import activities.csv to run schedule PERT simulation.")
            metric_row([("Expected cost exposure",f"{stats['expected_cost_exposure']:,.0f}"),
                        ("Schedule exposure (days)",f"{stats['expected_schedule_exposure_days']:,.1f}"),
                        ("Cost P80",f"{stats['cost_p80']:,.0f}"),("Cost P90",f"{stats['cost_p90']:,.0f}")])
            metric_row([("Delay P50 (days)",f"{stats['delay_p50']:,.1f}"),
                        ("Delay P80 (days)",f"{stats['delay_p80']:,.1f}"),
                        ("Delay P90 (days)",f"{stats['delay_p90']:,.1f}"),
                        ("Simulation runs",f"{stats['iterations']:,}")])
            show_df(ranked,350)
            st.plotly_chart(px.histogram(samples,x="cost",nbins=40,title="Monte Carlo risk cost distribution"),use_container_width=True)
            st.plotly_chart(px.histogram(samples,x="delay_days",nbins=40,title="Monte Carlo schedule impact distribution"),use_container_width=True)
            st.download_button("Download Monte Carlo samples",samples.to_csv(index=False).encode("utf-8-sig"),
              "risk_monte_carlo.csv","text/csv")
        except Exception as exc: st.error(f"Risk analysis error: {exc}")
    else: st.info("Import risk_register.csv to activate risk analysis.")
    st.caption("Scenario model assumes independent Bernoulli occurrence for each risk. Correlation, mitigation effectiveness and P6 calendar impact are not inferred.")

with optimization:
    st.subheader("Optimization Engine — Minimum Cost Schedule Crashing")
    activities=ds("activities.csv")
    if not activities.empty:
        try:
            _,base_stats=calculate_cpm(activities)
            target=st.number_input("Target project duration (periods)",min_value=0.0,
                max_value=float(base_stats["project_duration"]),value=max(0.0,float(base_stats["project_duration"])-1),step=1.0)
            if {"crash_duration_days","crash_cost_per_day"}.issubset(activities.columns):
                if st.button("Optimize schedule",type="primary"):
                    result,summary=optimize_crash(activities,target)
                    metric_row([("Normal duration",summary["normal_duration_total"]),
                      ("Achieved duration",summary["achieved_duration"]),("Crash cost",summary["total_crash_cost"])])
                    show_df(result,400)
            else:
                st.info("Optimization is ready when activity data includes crash_duration_days and crash_cost_per_day. These inputs must come from approved contractor/productivity and cost assumptions.")
                st.code("Add columns: crash_duration_days, crash_cost_per_day")
        except Exception as exc: st.error(str(exc))

with xer_tab:
    st.subheader("Primavera P6 XER Integration")
    xer_file=st.file_uploader("Upload Primavera P6 .XER",type=["xer"],key="xer_upload")
    if xer_file:
        try:
            tables=parse_xer(xer_file.getvalue())
            st.success(f"XER parsed: {len(tables)} tables.")
            names=list(tables)
            chosen=st.selectbox("Inspect XER table",names)
            show_df(tables[chosen],300)
            try:
                xer_cpm,xer_stats=calculate_xer_cpm(tables)
                st.markdown("#### Primavera network analysis (FS / SS / FF / SF + lag)")
                metric_row([("Calculated duration (days)",xer_stats["project_duration_days"]),
                  ("Activities",xer_stats["activities"]),("Critical activities",xer_stats["critical_activities"])])
                show_df(xer_cpm,380)
                st.download_button("Download XER CPM results",xer_cpm.to_csv(index=False).encode("utf-8-sig"),
                  "primavera_xer_cpm.csv","text/csv")
            except Exception as exc:
                st.warning(f"XER CPM: {exc}")
            try:
                p6_detail=parse_xer_with_pyp6xer(xer_file.getvalue())
                st.markdown("#### PyP6Xer — complete P6 object model")
                metric_row([(k,v) for k,v in p6_detail["summary"].items()])
                st.markdown("#### DCMA 14-point schedule quality analysis")
                show_df(p6_detail["dcma14"],430)
                with st.expander("Activities parsed by PyP6Xer"):
                    show_df(p6_detail["activities"],350)
                with st.expander("Resources and resource assignments"):
                    st.markdown("**Resources**"); show_df(p6_detail["resources"],220)
                    st.markdown("**Assignments**"); show_df(p6_detail["resource_assignments"],220)
                with st.expander("P6 calendars, WBS and relationships"):
                    st.markdown("**Calendars**"); show_df(p6_detail["calendars"],220)
                    st.markdown("**WBS**"); show_df(p6_detail["wbs"],220)
                    st.markdown("**Relationships**"); show_df(p6_detail["relationships"],220)
            except Exception as exc:
                st.warning(f"PyP6Xer detailed parser / DCMA14 could not complete; raw XER parser remains available. Details: {exc}")
                try:
                    dcma=calculate_dcma14(tables)
                    st.markdown("#### Fallback DCMA schedule-health screening")
                    show_df(dcma,430)
                except Exception as fallback_exc:
                    st.warning(f"Fallback DCMA screening: {fallback_exc}")
            if st.button("Convert XER to project WBS + activities",type="primary"):
                act_frame,wbs_frame=xer_to_frames(tables)
                save_dataset(project_id,"activities.csv",act_frame)
                if not wbs_frame.empty: save_dataset(project_id,"wbs.csv",wbs_frame)
                try:
                    p6_data=parse_xer_with_pyp6xer(xer_file.getvalue())
                    for dataset,key in [("resources.csv","resources"),("resource_assignments.csv","resource_assignments"),
                        ("calendars.csv","calendars"),("relationships.csv","relationships")]:
                        if not p6_data[key].empty: save_dataset(project_id,dataset,p6_data[key])
                except Exception as exc:
                    st.warning(f"XER core converted; detailed resource/calendar extraction was skipped: {exc}")
                st.success(f"Imported {len(act_frame)} activities and {len(wbs_frame)} WBS rows, with available P6 resource, calendar and relationship data.")
                st.rerun()
            st.download_button("Download XER table CSV",tables[chosen].to_csv(index=False).encode("utf-8-sig"),
                chosen.lower()+".csv","text/csv")
        except Exception as exc: st.exception(exc)
    st.warning("XER network analysis currently supports FS, SS, FF and SF relationships with lag using duration-based periods. P6 calendars, resource assignments, cost accounts, activity codes and constraints can be inspected/imported where available, but are not yet fully recalculated by the CPM engine. Primavera P6 remains the schedule authority.")

with resources_tab:
    st.subheader("Resource, Equipment & Manpower Intelligence")
    resource_data=ds("resources.csv")
    assignment_data=ds("resource_assignments.csv")
    if not assignment_data.empty:
        try:
            resource_summary,daily_load=calculate_resource_load(resource_data,assignment_data)
            st.markdown("#### Resource allocation & utilization")
            metric_row([
                ("Assigned resources",f"{resource_summary['rsrc_id'].nunique():,}"),
                ("Planned quantity",f"{resource_summary['target_qty'].sum():,.2f}"),
                ("Actual quantity",f"{resource_summary['actual_qty'].sum():,.2f}"),
                ("Overloaded resource-days",f"{int(daily_load['over_capacity'].sum()) if not daily_load.empty else 0:,}")
            ])
            show_df(resource_summary,350)
            if not daily_load.empty:
                st.markdown("#### Daily resource demand and capacity")
                chart=daily_load.copy()
                chart["capacity_line"]=chart["capacity_per_day"]
                st.plotly_chart(px.line(chart,x="date",y=["planned_load_per_day","capacity_line"],
                    color="rsrc_id",facet_col="rsrc_id",title="Daily demand vs available capacity"),
                    use_container_width=True)
                if daily_load["over_capacity"].any():
                    st.error(f"Capacity overload detected on {int(daily_load['over_capacity'].sum())} resource-days.")
                    show_df(daily_load[daily_load["over_capacity"]],250)
                elif daily_load["capacity_per_day"].isna().all():
                    st.info("Capacity belum diisi. Isi capacity_per_day pada resources.csv untuk mengukur overload.")
                st.download_button("Download daily resource loading CSV",
                    daily_load.to_csv(index=False).encode("utf-8-sig"),
                    "daily_resource_loading.csv","text/csv")
            st.download_button("Download resource allocation summary CSV",
                resource_summary.to_csv(index=False).encode("utf-8-sig"),
                "resource_allocation_summary.csv","text/csv")
        except Exception as exc:
            st.error(f"Resource analysis needs data correction: {exc}")
    else:
        st.info("Impor resources.csv dan resource_assignments.csv, atau gunakan konversi XER Primavera untuk mengisi keduanya.")
    st.caption("Kapasitas dibandingkan dalam unit yang sama dengan target_qty per hari. Distribusi saat ini diratakan pada hari kalender, bukan shift/hari kerja. Ini adalah screening overload, bukan resource leveling resmi Primavera P6.")

with milestones_tab:
    st.subheader("Milestone & Change Control")
    milestone_data=ds("milestones.csv")
    if not milestone_data.empty:
        milestone_result,milestone_stats=calculate_milestones(milestone_data,status_date)
        metric_row([("Milestones",milestone_stats["total"]),("Completed",milestone_stats["completed"]),
          ("Delayed",milestone_stats["delayed"]),("Overdue / at risk",milestone_stats["at_risk"])])
        show_df(milestone_result,350)
    else:
        st.info("Impor milestones.csv untuk memantau target, forecast, actual finish dan slippage.")
    change_data=ds("change_register.csv")
    if not change_data.empty:
        bac=float(pd.to_numeric(ds("boq_budget.csv").get("budget_amount",pd.Series(dtype=float)),errors="coerce").fillna(0).sum()) if not ds("boq_budget.csv").empty else 0.0
        change_result,change_stats=calculate_change_impact(change_data,bac)
        st.markdown("#### Change impact")
        metric_row([("Approved cost impact",f"{change_stats['approved_cost_impact']:,.0f}"),
          ("Approved schedule impact (days)",change_stats["approved_schedule_days"]),
          ("Revised BAC",f"{change_stats['revised_budget']:,.0f}"),
          ("Pending exposure",f"{change_stats['pending_cost_exposure']:,.0f}")])
        show_df(change_result,350)
    else:
        st.info("Impor change_register.csv untuk mengendalikan perubahan scope, biaya, dan jadwal.")

with drawing_tab:
    st.subheader("AI Drawing to BOQ — PDF Takeoff Draft")
    st.warning("AI takeoff is an initial quantity-survey draft. Verify drawing scale, dimensions, units, scope and every quantity before using it as a contractual BOQ.")
    drawing_file=st.file_uploader("Upload engineering drawing PDF",type=["pdf"],key="drawing_pdf")
    if drawing_file:
        try:
            page_count=render_pdf_page(drawing_file.getvalue(),0)[2]
            page_number=st.number_input("Drawing page",min_value=1,max_value=max(1,page_count),value=1,step=1)
            image_bytes,page_text,_=render_pdf_page(drawing_file.getvalue(),int(page_number)-1)
            st.image(image_bytes,caption=f"{drawing_file.name} — page {page_number}",use_container_width=True)
            with st.expander("Selectable text extracted from this page"):
                st.text_area("PDF text",page_text,height=140,disabled=True)
            gemini_key=st.text_input("Google Gemini API key (not stored)",type="password",key="drawing_gemini_key")
            gemini_model=st.text_input("Gemini model","gemini-2.5-flash",key="drawing_gemini_model")
            if st.button("Analyze drawing and draft BOQ items",type="primary"):
                if not gemini_key:
                    st.error("Gemini API key is required for drawing image analysis.")
                else:
                    try:
                        takeoff=analyze_drawing_page_gemini(image_bytes,gemini_key,gemini_model)
                        takeoff["drawing_id"]=drawing_file.name
                        takeoff["page"]=int(page_number)
                        st.session_state["drawing_takeoff_draft"]=takeoff
                    except Exception as exc:
                        st.error(f"Drawing analysis failed: {exc}")
        except Exception as exc:
            st.error(f"Could not read drawing PDF: {exc}")
    takeoff_saved=ds("drawing_takeoff.csv")
    takeoff_draft=st.session_state.get("drawing_takeoff_draft",takeoff_saved)
    if isinstance(takeoff_draft,pd.DataFrame) and not takeoff_draft.empty:
        st.markdown("#### Review and edit takeoff lines")
        st.caption("Assign each takeoff line to a project WBS before converting it into a BOQ draft. Unassigned lines remain draft-only and cannot be used in EVM.")
        wbs_options=ds("wbs.csv")
        if not wbs_options.empty and "wbs_id" in wbs_options:
            valid_wbs=sorted(wbs_options["wbs_id"].dropna().astype(str).unique().tolist())
            if "wbs_id" not in takeoff_draft.columns:
                takeoff_draft["wbs_id"]=""
            edited=st.data_editor(takeoff_draft,use_container_width=True,num_rows="dynamic",key="takeoff_editor",
                column_config={"wbs_id":st.column_config.SelectboxColumn("WBS mapping",options=valid_wbs,required=False)})
        else:
            edited=st.data_editor(takeoff_draft,use_container_width=True,num_rows="dynamic",key="takeoff_editor")
            st.warning("Import the project WBS first. BOQ draft lines will have no WBS mapping until assigned.")
        if st.button("Save reviewed takeoff to project database"):
            save_dataset(project_id,"drawing_takeoff.csv",edited)
            st.success("Takeoff draft saved. Review status remains under your control.")
        boq_draft=takeoff_to_boq_draft(edited)
        st.markdown("#### BOQ draft — unit rates intentionally blank")
        show_df(boq_draft,300)
        st.download_button("Download BOQ draft CSV",boq_draft.to_csv(index=False).encode("utf-8-sig"),
            "BOQ_DRAFT_from_Drawing.csv","text/csv")
    else:
        st.info("Upload a PDF drawing and run Gemini vision analysis to create a takeoff draft.")

with ai_advisor:
    st.subheader("AI Project Advisor & Prediction")
    st.warning("Mengirim ringkasan proyek ke penyedia AI eksternal hanya setelah Anda menekan Analyze. Jangan kirim data rahasia klien tanpa persetujuan.")
    provider=st.selectbox("AI provider",["Groq","Google Gemini"],key="ai_provider")
    api_key=st.text_input("API key (hanya untuk sesi ini; tidak disimpan)",type="password",key="ai_api_key")
    model=st.text_input("Model", "llama-3.3-70b-versatile" if provider=="Groq" else "gemini-2.5-flash",key="ai_model")
    context={"project_code":project_id,"project_name":project_name,"status_date":str(status_date),
      "dataset_rows":{n:len(ds(n)) for n in TEMPLATES}}
    try:
        if not ds("activities.csv").empty:
            cpm_frame,cpm_stats=calculate_cpm(ds("activities.csv"))
            context["schedule"]={"duration":cpm_stats["project_duration"],"critical_activities":cpm_frame.loc[cpm_frame["is_critical"],"activity_id"].tolist()}
        if not ds("boq_budget.csv").empty and not ds("activities.csv").empty:
            context["evm"]=calculate_evm(ds("project_master.csv"),ds("activities.csv"),ds("boq_budget.csv"),ds("progress.csv"),ds("actual_cost.csv"),status_date)
        if not ds("risk_register.csv").empty:
            _,risk_stats,_=risk_analysis(ds("risk_register.csv"),3000)
            context["risk"]=risk_stats
        trend_prediction,_=predict_project_trend(ds("project_master.csv"),ds("activities.csv"),
          ds("boq_budget.csv"),ds("progress.csv"),ds("actual_cost.csv"))
        if trend_prediction: context["trend_prediction"]=trend_prediction
    except Exception as exc:
        context["data_quality_note"]=str(exc)
    st.json(context)
    if st.button("Analyze project with AI",type="primary"):
        if not api_key:
            st.error("Masukkan API key Groq atau Gemini terlebih dahulu.")
        else:
            prompt=("You are a senior project controls advisor. Analyze the supplied project data. "
              "Separate verified metrics from assumptions, identify schedule/cost/risk red flags, "
              "give prioritized actions with owner and timing, and state missing data. Never invent values. "
              "Respond in Indonesian. Project data: "+json.dumps(context,default=str))
            try:
                if provider=="Groq":
                    response=requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
                      json={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.2},timeout=90)
                    response.raise_for_status()
                    answer=response.json()["choices"][0]["message"]["content"]
                else:
                    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    response=requests.post(url,headers={"x-goog-api-key":api_key},
                      json={"contents":[{"parts":[{"text":prompt}]}]},timeout=90)
                    response.raise_for_status()
                    answer=response.json()["candidates"][0]["content"]["parts"][0]["text"]
                st.markdown(answer)
            except Exception as exc:
                st.error(f"AI provider request failed: {exc}")
    st.markdown("#### Predictive readiness")
    trend_prediction,trend_history=predict_project_trend(ds("project_master.csv"),ds("activities.csv"),
        ds("boq_budget.csv"),ds("progress.csv"),ds("actual_cost.csv"))
    if trend_prediction:
        st.markdown("#### Historical trend forecast")
        metric_row([("Reporting periods",trend_prediction["reporting_periods"]),
          ("Latest SPI",trend_prediction["latest_SPI"]),("Latest CPI",trend_prediction["latest_CPI"]),
          ("Trend EAC",f"{trend_prediction['trend_EAC']:,.0f}" if pd.notna(trend_prediction["trend_EAC"]) else "—")])
        if trend_prediction["trend_finish_forecast"] is not None:
            st.metric("Trend-based finish forecast",pd.Timestamp(trend_prediction["trend_finish_forecast"]).strftime("%d %b %Y"))
        st.plotly_chart(px.line(trend_history,x="period_end",y=["PV","EV","AC"],markers=True,
            title="Historical cumulative PV / EV / AC"),use_container_width=True)
        st.caption(trend_prediction["method"]+". This is a trend projection, not a trained machine-learning model.")
    else:
        periods=ds("progress.csv")["period_end"].nunique() if not ds("progress.csv").empty and "period_end" in ds("progress.csv") else 0
        st.info(f"Available reporting periods: {periods}. At least 3 valid reporting periods with BOQ quantities and actual costs are needed for a trend forecast. ML prediction needs a longer, validated project history.")

with reports:
    st.subheader("Management Reports & Data Export")
    datasets={n:ds(n) for n in TEMPLATES}
    analysis={}
    report_metrics={}
    try:
        if not datasets["activities.csv"].empty:
            cpm_frame,cpm_stats=calculate_cpm(datasets["activities.csv"])
            analysis["CPM Results"]=cpm_frame
            report_metrics["Planned duration (periods)"]=round(cpm_stats["project_duration"],2)
            report_metrics["Critical activities"]=int(cpm_stats["n_critical"])
        if not datasets["boq_budget.csv"].empty and not datasets["activities.csv"].empty:
            evm_values=calculate_evm(datasets["project_master.csv"],datasets["activities.csv"],
                datasets["boq_budget.csv"],datasets["progress.csv"],datasets["actual_cost.csv"],status_date)
            report_metrics.update({k:round(float(evm_values[k]),2) for k in ["BAC","PV","EV","AC","SPI","CPI","EAC","ETC","VAC"] if pd.notna(evm_values[k])})
        if not datasets["risk_register.csv"].empty:
            risk_frame,risk_stats,_=risk_analysis(datasets["risk_register.csv"],10000)
            analysis["Risk Register Ranked"]=risk_frame
            report_metrics["Expected risk cost exposure"]=round(risk_stats["expected_cost_exposure"],2)
            report_metrics["Risk schedule exposure (days)"]=round(risk_stats["expected_schedule_exposure_days"],2)
        if not datasets["milestones.csv"].empty:
            analysis["Milestone Status"]=calculate_milestones(datasets["milestones.csv"],status_date)[0]
        if not datasets["resource_assignments.csv"].empty:
            analysis["Resource Allocation"]=calculate_resource_load(datasets["resources.csv"],datasets["resource_assignments.csv"])[0]
    except Exception as exc: st.warning(str(exc))
    if st.button("Generate integrated Excel workbook",type="primary"):
        try:
            book=export_workbook(datasets,analysis)
            st.session_state["report_excel"]=book
        except Exception as exc: st.exception(exc)
    if "report_excel" in st.session_state:
        st.download_button("⬇️ Download AI Project Control Report.xlsx",st.session_state["report_excel"],
            "AI_Project_Control_Report.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if st.button("Generate PDF management report"):
        try:
            st.session_state["report_pdf"]=generate_pdf_report(project_id,project_name,status_date,datasets,analysis,report_metrics)
        except Exception as exc: st.exception(exc)
    if "report_pdf" in st.session_state:
        st.download_button("⬇️ Download AI Project Control Report.pdf",st.session_state["report_pdf"],
            "AI_Project_Control_Report.pdf","application/pdf")
    st.divider()
    st.markdown("#### Optional Telegram delivery")
    st.caption("The PDF is sent only when you explicitly press Send. Bot token is not saved.")
    telegram_token=st.text_input("Telegram bot token",type="password",key="telegram_token")
    telegram_chat=st.text_input("Telegram chat ID",key="telegram_chat")
    if st.button("Send PDF report to Telegram"):
        try:
            pdf_bytes=st.session_state.get("report_pdf")
            if pdf_bytes is None:
                pdf_bytes=generate_pdf_report(project_id,project_name,status_date,datasets,analysis,report_metrics)
            if not telegram_token or not telegram_chat:
                st.error("Bot token and chat ID are required.")
            else:
                send_telegram_document(telegram_token,telegram_chat,pdf_bytes,"AI_Project_Control_Report.pdf",
                    f"{project_name} | {project_id} | {status_date}")
                st.success("PDF report sent to Telegram.")
        except Exception as exc: st.error(f"Telegram delivery failed: {exc}")
    st.markdown("#### Individual dataset exports")
    for name,frame in datasets.items():
        if not frame.empty:
            st.download_button(f"Download {name}",frame.to_csv(index=False).encode("utf-8-sig"),
                name,"text/csv",key="report_"+name)

with guide:
    st.subheader("User Guide")
    st.markdown("""
    **Recommended workflow**
    1. Create or select a project code in the sidebar.
    2. Import project master, WBS, activities, BOQ, progress, actual cost, risk register and commitments.
    3. Open Planning & CPM to inspect early/late dates, float and critical activities.
    4. Open Cost & EVM to inspect PV, EV, AC, SPI, CPI and forecasts.
    5. Update progress and actual cost each reporting period.
    6. Maintain risk register and run Monte Carlo scenarios.
    7. Import P6 resources, assignments and calendars or upload resource datasets.
    8. Maintain milestones and change register to monitor slippage and scope impact.
    9. Add approved crash duration and crash cost assumptions to eligible activities before optimization.
    10. Export the integrated workbook for management review.

    **Calculation policy**
    - CPM and EVM are deterministic engineering calculations.
    - Monte Carlo outputs are scenario distributions based on the entered uncertainty assumptions.
    - AI forecasting is intentionally not presented until sufficient historical, time-phased project data is available.
    - Primavera P6 remains the schedule authority for working calendars, resource levelling and native constraints.
    """)
    st.info("This integrated build is a local-first application. Project datasets are saved to SQLite on this computer. Backup restore validates the incoming datasets before an atomic database update; keep backup copies outside this computer.")

st.divider()
st.caption("AI Project Control System | Integrated V1 | Local-first project controls")
