"""Integrated calculation and data services for AI Project Control System.
Adapted integration layer around the audited project-control source engines.
"""
from __future__ import annotations
from datetime import date
from io import BytesIO
from pathlib import Path
import json
import os
import sqlite3
import numpy as np
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AIProjectControl"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "project_control.db"

TEMPLATES = {
 "project_master.csv": (["project_id","project_name","client","location","project_type","planned_start","planned_finish","status_date","currency"], ["PRJ-001","Demo Construction Project","Demo Client","Jakarta","Construction","2026-01-01","2026-12-31","2026-03-31","IDR"]),
 "wbs.csv": (["wbs_id","parent_wbs_id","wbs_name","description","responsible_party"], ["1.1","1","Foundation","Foundation works","Civil Team"]),
 "activities.csv": (["activity_id","wbs_id","activity_name","duration_days","planned_start","planned_finish","predecessor_ids","calendar_id","weight_pct"], ["A100","1.1","Excavation","10","2026-01-05","2026-01-14","","CAL-01","5"]),
 "boq_budget.csv": (["boq_id","wbs_id","item_code","description","unit","budget_quantity","unit_rate","budget_amount"], ["BOQ-001","1.1","CIV-001","Excavation","m3","1000","75000","75000000"]),
 "progress.csv": (["period_end","activity_id","boq_id","planned_quantity_to_date","actual_quantity_to_date","unit","evidence_reference","approved_by"], ["2026-03-31","A100","BOQ-001","800","650","m3","DAILY-REPORT-001","Site Engineer"]),
 "actual_cost.csv": (["transaction_date","wbs_id","boq_id","cost_code","cost_category","vendor","description","amount","currency","document_reference"], ["2026-03-31","1.1","BOQ-001","CIV-001","Material","Demo Vendor","Sample cost","25000000","IDR","INV-001"]),
 "risk_register.csv": (["risk_id","risk_description","cause","probability","cost_impact","schedule_impact_days","owner","response_strategy","mitigation_action","due_date","status"], ["R-001","Heavy rain","Seasonal weather","0.3","50000000","5","Project Manager","Mitigate","Prepare drainage","2026-04-15","Open"]),
 "commitments.csv": (["commitment_id","commitment_date","wbs_id","vendor","contract_or_po","description","committed_amount","paid_amount","currency","status"], ["COM-001","2026-02-01","1.1","Demo Vendor","PO-001","Equipment rental","100000000","25000000","IDR","Active"]),
}
REQUIRED = {
 "project_master.csv":["project_id","project_name","planned_start","planned_finish","status_date","currency"],
 "wbs.csv":["wbs_id","wbs_name"],
 "activities.csv":["activity_id","wbs_id","activity_name","duration_days","planned_start","planned_finish","predecessor_ids","weight_pct"],
 "boq_budget.csv":["boq_id","description","unit","budget_quantity","unit_rate"],
 "progress.csv":["period_end","activity_id","boq_id","actual_quantity_to_date"],
 "actual_cost.csv":["transaction_date","amount","currency"],
 "risk_register.csv":["risk_id","risk_description","probability","cost_impact","schedule_impact_days"],
 "commitments.csv":["commitment_id","committed_amount","currency"],
}

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS datasets(
          project_id TEXT NOT NULL, dataset_name TEXT NOT NULL, payload TEXT NOT NULL,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(project_id,dataset_name))""")

def save_dataset(project_id: str, name: str, frame: pd.DataFrame):
    init_db()
    payload = frame.to_json(orient="records", date_format="iso")
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""INSERT INTO datasets(project_id,dataset_name,payload,updated_at)
          VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(project_id,dataset_name)
          DO UPDATE SET payload=excluded.payload,updated_at=CURRENT_TIMESTAMP""",
          (project_id, name, payload))

def load_dataset(project_id: str, name: str):
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT payload FROM datasets WHERE project_id=? AND dataset_name=?",
                          (project_id,name)).fetchone()
    return pd.DataFrame(json.loads(row[0])) if row else pd.DataFrame()

def list_datasets(project_id: str):
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        return [r[0] for r in con.execute("SELECT dataset_name FROM datasets WHERE project_id=? ORDER BY dataset_name",(project_id,))]

def parse_xer(raw: bytes):
    text = raw.decode("latin-1", errors="replace")
    tables, current, fields = {}, None, []
    for line in text.splitlines():
        parts = line.rstrip("\r\n").split("\t")
        if not parts: continue
        if parts[0] == "%T" and len(parts)>1:
            current=parts[1].strip(); tables.setdefault(current,[])
        elif parts[0] == "%F" and current:
            fields=parts[1:]
        elif parts[0] == "%R" and current and fields:
            vals=parts[1:]
            if len(vals)<len(fields): vals += [""]*(len(fields)-len(vals))
            tables[current].append(dict(zip(fields,vals[:len(fields)])))
    return {k:pd.DataFrame(v) for k,v in tables.items()}

def xer_to_frames(tables):
    task=tables.get("TASK",pd.DataFrame()).copy()
    pred=tables.get("TASKPRED",pd.DataFrame()).copy()
    wbs=tables.get("PROJWBS",pd.DataFrame()).copy()
    if task.empty: raise ValueError("XER tidak memiliki tabel TASK berisi aktivitas.")
    def val(row, key, default=""):
        x=row.get(key,default)
        return default if pd.isna(x) else str(x)
    links={}
    code_by_id={val(r,"task_id"): (val(r,"task_code") or val(r,"task_id")) for _,r in task.iterrows()}
    if not pred.empty:
        for _,r in pred.iterrows():
            succ=val(r,"task_id"); pred_id=val(r,"pred_task_id")
            links.setdefault(succ,[]).append(code_by_id.get(pred_id,pred_id))
    acts=[]
    for _,r in task.iterrows():
        hours=pd.to_numeric(r.get("target_drtn_hr_cnt",0),errors="coerce")
        days=float(hours)/8.0 if pd.notna(hours) else 0.0
        start=val(r,"target_start_date") or val(r,"early_start_date")
        finish=val(r,"target_end_date") or val(r,"early_end_date")
        acts.append({"activity_id":val(r,"task_code") or val(r,"task_id"),
          "wbs_id":val(r,"wbs_id"),"activity_name":val(r,"task_name","Unnamed Activity"),
          "duration_days":days,"planned_start":start[:10],"planned_finish":finish[:10],
          "predecessor_ids":",".join(links.get(val(r,"task_id"),[])),
          "calendar_id":"P6-XER","weight_pct":0,
          "p6_task_id":val(r,"task_id"),"p6_status":val(r,"status_code")})
    wrows=[]
    for _,r in wbs.iterrows():
        wrows.append({"wbs_id":val(r,"wbs_id"),"parent_wbs_id":val(r,"parent_wbs_id"),
          "wbs_name":val(r,"wbs_name") or val(r,"wbs_short_name"),
          "description":"","responsible_party":""})
    return pd.DataFrame(acts),pd.DataFrame(wrows)

def validate_dataset(name: str, df: pd.DataFrame, existing: dict[str,pd.DataFrame]):
    issues=[]; missing=[c for c in REQUIRED.get(name,[]) if c not in df.columns]
    if missing: return ["Kolom wajib tidak ada: "+", ".join(missing)]
    if df.empty: return ["File tidak memiliki baris data."]
    if name=="activities.csv":
        if df["activity_id"].astype(str).duplicated().any(): issues.append("activity_id duplikat.")
        nums=pd.to_numeric(df["duration_days"],errors="coerce")
        if nums.isna().any() or (nums<0).any(): issues.append("duration_days harus angka >= 0.")
        for col in ["planned_start","planned_finish"]:
            if pd.to_datetime(df[col],errors="coerce").isna().any(): issues.append("Tanggal "+col+" tidak valid.")
        if "predecessor_ids" in df:
            ids=set(df["activity_id"].astype(str))
            for raw in df["predecessor_ids"].fillna(""):
                for p in str(raw).split(","):
                    p=p.strip()
                    if p and p not in ids: issues.append(f"Predecessor {p} tidak ditemukan.")
        wbs=existing.get("wbs.csv",pd.DataFrame())
        if not wbs.empty and "wbs_id" in wbs:
            missing_wbs=set(df["wbs_id"].astype(str))-set(wbs["wbs_id"].astype(str))
            if missing_wbs: issues.append("WBS tidak ditemukan: "+", ".join(sorted(missing_wbs)))
        try:
            weights=pd.to_numeric(df.get("weight_pct",0),errors="coerce")
            if hasattr(weights,"sum") and len(df) and abs(float(weights.sum())-100)>0.01:
                issues.append(f"Total weight_pct = {weights.sum():.2f}%, seharusnya 100%.")
        except Exception: pass
    if name=="wbs.csv" and df["wbs_id"].astype(str).duplicated().any(): issues.append("wbs_id duplikat.")
    if name=="boq_budget.csv":
        for c in ["budget_quantity","unit_rate"]:
            if c in df and (pd.to_numeric(df[c],errors="coerce").isna().any() or (pd.to_numeric(df[c],errors="coerce")<0).any()):
                issues.append(c+" harus angka >= 0.")
    if name=="risk_register.csv":
        p=pd.to_numeric(df["probability"],errors="coerce")
        if p.isna().any() or ((p<0)|(p>1)).any(): issues.append("probability harus antara 0 dan 1.")
    return issues

def calculate_cpm(activities: pd.DataFrame):
    if activities.empty: raise ValueError("Import activities terlebih dahulu.")
    records=[]
    for _,r in activities.iterrows():
        pred_raw=r.get("predecessor_ids","")
        pred_raw="" if pd.isna(pred_raw) else str(pred_raw)
        records.append({"id":str(r["activity_id"]),
          "duration":float(pd.to_numeric(r["duration_days"],errors="raise")),
          "predecessors":pred_raw})
    from pmcontrols.network import cpm
    result=cpm(records)
    out=result.table.copy()
    out=out.rename(columns={"activity":"activity_id","duration":"duration_days",
      "es":"early_start_day","ef":"early_finish_day","ls":"late_start_day",
      "lf":"late_finish_day","slack":"total_float_days","critical":"is_critical"})
    lookup=activities.set_index("activity_id")
    out["activity_name"]=out["activity_id"].map(lookup["activity_name"])
    out["wbs_id"]=out["activity_id"].map(lookup["wbs_id"])
    return out, result.stats

def calculate_evm(project: pd.DataFrame, activities: pd.DataFrame, boq: pd.DataFrame,
                  progress: pd.DataFrame, actual: pd.DataFrame, status_date):
    if boq.empty: raise ValueError("BOQ/budget belum diimpor.")
    b=boq.copy()
    if "budget_amount" not in b: b["budget_amount"]=pd.to_numeric(b["budget_quantity"],errors="coerce")*pd.to_numeric(b["unit_rate"],errors="coerce")
    b["budget_amount"]=pd.to_numeric(b["budget_amount"],errors="coerce").fillna(0)
    bac=float(b["budget_amount"].sum())
    if bac<=0: raise ValueError("BAC harus lebih besar dari nol.")
    sd=pd.Timestamp(status_date)
    a=activities.copy()
    a["planned_start"]=pd.to_datetime(a["planned_start"],errors="coerce")
    a["planned_finish"]=pd.to_datetime(a["planned_finish"],errors="coerce")
    a["weight_pct"]=pd.to_numeric(a.get("weight_pct",0),errors="coerce").fillna(0)
    a["budget_value"]=bac*a["weight_pct"]/100
    def planned(row):
        if pd.isna(row.planned_start) or pd.isna(row.planned_finish): return 0.0
        if sd<row.planned_start: return 0.0
        if sd>=row.planned_finish: return row.budget_value
        span=max(1,(row.planned_finish-row.planned_start).days+1)
        elapsed=(sd-row.planned_start).days+1
        return row.budget_value*min(1,max(0,elapsed/span))
    pv=float(a.apply(planned,axis=1).sum())
    if not progress.empty and "activity_id" in progress:
        p=progress.copy()
        p["period_end"]=pd.to_datetime(p.get("period_end"),errors="coerce")
        p=p[p["period_end"].isna() | (p["period_end"]<=sd)]
        p=p.sort_values("period_end").drop_duplicates(["activity_id","boq_id"] if "boq_id" in p else ["activity_id"],keep="last")
        p["actual_quantity_to_date"]=pd.to_numeric(p["actual_quantity_to_date"],errors="coerce").fillna(0)
        if "boq_id" in p and "boq_id" in b:
            q=b[["boq_id","budget_quantity","budget_amount"]].copy()
            q["budget_quantity"]=pd.to_numeric(q["budget_quantity"],errors="coerce").replace(0,np.nan)
            p=p.merge(q,on="boq_id",how="left")
            p["earned"]=p["budget_amount"].fillna(0)*(p["actual_quantity_to_date"]/p["budget_quantity"]).clip(0,1).fillna(0)
            ev=float(p.groupby("activity_id")["earned"].sum().sum())
        else: ev=0.0
    else: ev=0.0
    if ev==0 and "weight_pct" in a and not progress.empty:
        pass
    if not actual.empty:
        ac_frame=actual.copy()
        ac_frame["transaction_date"]=pd.to_datetime(ac_frame.get("transaction_date"),errors="coerce")
        ac_frame=ac_frame[ac_frame["transaction_date"].isna() | (ac_frame["transaction_date"]<=sd)]
        ac=float(pd.to_numeric(ac_frame.get("amount",pd.Series(dtype=float)),errors="coerce").fillna(0).sum())
    else: ac=0.0
    cpi=ev/ac if ac>0 else np.nan; spi=ev/pv if pv>0 else np.nan
    eac=bac/cpi if pd.notna(cpi) and cpi>0 else np.nan
    etc=eac-ac if pd.notna(eac) else np.nan
    vac=bac-eac if pd.notna(eac) else np.nan
    tcpi=(bac-ev)/(bac-ac) if bac>ac else np.nan
    return {"BAC":bac,"PV":pv,"EV":ev,"AC":ac,"SV":ev-pv,"CV":ev-ac,
      "SPI":spi,"CPI":cpi,"EAC":eac,"ETC":etc,"VAC":vac,"TCPI":tcpi,
      "physical_progress_pct":ev/bac*100}

def calculate_progress(activities, progress):
    if activities.empty: raise ValueError("Activities belum diimpor.")
    total=float(pd.to_numeric(activities.get("weight_pct",0),errors="coerce").fillna(0).sum())
    if progress.empty: return pd.DataFrame(), {"weighted_progress_pct":0.0,"reported_activities":0}
    p=progress.copy()
    p["actual_quantity_to_date"]=pd.to_numeric(p["actual_quantity_to_date"],errors="coerce").fillna(0)
    if "boq_id" in p:
        p=p.groupby(["activity_id","boq_id"],as_index=False)["actual_quantity_to_date"].max()
    return p, {"weighted_progress_pct":0.0 if total<=0 else None,"reported_activities":int(p["activity_id"].nunique())}

def risk_analysis(risks: pd.DataFrame, iterations=10000, seed=42):
    if risks.empty: raise ValueError("Risk register belum diimpor.")
    r=risks.copy()
    r["probability"]=pd.to_numeric(r["probability"],errors="coerce").fillna(0).clip(0,1)
    r["cost_impact"]=pd.to_numeric(r["cost_impact"],errors="coerce").fillna(0)
    r["schedule_impact_days"]=pd.to_numeric(r["schedule_impact_days"],errors="coerce").fillna(0)
    r["cost_exposure"]=r["probability"]*r["cost_impact"]
    r["schedule_exposure_days"]=r["probability"]*r["schedule_impact_days"]
    rng=np.random.default_rng(seed)
    probs=r["probability"].to_numpy()
    cost=r["cost_impact"].to_numpy()
    days=r["schedule_impact_days"].to_numpy()
    occur=rng.random((iterations,len(r)))<probs
    cost_samples=(occur*cost).sum(axis=1)
    day_samples=(occur*days).sum(axis=1)
    stats={"expected_cost_exposure":float(r["cost_exposure"].sum()),
      "expected_schedule_exposure_days":float(r["schedule_exposure_days"].sum()),
      "cost_p50":float(np.percentile(cost_samples,50)),"cost_p80":float(np.percentile(cost_samples,80)),
      "cost_p95":float(np.percentile(cost_samples,95)),"delay_p50":float(np.percentile(day_samples,50)),
      "delay_p80":float(np.percentile(day_samples,80)),"delay_p95":float(np.percentile(day_samples,95))}
    return r.sort_values("cost_exposure",ascending=False),stats,pd.DataFrame({"cost":cost_samples,"delay_days":day_samples})

def optimize_crash(activities: pd.DataFrame, target_days: float):
    required={"crash_duration_days","crash_cost_per_day"}
    if not required.issubset(activities.columns): raise ValueError("Tambahkan kolom crash_duration_days dan crash_cost_per_day untuk aktivitas yang dapat dipercepat.")
    rows=[]
    for _,r in activities.iterrows():
        pred_raw=r.get("predecessor_ids","")
        pred_raw="" if pd.isna(pred_raw) else str(pred_raw)
        rows.append({"id":str(r["activity_id"]),"duration":float(r["duration_days"]),
          "predecessors":pred_raw,
          "crash_duration":float(r["crash_duration_days"]),
          "crash_cost":float(r["crash_cost_per_day"])})
    from pmcontrols.crash import crash
    result=crash(rows,target=float(target_days))
    return result.table,result.stats

def export_workbook(datasets: dict[str,pd.DataFrame], analyses: dict[str,pd.DataFrame]):
    output=BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        for name,df in {**datasets,**analyses}.items():
            if isinstance(df,pd.DataFrame) and not df.empty:
                sheet=name.replace(".csv","")[:31]
                df.to_excel(writer,sheet_name=sheet,index=False)
    output.seek(0)
    return output.getvalue()


def calculate_xer_cpm(tables: dict[str,pd.DataFrame], hours_per_day=8):
    """Calendar-free XER CPM adapter retaining P6 FS/SS/FF/SF relationship types and lag."""
    task=tables.get("TASK",pd.DataFrame()).copy()
    rel=tables.get("TASKPRED",pd.DataFrame()).copy()
    if task.empty: raise ValueError("XER TASK table is empty.")
    ids=task["task_id"].astype(str).tolist()
    index={v:i for i,v in enumerate(ids)}
    duration={}
    for _,r in task.iterrows():
        value=pd.to_numeric(r.get("target_drtn_hr_cnt",0),errors="coerce")
        duration[str(r["task_id"])]=max(0.0,float(value)/hours_per_day) if pd.notna(value) else 0.0
    preds={i:[] for i in ids}; succs={i:[] for i in ids}
    if not rel.empty:
        for _,r in rel.iterrows():
            s=str(r.get("task_id","")); p=str(r.get("pred_task_id",""))
            if s not in index or p not in index: continue
            typ=str(r.get("pred_type","PR_FS") or "PR_FS")
            if typ not in {"PR_FS","PR_SS","PR_FF","PR_SF"}: typ="PR_FS"
            lag=pd.to_numeric(r.get("lag_hr_cnt",0),errors="coerce")
            lag=float(lag)/hours_per_day if pd.notna(lag) else 0.0
            preds[s].append((p,typ,lag)); succs[p].append((s,typ,lag))
    indeg={i:len(preds[i]) for i in ids}
    queue=[i for i in ids if indeg[i]==0]; order=[]
    while queue:
        node=queue.pop(0); order.append(node)
        for s,_,_ in succs[node]:
            indeg[s]-=1
            if indeg[s]==0: queue.append(s)
    if len(order)!=len(ids):
        cyclic=[i for i in ids if indeg[i]>0]
        raise ValueError("Precedence cycle detected in XER: "+", ".join(cyclic[:20]))
    es={}; ef={}
    for i in order:
        start=0.0; d=duration[i]
        for p,typ,lag in preds[i]:
            if typ=="PR_SS": cand=es[p]+lag
            elif typ=="PR_FF": cand=ef[p]+lag-d
            elif typ=="PR_SF": cand=es[p]+lag-d
            else: cand=ef[p]+lag
            start=max(start,cand)
        es[i]=start; ef[i]=start+d
    finish=max(ef.values(),default=0.0)
    ls={}; lf={}
    for i in reversed(order):
        end=finish; d=duration[i]
        for s,typ,lag in succs[i]:
            if typ=="PR_SS": cand=ls[s]-lag+d
            elif typ=="PR_FF": cand=lf[s]-lag
            elif typ=="PR_SF": cand=lf[s]-lag+d
            else: cand=ls[s]-lag
            end=min(end,cand)
        lf[i]=end; ls[i]=end-d
    byid=task.set_index(task["task_id"].astype(str))
    rows=[]
    for i in order:
        r=byid.loc[i]
        tf=ls[i]-es[i]
        rows.append({"task_id":i,"activity_code":str(r.get("task_code",i)),
          "activity_name":str(r.get("task_name","")),"duration_days":duration[i],
          "early_start_day":es[i],"early_finish_day":ef[i],"late_start_day":ls[i],
          "late_finish_day":lf[i],"total_float_days":tf,"critical":abs(tf)<1e-7})
    return pd.DataFrame(rows),{"project_duration_days":finish,"activities":len(rows),
      "critical_activities":int(sum(x["critical"] for x in rows)),
      "relationship_count":sum(len(v) for v in preds.values())}

def calculate_dcma14(tables: dict[str,pd.DataFrame], hours_per_day=8):
    """DCMA-style 14-point schedule health screen ported from the audited TPPSCI engine.
    Items without source evidence are explicitly marked Not Assessed.
    """
    task=tables.get("TASK",pd.DataFrame()).copy()
    rel=tables.get("TASKPRED",pd.DataFrame()).copy()
    if task.empty: raise ValueError("XER TASK table is empty.")
    def num(frame,col,default=0):
        if col not in frame: return pd.Series(default,index=frame.index,dtype=float)
        return pd.to_numeric(frame[col],errors="coerce").fillna(default)
    status=task.get("status_code",pd.Series("",index=task.index)).fillna("")
    incomplete=task[status!="TK_Complete"].copy()
    ninc=len(incomplete); nrel=len(rel); ntask=len(task)
    task_ids=set(task["task_id"].astype(str))
    pred_ids=set(rel.get("task_id",pd.Series(dtype=str)).astype(str))
    succ_ids=set(rel.get("pred_task_id",pd.Series(dtype=str)).astype(str))
    missing_logic=[]
    for _,r in incomplete.iterrows():
        tid=str(r["task_id"])
        if (tid not in pred_ids) or (tid not in succ_ids): missing_logic.append(tid)
    # Exclude the earliest true start and latest true finish from open-end counts.
    starts=[str(r["task_id"]) for _,r in incomplete.iterrows() if str(r["task_id"]) not in pred_ids]
    ends=[str(r["task_id"]) for _,r in incomplete.iterrows() if str(r["task_id"]) not in succ_ids]
    start_id=min(starts,key=lambda x: str(task.loc[task["task_id"].astype(str)==x].iloc[0].get("early_start_date",""))) if starts else None
    end_id=max(ends,key=lambda x: str(task.loc[task["task_id"].astype(str)==x].iloc[0].get("early_end_date",""))) if ends else None
    missing_logic=[x for x in missing_logic if not (x==start_id and x not in ends) and not (x==end_id and x not in starts)]
    lag=num(rel,"lag_hr_cnt")
    high_float=num(incomplete,"total_float_hr_cnt")>44*hours_per_day
    neg_float=num(incomplete,"total_float_hr_cnt")<0
    dur=num(incomplete,"remain_drtn_hr_cnt")
    dur=dur.where(dur>0,num(incomplete,"target_drtn_hr_cnt"))
    high_dur=dur>44*hours_per_day
    hard=incomplete.get("cstr_type",pd.Series("",index=incomplete.index)).fillna("").isin(
      ["CS_MANDSTART","CS_MANDFIN","CS_MSO","CS_MEO","CS_MEOB","CS_MAND"])
    data_date=None
    proj=tables.get("PROJECT",pd.DataFrame())
    if not proj.empty and "last_recalc_date" in proj:
        vals=pd.to_datetime(proj["last_recalc_date"],errors="coerce").dropna()
        if len(vals): data_date=vals.iloc[0]
    if data_date is None:
        dates=pd.to_datetime(pd.concat([task.get("act_start_date",pd.Series(dtype=str)),task.get("act_end_date",pd.Series(dtype=str))]),errors="coerce").dropna()
        if len(dates): data_date=dates.max()
    invalid=0; missed=0; should_finish=0
    if data_date is not None:
        forecast=pd.to_datetime(task.get("early_start_date",pd.Series(index=task.index,dtype=str)),errors="coerce")
        actual_start=pd.to_datetime(task.get("act_start_date",pd.Series(index=task.index,dtype=str)),errors="coerce")
        actual_end=pd.to_datetime(task.get("act_end_date",pd.Series(index=task.index,dtype=str)),errors="coerce")
        invalid=int((((status!="TK_Complete") & actual_start.isna() & forecast.notna() & (forecast<data_date)) |
                    (actual_start.notna() & (actual_start>data_date)) |
                    (actual_end.notna() & (actual_end>data_date))).sum())
        target_end=pd.to_datetime(task.get("target_end_date",task.get("early_end_date",pd.Series(index=task.index,dtype=str))),errors="coerce")
        due=target_end.notna() & (target_end<=data_date)
        should_finish=int(due.sum())
        missed=int((due & (status!="TK_Complete")).sum())
    res=tables.get("TASKRSRC",pd.DataFrame())
    if res.empty: resource_count=None
    else:
        assigned=set(res.get("task_id",pd.Series(dtype=str)).astype(str))
        resource_count=int(sum(1 for _,r in incomplete.iterrows() if float(pd.to_numeric(r.get("target_drtn_hr_cnt",0),errors="coerce") or 0)>0 and str(r["task_id"]) not in assigned))
    fs=int((rel.get("pred_type",pd.Series("PR_FS",index=rel.index)).fillna("PR_FS")=="PR_FS").sum()) if nrel else 0
    nonfs=nrel-fs
    rows=[
      (1,"Logic / open ends",len(missing_logic),ninc,"percent",len(missing_logic)/ninc*100 if ninc else 0),
      (2,"Leads / negative lag",int((lag<0).sum()),nrel,"count",int((lag<0).sum())),
      (3,"Lags / positive lag",int((lag>0).sum()),nrel,"percent",int((lag>0).sum())/nrel*100 if nrel else 0),
      (4,"Finish-to-Start relationships",fs,nrel,"percent",fs/nrel*100 if nrel else 0),
      (5,"Hard constraints",int(hard.sum()),ninc,"percent",int(hard.sum())/ninc*100 if ninc else 0),
      (6,"High float > 44d",int(high_float.sum()),ninc,"percent",int(high_float.sum())/ninc*100 if ninc else 0),
      (7,"Negative float",int(neg_float.sum()),ninc,"count",int(neg_float.sum())),
      (8,"High duration > 44d",int(high_dur.sum()),ninc,"percent",int(high_dur.sum())/ninc*100 if ninc else 0),
      (9,"Invalid dates",invalid,ntask,"count",invalid),
      (10,"Missing resource assignments",resource_count,None,"count",resource_count if resource_count is not None else np.nan),
      (11,"Missed tasks",missed,should_finish,"percent",missed/should_finish*100 if should_finish else 0),
      (12,"Critical path continuity",np.nan,None,"na",np.nan),
      (13,"Critical Path Length Index",np.nan,None,"na",np.nan),
      (14,"Baseline Execution Index",np.nan,None,"na",np.nan),
    ]
    out=[]
    for ident,name,count,total,unit,value in rows:
        if pd.isna(value): rag="Not Assessed"
        elif ident==4: rag="Green" if value>=90 else ("Amber" if value>=80 else "Red")
        elif ident==2 or ident==7: rag="Green" if value==0 else "Red"
        else: rag="Green" if value<=5 else ("Amber" if value<=10 else "Red")
        if ident==10 and resource_count is None: rag="Not Assessed"
        out.append({"DCMA Point":ident,"Metric":name,"Flagged":count,"Population":total,
                    "Value":value,"RAG":rag})
    return pd.DataFrame(out)


def calculate_schedule_pert(activities: pd.DataFrame, iterations=10000, seed=42):
    """Three-point schedule-risk analysis using the audited pmcontrols PERT engine."""
    if activities.empty: raise ValueError("Activities belum diimpor.")
    rows=[]
    for _,r in activities.iterrows():
        d=float(pd.to_numeric(r["duration_days"],errors="raise"))
        pred=r.get("predecessor_ids","")
        pred="" if pd.isna(pred) else str(pred)
        rows.append({"id":str(r["activity_id"]),"predecessors":pred,
          "optimistic":d*0.90 if d>0 else 0.0,"most_likely":d,"pessimistic":d*1.25 if d>0 else 0.0})
    from pmcontrols.network import pert
    result=pert(rows,n_sim=int(iterations),seed=int(seed),keep_samples=True)
    return result.table,result.stats,result.meta

def add_earned_schedule_metrics(evm_stats, project, activities, status_date):
    """Use pmcontrols' PMB / earned-schedule engine when a valid time-phased baseline exists."""
    from pmcontrols import plan, evm as pm_evm
    if activities.empty or project.empty: return evm_stats
    try:
        start=pd.to_datetime(project.iloc[0]["planned_start"])
        finish=pd.to_datetime(project.iloc[0]["planned_finish"])
        sd=pd.Timestamp(status_date)
        if pd.isna(start) or pd.isna(finish) or finish<=start: return evm_stats
        a=activities.copy()
        a["planned_start"]=pd.to_datetime(a["planned_start"],errors="coerce")
        a["planned_finish"]=pd.to_datetime(a["planned_finish"],errors="coerce")
        a["weight_pct"]=pd.to_numeric(a["weight_pct"],errors="coerce").fillna(0)
        bac=float(evm_stats["BAC"])
        budget=a["weight_pct"]*bac/100.0
        duration=max(1,(finish-start).days)
        pv_curve=[]
        for day in range(duration+1):
            current=start+pd.Timedelta(days=day)
            total=0.0
            for idx,row in a.iterrows():
                s=row["planned_start"]; f=row["planned_finish"]
                if pd.isna(s) or pd.isna(f): continue
                span=max(1,(f-s).days+1)
                fraction=min(1.0,max(0.0,((current-s).days+1)/span))
                total+=float(budget.loc[idx])*fraction
            pv_curve.append(min(bac,max(0.0,total)))
        pv_curve[-1]=bac
        pmb=plan(list(range(duration+1)),pv_curve)
        at=max(0.0,min(float(duration),float((sd-start).days)))
        result=pm_evm(pmb,ev=float(min(bac,max(0.0,evm_stats["EV"]))),
                      ac=float(max(0.0,evm_stats["AC"])),at=at)
        for key in ["es","sv_t","spi_t","ieac_t"]:
            evm_stats[{"es":"ES","sv_t":"SV(t)","spi_t":"SPI(t)","ieac_t":"IEAC(t)"}[key]]=result.stats[key]
        return evm_stats
    except Exception:
        return evm_stats


def parse_xer_with_pyp6xer(raw: bytes):
    """Parse XER with PyP6Xer v2 object model and run its full DCMA14 analysis."""
    import os, tempfile
    from xerparser.reader import Reader
    from xerparser.dcma14 import DCMA14
    handle=tempfile.NamedTemporaryFile(prefix="aipc_",suffix=".xer",delete=False)
    path=handle.name
    try:
        handle.write(raw); handle.close()
        reader=Reader(path)
        activities=list(reader.activities.activities)
        projects=list(reader.projects)
        resources=list(reader.resources)
        calendars=list(reader.calendars)
        relations=list(reader.relations)
        assignments=list(reader.activityresources)
        wbs=list(reader.wbss)
        def records(items, fields):
            output=[]
            for item in items:
                row={}
                for field in fields:
                    value=getattr(item,field,None)
                    if isinstance(value,(str,int,float,bool)) or value is None:
                        row[field]=value
                    else:
                        row[field]=str(value)
                output.append(row)
            return pd.DataFrame(output)
        activity_frame=records(activities,["task_id","task_code","task_name","wbs_id","status_code",
          "duration","target_drtn_hr_cnt","remain_drtn_hr_cnt","total_float_hr_cnt","free_float_hr_cnt",
          "target_start_date","target_end_date","early_start_date","early_end_date","act_start_date",
          "act_end_date","phys_complete_pct","calendar_id"])
        resource_frame=records(resources,["rsrc_id","rsrc_name","rsrc_type","unit_of_measure"])
        assignment_frame=records(assignments,["task_id","rsrc_id","target_qty","act_reg_qty","target_cost","act_reg_cost","act_ot_cost"])
        calendar_frame=records(calendars,["clndr_id","clndr_name","day_hr_cnt","week_hr_cnt","month_hr_cnt","year_hr_cnt"])
        wbs_frame=records(wbs,["wbs_id","wbs_name","parent_wbs_id","proj_id"])
        relation_frame=records(relations,["task_id","pred_task_id","pred_type","lag_hr_cnt"])
        dcma=DCMA14(reader).analysis()["analysis"]
        metric_rows=[]
        labels={"successors":"Activities without successors","predecessors":"Activities without predecessors",
          "lags":"Positive relationship lags","leads":"Negative relationship leads","relations":"Finish-to-Start relationships",
          "constraints":"Hard constraints","totalfloat":"High total float","negativefloat":"Negative total float",
          "duration":"Long duration activities","invaliddates":"Invalid dates","resources":"Missing resource assignments",
          "slippage":"Schedule slippage","critical_test":"Critical path continuity","cpli":"Critical Path Length Index",
          "bei":"Baseline Execution Index"}
        for key,value in dcma.items():
            if not isinstance(value,dict): continue
            count=value.get("cnt",value.get("fs_cnt",value.get("cstr_cnt")))
            pct=value.get("pct")
            score=value.get("cpli",value.get("bei"))
            passed=value.get("passed")
            metric_rows.append({"DCMA check":labels.get(key,key),"Count":count,
              "Percentage":pct,"Score":score,"Passed":passed})
        summary={"projects":len(projects),"activities":len(activities),"relationships":len(relations),
          "WBS elements":len(wbs),"resources":len(resources),"resource assignments":len(assignments),
          "calendars":len(calendars)}
        return {"summary":summary,"activities":activity_frame,"resources":resource_frame,
          "resource_assignments":assignment_frame,"calendars":calendar_frame,"wbs":wbs_frame,
          "relationships":relation_frame,"dcma14":pd.DataFrame(metric_rows)}
    finally:
        try: os.unlink(path)
        except OSError: pass
