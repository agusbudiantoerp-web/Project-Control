"""Integrated calculation and data services for AI Project Control System.
Adapted integration layer around the audited project-control source engines.
"""
from __future__ import annotations
from datetime import date
from io import BytesIO
from pathlib import Path
import json
import os
import re
import sqlite3
import numpy as np
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AIProjectControl"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "project_control.db"

TEMPLATES = {
 "project_master.csv": (["project_id","project_name","client","location","project_type","planned_start","planned_finish","status_date","currency"], ["PRJ-001","Demo Construction Project","Demo Client","Jakarta","Construction","2026-01-01","2026-12-31","2026-03-31","IDR"]),
 "wbs.csv": (["wbs_id","parent_wbs_id","wbs_name","description","responsible_party"], ["1.1","","Foundation","Foundation works","Civil Team"]),
 "activities.csv": (["activity_id","wbs_id","activity_name","duration_days","planned_start","planned_finish","predecessor_ids","calendar_id","weight_pct"], ["A100","1.1","Excavation","10","2026-01-05","2026-01-14","","CAL-01","100"]),
 "boq_budget.csv": (["boq_id","wbs_id","item_code","description","unit","budget_quantity","unit_rate","budget_amount"], ["BOQ-001","1.1","CIV-001","Excavation","m3","1000","75000","75000000"]),
 "progress.csv": (["period_end","activity_id","boq_id","planned_quantity_to_date","actual_quantity_to_date","unit","evidence_reference","approved_by"], ["2026-03-31","A100","BOQ-001","800","650","m3","DAILY-REPORT-001","Site Engineer"]),
 "actual_cost.csv": (["transaction_date","wbs_id","boq_id","cost_code","cost_category","vendor","description","amount","currency","document_reference"], ["2026-03-31","1.1","BOQ-001","CIV-001","Material","Demo Vendor","Sample cost","25000000","IDR","INV-001"]),
 "risk_register.csv": (["risk_id","risk_description","cause","probability","cost_impact","schedule_impact_days","owner","response_strategy","mitigation_action","due_date","status"], ["R-001","Heavy rain","Seasonal weather","0.3","50000000","5","Project Manager","Mitigate","Prepare drainage","2026-04-15","Open"]),
 "commitments.csv": (["commitment_id","commitment_date","wbs_id","vendor","contract_or_po","description","committed_amount","paid_amount","currency","status"], ["COM-001","2026-02-01","1.1","Demo Vendor","PO-001","Equipment rental","100000000","25000000","IDR","Active"]),
 "resources.csv": (["rsrc_id","rsrc_name","rsrc_type","unit_of_measure","capacity_per_day"], ["R-CRANE-01","Mobile Crane","Equipment","hour","8"]),
 "resource_assignments.csv": (["task_id","rsrc_id","target_qty","actual_qty","target_cost","actual_cost","target_start_date","target_end_date"], ["A100","R-CRANE-01","40","0","10000000","0","2026-01-01","2026-01-05"]),
 "calendars.csv": (["calendar_id","calendar_name","workdays_per_week","hours_per_day","holidays"], ["CAL-01","Six-day workweek","6","8",""]),
 "relationships.csv": (["task_id","pred_task_id","pred_type","lag_hr_cnt"], ["","","PR_FS","0"]),
 "milestones.csv": (["milestone_id","milestone_name","planned_date","forecast_date","actual_date","status","owner"], ["M-001","Foundation Complete","2026-02-12","2026-02-14","","At Risk","Project Manager"]),
 "change_register.csv": (["change_id","date_raised","description","cost_impact","schedule_impact_days","status","approved_by"], ["CR-001","2026-03-01","Additional drainage scope","15000000","3","Pending",""]),
 "drawing_takeoff.csv": (["drawing_id","page","discipline","item_code","description","unit","quantity","measurement_method","confidence","assumptions","review_status"], ["DWG-001","1","Civil","ITM-001","Concrete slab","m3","","Scale / dimensions required","Low","Verify drawing scale and dimensions","Pending Review"]),
}
REQUIRED = {
 "project_master.csv":["project_id","project_name","planned_start","planned_finish","status_date","currency"],
 "wbs.csv":["wbs_id","wbs_name"],
 "activities.csv":["activity_id","wbs_id","activity_name","duration_days","planned_start","planned_finish","predecessor_ids","weight_pct"],
 "boq_budget.csv":["boq_id","wbs_id","description","unit","budget_quantity","unit_rate"],
 "progress.csv":["period_end","activity_id","boq_id","actual_quantity_to_date"],
 "actual_cost.csv":["transaction_date","amount","currency"],
 "risk_register.csv":["risk_id","risk_description","probability","cost_impact","schedule_impact_days"],
 "commitments.csv":["commitment_id","commitment_date","committed_amount","paid_amount","currency"],
 "resources.csv":["rsrc_id","rsrc_name","rsrc_type"],
 "resource_assignments.csv":["task_id","rsrc_id","target_qty"],
 "calendars.csv":["calendar_id","calendar_name","workdays_per_week","hours_per_day"],
 "relationships.csv":["task_id","pred_task_id","pred_type"],
 "milestones.csv":["milestone_id","milestone_name","planned_date","status"],
 "change_register.csv":["change_id","date_raised","description","cost_impact","schedule_impact_days","status"],
 "drawing_takeoff.csv":["drawing_id","page","discipline","description","unit","quantity","confidence","review_status"],
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

def list_project_ids():
    """Return all project IDs available in the local portfolio database."""
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute("SELECT DISTINCT project_id FROM datasets ORDER BY project_id").fetchall()
    return [row[0] for row in rows]


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
            if hasattr(weights,"sum") and len(df) and float(pd.to_numeric(weights,errors="coerce").fillna(0).abs().sum())>0 and abs(float(weights.sum())-100)>0.01:
                issues.append(f"Total weight_pct = {weights.sum():.2f}%, seharusnya 100%. Isi 0 semua diperbolehkan untuk data jadwal XER tanpa pembobotan EVM.")
        except Exception: pass
    unique_keys={"project_master.csv":"project_id","wbs.csv":"wbs_id","boq_budget.csv":"boq_id",
      "risk_register.csv":"risk_id","resources.csv":"rsrc_id","milestones.csv":"milestone_id",
      "change_register.csv":"change_id","resource_assignments.csv":None}
    key=unique_keys.get(name)
    if key and key in df and df[key].astype(str).duplicated().any():
        issues.append(f"{key} duplikat.")
    if name=="wbs.csv":
        wbs_ids=set(df["wbs_id"].astype(str))
        parents=df.get("parent_wbs_id",pd.Series("",index=df.index)).fillna("").astype(str)
        for wbs_id,parent in zip(df["wbs_id"].astype(str),parents):
            if parent and parent!="nan" and parent not in wbs_ids:
                issues.append(f"Parent WBS {parent} untuk {wbs_id} tidak ditemukan.")
            if parent==wbs_id: issues.append(f"WBS {wbs_id} tidak boleh menjadi parent dirinya sendiri.")
    if name=="activities.csv":
        start=pd.to_datetime(df["planned_start"],errors="coerce")
        finish=pd.to_datetime(df["planned_finish"],errors="coerce")
        if (finish<start).any(): issues.append("planned_finish tidak boleh lebih awal daripada planned_start.")
        if (df["activity_id"].astype(str)==df.get("predecessor_ids",pd.Series("",index=df.index)).fillna("").astype(str)).any():
            issues.append("Aktivitas tidak boleh menjadi predecessor dirinya sendiri.")
    if name=="boq_budget.csv":
        if df["boq_id"].astype(str).duplicated().any(): issues.append("boq_id duplikat.")
        if "budget_amount" in df:
            amounts=pd.to_numeric(df["budget_amount"],errors="coerce")
            if amounts.notna().any() and (amounts.dropna()<0).any(): issues.append("budget_amount tidak boleh negatif.")
        acts=existing.get("activities.csv",pd.DataFrame())
        wbs=existing.get("wbs.csv",pd.DataFrame())
        valid_wbs=set(wbs["wbs_id"].astype(str)) if not wbs.empty else set()
        if valid_wbs:
            missing=set(df["wbs_id"].astype(str))-valid_wbs
            if missing: issues.append("WBS BOQ tidak ditemukan: "+", ".join(sorted(missing)))
    if name=="resource_assignments.csv":
        resources=existing.get("resources.csv",pd.DataFrame())
        if not resources.empty:
            missing=set(df["rsrc_id"].astype(str))-set(resources["rsrc_id"].astype(str))
            if missing: issues.append("Resource tidak ditemukan: "+", ".join(sorted(missing)))
        activities=existing.get("activities.csv",pd.DataFrame())
        if not activities.empty:
            missing=set(df["task_id"].astype(str))-set(activities["activity_id"].astype(str))
            if missing: issues.append("Activity assignment tidak ditemukan: "+", ".join(sorted(missing)))
    if name=="milestones.csv":
        planned=pd.to_datetime(df["planned_date"],errors="coerce")
        if planned.isna().any(): issues.append("planned_date harus berisi tanggal yang valid.")
    if name=="change_register.csv":
        for col in ["cost_impact","schedule_impact_days"]:
            vals=pd.to_numeric(df[col],errors="coerce")
            if vals.isna().any(): issues.append(col+" harus berupa angka.")

    if name=="boq_budget.csv":
        for c in ["budget_quantity","unit_rate"]:
            if c in df and (pd.to_numeric(df[c],errors="coerce").isna().any() or (pd.to_numeric(df[c],errors="coerce")<0).any()):
                issues.append(c+" harus angka >= 0.")
    if name=="risk_register.csv":
        p=pd.to_numeric(df["probability"],errors="coerce")
        if p.isna().any() or ((p<0)|(p>1)).any(): issues.append("probability harus antara 0 dan 1.")
    if name=="progress.csv":
        q=pd.to_numeric(df["actual_quantity_to_date"],errors="coerce")
        if q.isna().any() or (q<0).any(): issues.append("actual_quantity_to_date harus angka >= 0.")
        acts=existing.get("activities.csv",pd.DataFrame())
        if not acts.empty and "activity_id" in acts:
            missing_ids=set(df["activity_id"].astype(str))-set(acts["activity_id"].astype(str))
            if missing_ids: issues.append("Activity tidak ditemukan: "+", ".join(sorted(missing_ids)))
        budget=existing.get("boq_budget.csv",pd.DataFrame())
        if not budget.empty and "boq_id" in budget:
            missing_boq=set(df["boq_id"].astype(str))-set(budget["boq_id"].astype(str))
            if missing_boq: issues.append("BOQ tidak ditemukan: "+", ".join(sorted(missing_boq)))
            if not acts.empty and {"activity_id","wbs_id"}.issubset(acts.columns) and {"boq_id","wbs_id"}.issubset(budget.columns):
                activity_wbs=acts.set_index(acts["activity_id"].astype(str))["wbs_id"].astype(str).to_dict()
                boq_wbs=budget.set_index(budget["boq_id"].astype(str))["wbs_id"].astype(str).to_dict()
                for _, row in df.iterrows():
                    activity_id=str(row["activity_id"]); boq_id=str(row["boq_id"])
                    if activity_id in activity_wbs and boq_id in boq_wbs and activity_wbs[activity_id]!=boq_wbs[boq_id]:
                        issues.append(f"Progress activity {activity_id} dan BOQ {boq_id} berada pada WBS berbeda.")
    if name=="actual_cost.csv":
        amount=pd.to_numeric(df["amount"],errors="coerce")
        if amount.isna().any() or not np.isfinite(amount).all() or (amount<0).any():
            issues.append("amount harus angka finite >= 0.")
        dates=pd.to_datetime(df["transaction_date"],errors="coerce")
        if dates.isna().any(): issues.append("transaction_date harus tanggal valid.")
        if df["currency"].isna().any() or df["currency"].astype(str).str.strip().eq("").any():
            issues.append("currency tidak boleh kosong.")
        master=existing.get("project_master.csv",pd.DataFrame())
        if not master.empty and "currency" in master:
            expected=set(master["currency"].dropna().astype(str).str.upper())
            found=set(df["currency"].dropna().astype(str).str.upper())
            if expected and found-expected: issues.append("Mata uang actual_cost tidak sama dengan mata uang proyek.")
    if name=="commitments.csv":
        for col in ["committed_amount","paid_amount"]:
            values=pd.to_numeric(df[col],errors="coerce")
            if values.isna().any() or not np.isfinite(values).all() or (values<0).any():
                issues.append(col+" harus angka finite >= 0.")
        committed=pd.to_numeric(df["committed_amount"],errors="coerce")
        paid=pd.to_numeric(df["paid_amount"],errors="coerce")
        if committed.notna().all() and paid.notna().all() and (paid>committed).any():
            issues.append("paid_amount tidak boleh melebihi committed_amount.")
        dates=pd.to_datetime(df["commitment_date"],errors="coerce")
        if dates.isna().any(): issues.append("commitment_date harus tanggal valid.")
        if df["currency"].isna().any() or df["currency"].astype(str).str.strip().eq("").any():
            issues.append("currency komitmen tidak boleh kosong.")
        master=existing.get("project_master.csv",pd.DataFrame())
        if not master.empty and "currency" in master:
            expected=set(master["currency"].dropna().astype(str).str.upper())
            found=set(df["currency"].dropna().astype(str).str.upper())
            if expected and found-expected: issues.append("Mata uang komitmen tidak sama dengan mata uang proyek.")
    if name=="risk_register.csv":
        for col in ["cost_impact","schedule_impact_days"]:
            values=pd.to_numeric(df[col],errors="coerce")
            if values.isna().any() or not np.isfinite(values).all() or (values<0).any():
                issues.append(col+" harus angka finite >= 0.")
    if name=="resources.csv" and "capacity_per_day" in df:
        capacity=pd.to_numeric(df["capacity_per_day"],errors="coerce")
        invalid=capacity.notna() & ((capacity<=0) | ~np.isfinite(capacity))
        if invalid.any(): issues.append("capacity_per_day harus > 0 jika diisi.")
    if name=="change_register.csv":
        for col in ["cost_impact","schedule_impact_days"]:
            values=pd.to_numeric(df[col],errors="coerce")
            if values.isna().any() or not np.isfinite(values).all() or (values<0).any():
                issues.append(col+" harus angka finite >= 0.")
    if name=="project_master.csv":
        for col in ["planned_start","planned_finish","status_date"]:
            values=pd.to_datetime(df[col],errors="coerce")
            if values.isna().any(): issues.append(col+" harus tanggal valid.")
        if not df["currency"].astype(str).str.strip().ne("").all():
            issues.append("currency proyek tidak boleh kosong.")
        start=pd.to_datetime(df["planned_start"],errors="coerce")
        finish=pd.to_datetime(df["planned_finish"],errors="coerce")
        if (finish<start).any(): issues.append("planned_finish tidak boleh sebelum planned_start.")
    if name=="progress.csv":
        periods=pd.to_datetime(df["period_end"],errors="coerce")
        if periods.isna().any(): issues.append("period_end harus tanggal valid.")
    if name=="resources.csv" and df["rsrc_id"].astype(str).duplicated().any():
        issues.append("rsrc_id duplikat.")
    return issues


def validate_project_datasets(datasets: dict[str,pd.DataFrame]):
    """Validate all supplied non-empty datasets against one consistent project snapshot."""
    issues={}
    snapshot={name:frame for name,frame in datasets.items()
              if name in TEMPLATES and isinstance(frame,pd.DataFrame) and not frame.empty}
    for name,frame in snapshot.items():
        findings=validate_dataset(name,frame,snapshot)
        if findings:
            issues[name]=findings
    return issues

def calculate_cpm(activities: pd.DataFrame):
    if activities.empty: raise ValueError("Import activities terlebih dahulu.")
    required={"activity_id","duration_days"}
    missing=required-set(activities.columns)
    if missing:
        raise ValueError("Activities missing CPM columns: "+", ".join(sorted(missing)))
    frame=activities.copy()
    ids=frame["activity_id"]
    if ids.isna().any() or ids.astype(str).str.strip().eq("").any():
        raise ValueError("CPM activity_id harus terisi dan unik.")
    frame["activity_id"]=ids.astype(str).str.strip()
    if frame["activity_id"].duplicated().any():
        raise ValueError("CPM activity_id harus terisi dan unik.")
    durations=pd.to_numeric(frame["duration_days"],errors="coerce")
    if durations.isna().any() or not np.isfinite(durations).all() or (durations<0).any():
        raise ValueError("CPM duration_days harus berupa angka finite dan tidak negatif.")
    frame["duration_days"]=durations.astype(float)
    if "predecessor_ids" not in frame:
        frame["predecessor_ids"]=""
    known=set(frame["activity_id"])
    records=[]
    for _,r in frame.iterrows():
        pred_raw=r.get("predecessor_ids","")
        pred_raw="" if pd.isna(pred_raw) else str(pred_raw)
        predecessors=[p.strip() for p in pred_raw.split(",") if p.strip()]
        if r["activity_id"] in predecessors:
            raise ValueError(f"CPM activity {r['activity_id']} tidak boleh menjadi predecessor dirinya sendiri.")
        unknown=sorted(set(predecessors)-known)
        if unknown:
            raise ValueError(f"CPM unknown predecessor (predecessor tidak ditemukan) untuk {r['activity_id']}: "+", ".join(unknown))
        records.append({"id":r["activity_id"],
          "duration":float(r["duration_days"]),
          "predecessors":",".join(predecessors)})
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
    """Calculate auditable EVM using BOQ value and WBS-weighted activity allocation.

    Progress rows are cumulative quantities; only the latest report per
    activity/BOQ at or before status_date is used.
    """
    if boq.empty: raise ValueError("BOQ/budget belum diimpor.")
    if activities.empty: raise ValueError("Activities belum diimpor.")
    required_boq={"boq_id","wbs_id","budget_quantity","unit_rate"}
    missing=required_boq-set(boq.columns)
    if missing: raise ValueError("BOQ missing columns: "+", ".join(sorted(missing)))
    required_act={"activity_id","wbs_id","planned_start","planned_finish","weight_pct"}
    missing=required_act-set(activities.columns)
    if missing: raise ValueError("Activities missing columns: "+", ".join(sorted(missing)))
    b=boq.copy()
    if b["boq_id"].isna().any() or b["boq_id"].astype(str).str.strip().eq("").any():
        raise ValueError("BOQ contains blank boq_id values.")
    if b["wbs_id"].isna().any() or b["wbs_id"].astype(str).str.strip().eq("").any():
        raise ValueError("BOQ contains blank wbs_id values.")
    if b["boq_id"].astype(str).duplicated().any():
        raise ValueError("BOQ contains duplicate boq_id values.")
    b["budget_quantity"]=pd.to_numeric(b["budget_quantity"],errors="coerce")
    b["unit_rate"]=pd.to_numeric(b["unit_rate"],errors="coerce")
    if b[["budget_quantity","unit_rate"]].isna().any().any() or (b[["budget_quantity","unit_rate"]]<0).any().any():
        raise ValueError("BOQ budget_quantity and unit_rate must be valid non-negative numbers.")
    calculated_amount=b["budget_quantity"]*b["unit_rate"]
    if "budget_amount" in b:
        supplied=pd.to_numeric(b["budget_amount"],errors="coerce")
        if supplied.isna().any() or (supplied<0).any():
            raise ValueError("BOQ budget_amount must be valid and non-negative.")
        # Approved BOQ amount is authoritative; absent amount is derived from quantity x rate.
        b["budget_amount"]=supplied
    else:
        b["budget_amount"]=calculated_amount
    bac=float(b["budget_amount"].sum())
    if bac<=0: raise ValueError("BAC harus lebih besar dari nol.")
    sd=pd.to_datetime(status_date,errors="coerce")
    if pd.isna(sd): raise ValueError("Status date tidak valid.")
    a=activities.copy()
    if a["activity_id"].isna().any() or a["activity_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Activities contain blank activity_id values.")
    if a["wbs_id"].isna().any() or a["wbs_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Activities contain blank wbs_id values.")
    if a["activity_id"].astype(str).duplicated().any():
        raise ValueError("Activities contain duplicate activity_id values.")
    a["planned_start"]=pd.to_datetime(a["planned_start"],errors="coerce")
    a["planned_finish"]=pd.to_datetime(a["planned_finish"],errors="coerce")
    if a[["planned_start","planned_finish"]].isna().any().any():
        raise ValueError("Activity planned_start / planned_finish contains invalid dates.")
    reversed_dates=a["planned_finish"]<a["planned_start"]
    if reversed_dates.any():
        bad_ids=a.loc[reversed_dates,"activity_id"].astype(str).head(10).tolist()
        raise ValueError("Activity planned_finish cannot be earlier than planned_start: "+", ".join(bad_ids))
    a["weight_pct"]=pd.to_numeric(a["weight_pct"],errors="coerce")
    if a["weight_pct"].isna().any() or (a["weight_pct"]<0).any():
        raise ValueError("Activity weight_pct must be valid and non-negative.")
    weight_by_wbs=a.groupby(a["wbs_id"].astype(str))["weight_pct"].transform("sum")
    if (weight_by_wbs<=0).any():
        raise ValueError("Each WBS with BOQ value must have positive activity weight_pct.")
    boq_wbs=set(b["wbs_id"].astype(str))
    activity_wbs=set(a["wbs_id"].astype(str))
    missing_wbs=boq_wbs-activity_wbs
    if missing_wbs:
        raise ValueError("BOQ WBS has no mapped activity; progress and activity must share the same WBS: "+", ".join(sorted(missing_wbs)))
    a["wbs_share"]=a["weight_pct"]/weight_by_wbs
    a["budget_value"]=0.0
    # Allocate each BOQ item to activities in the same WBS, proportionally to activity weights.
    wbs_budget=b.groupby(b["wbs_id"].astype(str))["budget_amount"].sum().to_dict()
    a["budget_value"]=a.apply(lambda row: wbs_budget.get(str(row["wbs_id"]),0.0)*row["wbs_share"],axis=1)
    def planned(row):
        if sd<row.planned_start: return 0.0
        if sd>=row.planned_finish: return row.budget_value
        span=max(1,(row.planned_finish-row.planned_start).days+1)
        elapsed=(sd-row.planned_start).days+1
        return row.budget_value*min(1,max(0,elapsed/span))
    pv=float(a.apply(planned,axis=1).sum())
    ev_detail=pd.DataFrame(columns=["activity_id","wbs_id","budget_value","earned_value"])
    ev=0.0
    if not progress.empty:
        required_progress={"period_end","activity_id","boq_id","actual_quantity_to_date"}
        missing=required_progress-set(progress.columns)
        if missing: raise ValueError("Progress missing columns: "+", ".join(sorted(missing)))
        p=progress.copy()
        p["period_end"]=pd.to_datetime(p["period_end"],errors="coerce")
        if p["period_end"].isna().any():
            raise ValueError("Progress contains invalid period_end dates.")
        p=p[p["period_end"]<=sd].copy()
        if not p.empty:
            p["actual_quantity_to_date"]=pd.to_numeric(p["actual_quantity_to_date"],errors="coerce")
            if p["actual_quantity_to_date"].isna().any() or (p["actual_quantity_to_date"]<0).any():
                raise ValueError("actual_quantity_to_date must be valid and non-negative.")
            activity_ids=set(a["activity_id"].astype(str))
            boq_ids=set(b["boq_id"].astype(str))
            unknown_activities=set(p["activity_id"].astype(str))-activity_ids
            unknown_boq=set(p["boq_id"].astype(str))-boq_ids
            if unknown_activities: raise ValueError("Progress references unknown activities: "+", ".join(sorted(unknown_activities)))
            if unknown_boq: raise ValueError("Progress references unknown BOQ: "+", ".join(sorted(unknown_boq)))
            duplicate_reports = p.duplicated(
                ["period_end", "activity_id", "boq_id"], keep=False
            )
            if duplicate_reports.any():
                duplicate_keys = p.loc[duplicate_reports, ["period_end", "activity_id", "boq_id"]]
                examples = duplicate_keys.astype(str).drop_duplicates().head(5)
                detail = "; ".join(
                    f"{row.period_end} / {row.activity_id} / {row.boq_id}"
                    for row in examples.itertuples(index=False)
                )
                raise ValueError(
                    "Progress contains duplicate rows for the same reporting period, "
                    f"activity and BOQ. Resolve duplicates before EVM: {detail}"
                )
            p=p.sort_values("period_end").drop_duplicates(["activity_id","boq_id"],keep="last")
            q=b[["boq_id","wbs_id","budget_quantity","budget_amount"]].copy()
            allocation=a[["activity_id","wbs_id","wbs_share"]].copy()
            p=p.merge(q,on="boq_id",how="left",validate="many_to_one")
            p=p.merge(allocation,on="activity_id",how="left",suffixes=("_boq","_activity"),validate="many_to_one")
            mismatch=p[p["wbs_id_boq"].astype(str)!=p["wbs_id_activity"].astype(str)]
            if not mismatch.empty:
                raise ValueError("Progress activity and BOQ must belong to the same WBS.")
            if (p["budget_quantity"]<=0).any():
                raise ValueError("BOQ budget_quantity must be greater than zero for reported progress.")
            # Progress quantities are activity-specific. Each activity earns
            # only its normalized share of the WBS BOQ budget; summing quantities
            # across activities would reject valid allocations where each activity
            # reports completion against its own assigned work package.
            overreported = p["actual_quantity_to_date"] > p["budget_quantity"]
            if overreported.any():
                examples = p.loc[overreported, ["activity_id", "boq_id", "actual_quantity_to_date", "budget_quantity"]].head(5)
                detail = "; ".join(
                    f"{row.activity_id}/{row.boq_id}: {row.actual_quantity_to_date} > {row.budget_quantity}"
                    for row in examples.itertuples(index=False)
                )
                raise ValueError("Reported cumulative quantity exceeds BOQ budget quantity for its activity allocation: " + detail)
            p["earned_value"]=p["budget_amount"]*p["wbs_share"]*(p["actual_quantity_to_date"]/p["budget_quantity"])
            ev=float(p["earned_value"].sum())
            ev_detail=p.groupby(["activity_id","wbs_id_activity"],as_index=False).agg(
                earned_value=("earned_value","sum"))
            ev_detail=ev_detail.rename(columns={"wbs_id_activity":"wbs_id"})
    ac=0.0
    if not actual.empty:
        if not {"transaction_date","amount"}.issubset(actual.columns):
            raise ValueError("Actual cost requires transaction_date and amount.")
        ac_frame=actual.copy()
        ac_frame["transaction_date"]=pd.to_datetime(ac_frame["transaction_date"],errors="coerce")
        ac_frame["amount"]=pd.to_numeric(ac_frame["amount"],errors="coerce")
        if ac_frame[["transaction_date","amount"]].isna().any().any():
            raise ValueError("Actual cost contains invalid transaction dates or amounts.")
        if (ac_frame["amount"]<0).any():
            raise ValueError("Actual cost amount cannot be negative.")
        ac=float(ac_frame.loc[ac_frame["transaction_date"]<=sd,"amount"].sum())
        if "currency" in ac_frame and not ac_frame.empty:
            currencies=set(ac_frame["currency"].dropna().astype(str).str.strip())-{"", "nan"}
            if len(currencies)>1:
                raise ValueError("Actual cost contains multiple currencies; convert to project currency before EVM.")
            if not project.empty and "currency" in project and currencies:
                project_currency=str(project.iloc[0]["currency"]).strip()
                if project_currency and next(iter(currencies))!=project_currency:
                    raise ValueError("Actual cost currency does not match project currency.")
    cpi=ev/ac if ac>0 else np.nan
    spi=ev/pv if pv>0 else np.nan
    eac=bac/cpi if pd.notna(cpi) and cpi>0 else np.nan
    etc=eac-ac if pd.notna(eac) else np.nan
    vac=bac-eac if pd.notna(eac) else np.nan
    tcpi=(bac-ev)/(bac-ac) if bac>ac else np.nan
    return {"BAC":bac,"PV":pv,"EV":ev,"AC":ac,"SV":ev-pv,"CV":ev-ac,
      "SPI":spi,"CPI":cpi,"EAC":eac,"ETC":etc,"VAC":vac,"TCPI":tcpi,
      "physical_progress_pct":ev/bac*100,"ev_detail":ev_detail}

def calculate_progress(activities, progress, boq=None):
    if activities.empty: raise ValueError("Activities belum diimpor.")
    if progress.empty:
        return pd.DataFrame(), {"weighted_progress_pct":0.0,"reported_activities":0,
          "total_activities":int(len(activities)),"unreported_activities":int(len(activities)),
          "status_date":None}
    required_progress={"period_end","activity_id","actual_quantity_to_date"}
    missing=required_progress-set(progress.columns)
    if missing:
        raise ValueError("Progress missing columns: "+", ".join(sorted(missing)))
    p=progress.copy()
    if activities["activity_id"].isna().any() or activities["activity_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Activities contain blank activity_id values.")
    if activities["activity_id"].astype(str).duplicated().any():
        raise ValueError("Activities contain duplicate activity_id values.")
    if p["activity_id"].isna().any() or p["activity_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Progress contains blank activity_id values.")
    unknown_activities=set(p["activity_id"].astype(str))-set(activities["activity_id"].astype(str))
    if unknown_activities:
        raise ValueError("Progress references unknown activities: "+", ".join(sorted(unknown_activities)))
    p["period_end"]=pd.to_datetime(p["period_end"],errors="coerce")
    if p["period_end"].isna().any():
        raise ValueError("Progress contains invalid period_end dates.")
    p["actual_quantity_to_date"]=pd.to_numeric(p["actual_quantity_to_date"],errors="coerce")
    if p["actual_quantity_to_date"].isna().any() or (p["actual_quantity_to_date"]<0).any():
        raise ValueError("actual_quantity_to_date must be valid and non-negative.")
    status_date=p["period_end"].max()
    keys=["activity_id","boq_id"] if "boq_id" in p else ["activity_id"]
    duplicate_reports=p.duplicated(["period_end"]+keys,keep=False)
    if duplicate_reports.any():
        raise ValueError("Progress contains duplicate rows for the same reporting period and activity/BOQ.")
    p=p.sort_values("period_end").drop_duplicates(keys,keep="last")
    reported=int(p["activity_id"].nunique())
    if boq is None or boq.empty:
        return p, {"weighted_progress_pct":None,"reported_activities":reported,
          "total_activities":int(len(activities)),"unreported_activities":max(0,len(activities)-reported),
          "status_date":status_date}
    evm=calculate_evm(pd.DataFrame(),activities,boq,p,pd.DataFrame(),status_date or date.today())
    p["report_status"]="Reported"
    return p, {"weighted_progress_pct":float(evm["physical_progress_pct"]),
      "reported_activities":reported,"total_activities":int(len(activities)),
      "unreported_activities":max(0,len(activities)-reported),"status_date":status_date}

def risk_analysis(risks: pd.DataFrame, iterations=10000, seed=42):
    """Independent Bernoulli Monte Carlo risk exposure; impacts are non-negative."""
    if risks.empty:
        raise ValueError("Risk register belum diimpor.")
    if not isinstance(iterations, (int, np.integer)) or iterations < 100:
        raise ValueError("iterations harus bilangan bulat minimal 100.")
    required = {"risk_id", "probability", "cost_impact", "schedule_impact_days"}
    missing = required - set(risks.columns)
    if missing:
        raise ValueError("Kolom risk register belum lengkap: " + ", ".join(sorted(missing)))
    r = risks.copy()
    if r["risk_id"].isna().any() or r["risk_id"].astype(str).str.strip().eq("").any():
        raise ValueError("risk_id tidak boleh kosong.")
    if r["risk_id"].astype(str).duplicated().any():
        raise ValueError("risk_id harus unik.")
    for col in ["probability", "cost_impact", "schedule_impact_days"]:
        r[col] = pd.to_numeric(r[col], errors="coerce")
        if r[col].isna().any() or not np.isfinite(r[col]).all():
            raise ValueError(f"{col} harus berisi angka valid.")
    if ((r["probability"] < 0) | (r["probability"] > 1)).any():
        raise ValueError("probability harus berada antara 0 dan 1.")
    for col in ["cost_impact", "schedule_impact_days"]:
        if (r[col] < 0).any():
            raise ValueError(f"{col} tidak boleh negatif.")
    r["cost_exposure"] = r["probability"] * r["cost_impact"]
    r["schedule_exposure_days"] = r["probability"] * r["schedule_impact_days"]
    rng = np.random.default_rng(seed)
    probabilities = r["probability"].to_numpy(dtype=float)
    cost_impacts = r["cost_impact"].to_numpy(dtype=float)
    day_impacts = r["schedule_impact_days"].to_numpy(dtype=float)
    # Bound temporary Bernoulli matrix memory for large risk registers / iteration counts.
    cost_samples = np.empty(iterations, dtype=float)
    day_samples = np.empty(iterations, dtype=float)
    rows_per_chunk = max(1, min(10000, 1_000_000 // max(1, len(r))))
    for offset in range(0, iterations, rows_per_chunk):
        stop = min(iterations, offset + rows_per_chunk)
        occur = rng.random((stop - offset, len(r))) < probabilities
        cost_samples[offset:stop] = occur @ cost_impacts
        day_samples[offset:stop] = occur @ day_impacts
    stats = {
        "expected_cost_exposure": float(r["cost_exposure"].sum()),
        "expected_schedule_exposure_days": float(r["schedule_exposure_days"].sum()),
        "cost_p50": float(np.percentile(cost_samples, 50)),
        "cost_p80": float(np.percentile(cost_samples, 80)),
        "cost_p90": float(np.percentile(cost_samples, 90)),
        "cost_p95": float(np.percentile(cost_samples, 95)),
        "delay_p50": float(np.percentile(day_samples, 50)),
        "delay_p80": float(np.percentile(day_samples, 80)),
        "delay_p90": float(np.percentile(day_samples, 90)),
        "delay_p95": float(np.percentile(day_samples, 95)),
        "iterations": int(iterations),
        "seed": int(seed),
    }
    samples = pd.DataFrame({"cost": cost_samples, "delay_days": day_samples})
    return r.sort_values("cost_exposure", ascending=False), stats, samples

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
    """Export datasets with safe, unique worksheet names and formula-injection guards."""
    import re
    output=BytesIO()
    used=set()
    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        for name,df in {**datasets,**analyses}.items():
            if not isinstance(df,pd.DataFrame) or df.empty:
                continue
            base=re.sub(r"[\[\]:*?/\\]", "_", str(name).replace(".csv","")).strip() or "Sheet"
            sheet=base[:31]
            suffix=1
            while sheet.casefold() in used:
                tail=f"_{suffix}"
                sheet=base[:31-len(tail)]+tail
                suffix+=1
            used.add(sheet.casefold())
            safe=df.copy()
            for col in safe.select_dtypes(include=["object","string"]).columns:
                safe[col]=safe[col].map(
                    lambda value: "'" + value if isinstance(value,str)
                    and value.lstrip(" \\t\\r\\n").startswith(("=","+","-","@"))
                    else value
                )
            safe.to_excel(writer,sheet_name=sheet,index=False)
    output.seek(0)
    return output.getvalue()


def calculate_xer_cpm(tables: dict[str,pd.DataFrame], hours_per_day=8):
    """Calendar-free XER CPM adapter retaining P6 FS/SS/FF/SF relationship types and lag."""
    task=tables.get("TASK",pd.DataFrame()).copy()
    rel=tables.get("TASKPRED",pd.DataFrame()).copy()
    if task.empty: raise ValueError("XER TASK table is empty.")
    if not np.isfinite(hours_per_day) or hours_per_day<=0:
        raise ValueError("hours_per_day must be a finite number greater than zero.")
    if "task_id" not in task:
        raise ValueError("XER TASK table is missing task_id.")
    if task["task_id"].isna().any() or task["task_id"].astype(str).str.strip().eq("").any() or task["task_id"].astype(str).str.strip().duplicated().any():
        raise ValueError("XER TASK contains a blank task_id.")
    ids=task["task_id"].astype(str).tolist()
    if len(set(ids)) != len(ids):
        raise ValueError("XER TASK contains duplicate task_id values.")
    index={v:i for i,v in enumerate(ids)}
    duration={}
    for _,r in task.iterrows():
        raw_duration=r.get("target_drtn_hr_cnt",0)
        value=pd.to_numeric(raw_duration,errors="coerce")
        if pd.isna(value) or not np.isfinite(float(value)) or float(value)<0:
            raise ValueError(f"Invalid target duration for P6 task {r['task_id']!r}.")
        duration[str(r["task_id"])]=float(value)/hours_per_day
    preds={i:[] for i in ids}; succs={i:[] for i in ids}
    if not rel.empty:
        supported_types={"PR_FS","PR_SS","PR_FF","PR_SF"}
        for row_no,r in rel.iterrows():
            s=str(r.get("task_id","")).strip(); p=str(r.get("pred_task_id","")).strip()
            if s not in index or p not in index:
                raise ValueError(
                    f"XER relationship row {row_no} references an unknown activity "
                    f"(successor={s!r}, predecessor={p!r}); import the complete TASK table."
                )
            typ=str(r.get("pred_type","PR_FS") or "PR_FS").strip()
            if typ not in supported_types:
                raise ValueError(f"Unsupported P6 relationship type {typ!r} at XER relationship row {row_no}.")
            lag=pd.to_numeric(r.get("lag_hr_cnt",0),errors="coerce")
            if pd.isna(lag) or not np.isfinite(float(lag)):
                raise ValueError(f"Invalid relationship lag at XER relationship row {row_no}.")
            lag=float(lag)/hours_per_day
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
    if not np.isfinite(hours_per_day) or hours_per_day <= 0:
        raise ValueError("hours_per_day must be a finite number greater than zero.")
    if "task_id" not in task:
        raise ValueError("XER TASK table is missing task_id.")
    task_ids=task["task_id"].astype(str).str.strip()
    if task["task_id"].isna().any() or task_ids.eq("").any() or task_ids.duplicated().any():
        raise ValueError("XER TASK contains blank or duplicate task_id values.")
    if not rel.empty:
        required_rel={"task_id","pred_task_id"}
        missing_rel=required_rel-set(rel.columns)
        if missing_rel:
            raise ValueError("XER TASKPRED missing columns: "+", ".join(sorted(missing_rel)))
        known=set(task_ids)
        for row_no,r in rel.iterrows():
            successor=str(r["task_id"]).strip(); predecessor=str(r["pred_task_id"]).strip()
            if successor not in known or predecessor not in known:
                raise ValueError(f"XER relationship row {row_no} references an unknown activity.")
            lag=pd.to_numeric(r.get("lag_hr_cnt",0),errors="coerce")
            if pd.isna(lag) or not np.isfinite(float(lag)):
                raise ValueError(f"Invalid relationship lag at XER relationship row {row_no}.")
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
    # A single-activity schedule is simultaneously its own start and finish;
    # it must not be penalized as an open-end logic defect.
    if len(incomplete) == 1 and len(task_ids) == 1:
        missing_logic = []
    else:
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
    """Three-point schedule-risk analysis; optimistic=0.90x and pessimistic=1.25x are explicit screening assumptions."""
    if activities.empty: raise ValueError("Activities belum diimpor.")
    if not isinstance(iterations, (int, np.integer)) or iterations < 100:
        raise ValueError("iterations harus bilangan bulat minimal 100.")
    required={"activity_id","duration_days"}
    missing=required-set(activities.columns)
    if missing: raise ValueError("Kolom aktivitas PERT belum lengkap: "+", ".join(sorted(missing)))
    ids=activities["activity_id"].astype(str).str.strip()
    if ids.eq("").any() or ids.duplicated().any():
        raise ValueError("activity_id untuk PERT harus terisi dan unik.")
    durations=pd.to_numeric(activities["duration_days"],errors="coerce")
    if durations.isna().any() or not np.isfinite(durations).all() or (durations<0).any():
        raise ValueError("duration_days PERT harus angka finite dan tidak negatif.")
    rows=[]
    for (_,r),d in zip(activities.iterrows(),durations):
        pred=r.get("predecessor_ids","")
        pred="" if pd.isna(pred) else str(pred)
        rows.append({"id":str(r["activity_id"]).strip(),"predecessors":pred,
          "a":float(d)*0.90,"m":float(d),"b":float(d)*1.25})
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
        assignment_frame=records(assignments,["task_id","rsrc_id","target_qty","act_reg_qty","target_cost","act_reg_cost","act_ot_cost","target_start_date","target_end_date"])
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


def generate_pdf_report(project_code, project_name, status_date, datasets, analyses, metrics=None):
    """Build a compact landscape PDF management pack in memory."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from xml.sax.saxutils import escape
    output=BytesIO()
    doc=SimpleDocTemplate(output,pagesize=landscape(A4),rightMargin=12*mm,leftMargin=12*mm,
      topMargin=12*mm,bottomMargin=12*mm,title=f"{escape(str(project_code))} Project Controls Report")
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle",parent=styles["Title"],alignment=TA_CENTER,fontSize=18))
    story=[Paragraph("AI PROJECT CONTROL SYSTEM",styles["ReportTitle"]),
      Paragraph(f"{escape(str(project_name))} | Project: {escape(str(project_code))} | Status date: {escape(str(status_date))}",styles["Heading2"]),
      Spacer(1,8)]
    metrics=metrics or {}
    if metrics:
        story.append(Paragraph("Executive KPIs",styles["Heading2"]))
        rows=[["Indicator","Value"]]+[[str(k),str(v)] for k,v in metrics.items()]
        table=Table(rows,repeatRows=1,hAlign="LEFT",colWidths=[65*mm,65*mm])
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#26384A")),
          ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.35,colors.grey),
          ("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
          ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#EEF2F6")])]))
        story.extend([table,Spacer(1,10)])
    for section,collection in [("Analysis Results",analyses),("Project Data Snapshot",datasets)]:
        for name,frame in collection.items():
            if not isinstance(frame,pd.DataFrame) or frame.empty: continue
            story.append(Paragraph(escape(f"{section}: {name}"),styles["Heading3"]))
            view=frame.head(25).copy().fillna("")
            data=[[str(c) for c in view.columns]]
            for _,row in view.iterrows():
                data.append([str(x)[:80] for x in row.tolist()])
            table=Table(data,repeatRows=1,hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#34495E")),
              ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.grey),
              ("FONTSIZE",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"TOP"),
              ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4F6F8")])]))
            story.extend([table,Spacer(1,8)])
    story.append(Spacer(1,8))
    story.append(Paragraph("Engineering note: results depend on source data quality and stated model assumptions. Primavera P6 remains authoritative for native calendars, constraints and resource levelling.",styles["Italic"]))
    doc.build(story)
    output.seek(0)
    return output.getvalue()

def send_telegram_document(bot_token, chat_id, file_bytes, filename, caption="AI Project Control Report"):
    """Send a report to Telegram only when explicitly requested by the user."""
    import requests
    response=requests.post(
      f"https://api.telegram.org/bot{bot_token}/sendDocument",
      data={"chat_id":chat_id,"caption":caption},
      files={"document":(filename,file_bytes,"application/pdf")},
      timeout=120)
    response.raise_for_status()
    payload=response.json()
    if not payload.get("ok"): raise RuntimeError(payload.get("description","Telegram API rejected the document"))
    return payload


def predict_project_trend(project, activities, boq, progress, actual_cost):
    """Time-series project forecast from approved progress periods; returns None until 3 periods exist."""
    if progress.empty or "period_end" not in progress: return None,pd.DataFrame()
    periods=sorted(pd.to_datetime(progress["period_end"],errors="coerce").dropna().unique())
    if len(periods)<3: return None,pd.DataFrame()
    rows=[]
    for period in periods:
        values=calculate_evm(project,activities,boq,progress,actual_cost,pd.Timestamp(period))
        rows.append({"period_end":pd.Timestamp(period),"PV":values["PV"],"EV":values["EV"],
          "AC":values["AC"],"SPI":values["SPI"],"CPI":values["CPI"],
          "earned_pct":values["physical_progress_pct"]})
    history=pd.DataFrame(rows).sort_values("period_end").reset_index(drop=True)
    valid=history.dropna(subset=["earned_pct"])
    if len(valid)<3: return None,history
    bac=float(pd.to_numeric(boq.get("budget_amount",pd.Series(dtype=float)),errors="coerce").fillna(0).sum())
    if bac<=0: return None,history
    x=(valid["period_end"]-valid["period_end"].min()).dt.days.to_numpy(dtype=float)
    y=(valid["EV"]/bac).to_numpy(dtype=float)
    if len(set(x))<2: return None,history
    slope,intercept=np.polyfit(x,y,1)
    latest=valid.iloc[-1]
    finish_forecast=None
    if slope>0 and latest["EV"]<bac:
        remaining=max(0.0,(1.0-float(latest["EV"]/bac))/slope)
        finish_forecast=latest["period_end"]+pd.Timedelta(days=remaining)
    eac=bac/float(latest["CPI"]) if pd.notna(latest["CPI"]) and latest["CPI"]>0 else np.nan
    result={"reporting_periods":len(valid),"BAC":bac,"latest_EV":float(latest["EV"]),
      "latest_AC":float(latest["AC"]),"latest_SPI":float(latest["SPI"]) if pd.notna(latest["SPI"]) else np.nan,
      "latest_CPI":float(latest["CPI"]) if pd.notna(latest["CPI"]) else np.nan,
      "trend_slope_pct_per_day":float(slope*100),"trend_finish_forecast":finish_forecast,
      "trend_EAC":float(eac) if pd.notna(eac) else np.nan,
      "method":"Linear trend on cumulative earned-value progress; minimum 3 reporting periods"}
    return result,MAX_DRAWING_PDF_BYTES = 50 * 1024 * 1024
MAX_DRAWING_PDF_PAGES = 500
MAX_DRAWING_IMAGE_BYTES = 12 * 1024 * 1024
MAX_DRAWING_TAKEOFF_ITEMS = 500
MAX_GEMINI_RESPONSE_CHARS = 1_000_000


def render_pdf_page(raw: bytes, page_number: int, zoom=1.5):
    """Render one bounded PDF page without retaining the document handle."""
    import fitz

    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise ValueError("PDF upload is empty or invalid.")
    if len(raw) > MAX_DRAWING_PDF_BYTES:
        raise ValueError("PDF upload exceeds the 50 MB drawing limit.")
    if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 0:
        raise ValueError("PDF page number must be a non-negative integer.")
    if isinstance(zoom, bool) or not isinstance(zoom, (int, float)) or not np.isfinite(float(zoom)) or not 0.25 <= float(zoom) <= 4.0:
        raise ValueError("PDF render zoom must be between 0.25 and 4.0.")
    doc = fitz.open(stream=bytes(raw), filetype="pdf")
    try:
        page_count = len(doc)
        if page_count < 1 or page_count > MAX_DRAWING_PDF_PAGES:
            raise ValueError("PDF must contain between 1 and 500 pages.")
        if page_number >= page_count:
            raise ValueError("PDF page number is out of range.")
        page = doc.load_page(page_number)
        pix = page.get_pixmap(matrix=fitz.Matrix(float(zoom), float(zoom)), alpha=False)
        image_bytes = pix.tobytes("png")
        if len(image_bytes) > MAX_DRAWING_IMAGE_BYTES:
            raise ValueError("Rendered drawing page exceeds the 12 MB image limit.")
        return image_bytes, page.get_text("text"), page_count
    finally:
        doc.close()


def analyze_drawing_page_gemini(image_bytes: bytes, api_key: str, model='gemini-2.5-flash'):
    """Return bounded, untrusted Gemini takeoff rows for mandatory human review."""
    import base64
    import requests

    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        raise ValueError("Drawing page image is empty.")
    if len(image_bytes) > MAX_DRAWING_IMAGE_BYTES:
        raise ValueError("Drawing page image exceeds the 12 MB limit.")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("Gemini API key is required.")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", model.strip()):
        raise ValueError("Gemini model name contains unsupported characters.")
    prompt=('You are a construction quantity surveyor. Inspect this engineering drawing page and extract only items whose dimensions, counts, schedules or quantities are explicitly visible. Do not invent dimensions, scale, thickness, lengths or quantities. If a required dimension is missing, set quantity to null and explain what must be measured. Return ONLY valid JSON: an array of objects with keys discipline,item_code,description,unit,quantity,measurement_method,confidence,assumptions. Use SI units where supported. Confidence must be High, Medium or Low. Every quantity is a draft and must be checked by a human quantity surveyor.')
    try:
        response=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model.strip()}:generateContent',
          headers={'x-goog-api-key':api_key.strip()},
          json={'contents':[{'parts':[{'text':prompt},{'inline_data':{'mime_type':'image/png','data':base64.b64encode(bytes(image_bytes)).decode('ascii')}}]}],
          'generationConfig':{'temperature':0.1,'responseMimeType':'application/json'}},timeout=120)
        response.raise_for_status()
        payload=response.json()
        raw_text=payload['candidates'][0]['content']['parts'][0]['text']
        if not isinstance(raw_text,str) or len(raw_text)>MAX_GEMINI_RESPONSE_CHARS:
            raise ValueError("Gemini drawing response exceeds the supported output limit.")
        text=raw_text.strip()
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        raise RuntimeError("Gemini drawing analysis failed; check API configuration and provider response.") from None
    if text.startswith(chr(96)*3):
        text='\n'.join(text.splitlines()[1:-1])
    try:
        data=json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("Gemini returned unreadable drawing-analysis JSON.") from None
    if not isinstance(data,list):
        raise ValueError("Gemini response was not a JSON array.")
    if len(data)>MAX_DRAWING_TAKEOFF_ITEMS:
        raise ValueError(f"Gemini response exceeds the {MAX_DRAWING_TAKEOFF_ITEMS} item review limit.")
    rows=[]
    for i,item in enumerate(data,1):
        if not isinstance(item,dict):
            continue
        raw_quantity=item.get('quantity')
        quantity=None
        if raw_quantity not in (None,'') and not isinstance(raw_quantity,bool):
            try:
                parsed=float(raw_quantity)
                if np.isfinite(parsed) and parsed>=0:
                    quantity=parsed
            except (TypeError,ValueError):
                pass
        confidence=str(item.get('confidence','Low')).title()
        if confidence not in {'High','Medium','Low'}:
            confidence='Low'
        rows.append({'drawing_id':'DWG-UPLOAD','page':None,'wbs_id':'','discipline':str(item.get('discipline','')),
          'item_code':str(item.get('item_code') or f'TAKEOFF-{i:03d}'),'description':str(item.get('description','')),
          'unit':str(item.get('unit','')),'quantity':quantity,
          'measurement_method':str(item.get('measurement_method','')),'confidence':confidence,
          'assumptions':str(item.get('assumptions','')),'review_status':'Pending Review'})
    return pd.DataFrame(rows)


me(rows)

def takeoff_to_boq_draft(takeoff: pd.DataFrame):
    """Convert reviewed takeoff rows to a non-priced, explicitly provisional BOQ."""
    if not isinstance(takeoff, pd.DataFrame):
        raise TypeError("Takeoff must be a pandas DataFrame.")
    if takeoff.empty:
        return pd.DataFrame()
    if len(takeoff) > MAX_DRAWING_TAKEOFF_ITEMS:
        raise ValueError(f"Takeoff exceeds the {MAX_DRAWING_TAKEOFF_ITEMS} item review limit.")
    rows=[]
    for i,(_,r) in enumerate(takeoff.iterrows(),1):
        wbs_value=r.get('wbs_id','')
        wbs_id='' if pd.isna(wbs_value) else str(wbs_value).strip()
        raw_quantity=r.get('quantity')
        quantity=None
        missing_quantity = raw_quantity is None or (
            isinstance(raw_quantity, str) and not raw_quantity.strip()
        )
        if not missing_quantity:
            try:
                missing_quantity = bool(pd.isna(raw_quantity))
            except (TypeError, ValueError):
                missing_quantity = False
        if not missing_quantity:
            if isinstance(raw_quantity, (bool, np.bool_)):
                raise ValueError(f"Takeoff row {i} quantity must be numeric, not boolean.")
            try:
                quantity=float(raw_quantity)
            except (TypeError,ValueError):
                raise ValueError(f"Takeoff row {i} has a non-numeric quantity.") from None
            if not np.isfinite(quantity) or quantity < 0:
                raise ValueError(f"Takeoff row {i} quantity must be finite and non-negative.")
        rows.append({'boq_id':f'BOQ-DRAFT-{i:03d}','wbs_id':wbs_id,'item_code':str(r.get('item_code','') or '').strip(),
          'description':str(r.get('description','') or '').strip(),'unit':str(r.get('unit','') or '').strip(),
          'budget_quantity':quantity,'unit_rate':'','budget_amount':'','review_status':'Pending Review'})
    return pd.DataFrame(rows)


def calculate_milestones(milestones: pd.DataFrame, status_date):
    if milestones.empty:
        return pd.DataFrame(), {"total":0,"completed":0,"delayed":0,"at_risk":0}
    df=milestones.copy()
    for col in ["planned_date","forecast_date","actual_date"]:
        if col not in df: df[col]=pd.NaT
        df[col]=pd.to_datetime(df[col],errors="coerce")
    sd=pd.Timestamp(status_date)
    actual=df["actual_date"].notna()
    forecast=df["forecast_date"].fillna(df["planned_date"])
    df["slippage_days"]=np.where(actual,
        (df["actual_date"]-df["planned_date"]).dt.days,
        (forecast-df["planned_date"]).dt.days)
    status=df.get("status",pd.Series("",index=df.index)).fillna("").astype(str).str.lower()
    df["calculated_status"]=np.where(actual,"Completed",
        np.where(forecast.isna(),"Date Missing",
          np.where(forecast<sd,"Overdue",
            np.where((forecast-df["planned_date"]).dt.days>0,"At Risk","On Track"))))
    completed=int(actual.sum())
    delayed=int((pd.to_numeric(df["slippage_days"],errors="coerce")>0).sum())
    at_risk=int(df["calculated_status"].isin(["At Risk","Overdue"]).sum())
    return df,{"total":len(df),"completed":completed,"delayed":delayed,"at_risk":at_risk}

def calculate_change_impact(changes: pd.DataFrame, original_bac: float):
    if changes.empty:
        return pd.DataFrame(),{"approved_cost_impact":0.0,"approved_schedule_days":0.0,
          "revised_budget":float(original_bac),"pending_count":0,"pending_cost_exposure":0.0}
    df=changes.copy()
    df["cost_impact"]=pd.to_numeric(df["cost_impact"],errors="coerce").fillna(0)
    df["schedule_impact_days"]=pd.to_numeric(df["schedule_impact_days"],errors="coerce").fillna(0)
    status=df["status"].fillna("").astype(str).str.strip().str.lower()
    approved=status.isin(["approved","accepted"])
    pending=status.isin(["pending","submitted","under review","under_review"])
    stats={"approved_cost_impact":float(df.loc[approved,"cost_impact"].sum()),
      "approved_schedule_days":float(df.loc[approved,"schedule_impact_days"].sum()),
      "revised_budget":float(original_bac)+float(df.loc[approved,"cost_impact"].sum()),
      "pending_count":int(pending.sum()),
      "pending_cost_exposure":float(df.loc[pending,"cost_impact"].sum())}
    df["control_class"]=np.where(approved,"Approved baseline change",
        np.where(pending,"Pending decision","Other / rejected"))
    return df,stats

def calculate_resource_load(resources: pd.DataFrame, assignments: pd.DataFrame):
    """Build resource summary and calendar-day demand with capacity screening.

    target_qty is spread evenly over the inclusive assignment window. This is
    a transparent planning approximation, not Primavera resource leveling.
    """
    if assignments.empty:
        return pd.DataFrame(), pd.DataFrame()
    a = assignments.copy()
    if "rsrc_id" not in a or a["rsrc_id"].isna().any() or a["rsrc_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Every resource assignment must have a non-blank rsrc_id.")
    a["rsrc_id"] = a["rsrc_id"].astype(str).str.strip()
    for col in ["target_qty", "actual_qty", "target_cost", "actual_cost"]:
        if col not in a:
            a[col] = 0.0
        a[col] = pd.to_numeric(a[col], errors="coerce")
        if a[col].isna().any() or not np.isfinite(a[col].to_numpy(dtype=float)).all() or (a[col] < 0).any():
            raise ValueError(f"{col} must contain finite non-negative numbers.")
    if resources.empty:
        summary = a.groupby("rsrc_id", dropna=False).agg(
            target_qty=("target_qty", "sum"), actual_qty=("actual_qty", "sum"),
            target_cost=("target_cost", "sum"), actual_cost=("actual_cost", "sum")
        ).reset_index()
        return summary, pd.DataFrame()

    r = resources.copy()
    if "rsrc_id" not in r or r["rsrc_id"].isna().any() or r["rsrc_id"].astype(str).str.strip().eq("").any() or r["rsrc_id"].astype(str).str.strip().duplicated().any():
        raise ValueError("resources.csv must contain unique non-blank rsrc_id values.")
    r["rsrc_id"] = r["rsrc_id"].astype(str).str.strip()
    unknown = set(a["rsrc_id"]) - set(r["rsrc_id"])
    if unknown:
        raise ValueError("Assignments reference unknown resources: " + ", ".join(sorted(unknown)))
    summary = a.groupby("rsrc_id", dropna=False).agg(
        target_qty=("target_qty", "sum"), actual_qty=("actual_qty", "sum"),
        target_cost=("target_cost", "sum"), actual_cost=("actual_cost", "sum")
    ).reset_index().merge(r, on="rsrc_id", how="left")

    if not {"target_start_date", "target_end_date"}.issubset(a.columns):
        return summary, pd.DataFrame()
    daily = []
    for _, row in a.iterrows():
        start = pd.to_datetime(row["target_start_date"], errors="coerce")
        finish = pd.to_datetime(row["target_end_date"], errors="coerce")
        if pd.isna(start) or pd.isna(finish):
            raise ValueError(f"Invalid assignment date range for resource {row['rsrc_id']}.")
        start_day, finish_day = start.normalize(), finish.normalize()
        if finish_day < start_day:
            raise ValueError(f"Invalid assignment date range for resource {row['rsrc_id']}.")
        if (finish_day - start_day).days > 3660:
            raise ValueError(f"Resource assignment window exceeds 10 years for resource {row['rsrc_id']}.")
        days = pd.date_range(start_day, finish_day, freq="D")
        per_day = float(row["target_qty"]) / len(days)
        for day in days:
            daily.append({"date": day, "rsrc_id": row["rsrc_id"],
                          "planned_load_per_day": per_day})
    load = pd.DataFrame(daily).groupby(
        ["date", "rsrc_id"], as_index=False
    )["planned_load_per_day"].sum()
    caps = r[["rsrc_id"]].copy()
    if "capacity_per_day" in r:
        raw_capacity = r["capacity_per_day"]
        caps["capacity_per_day"] = pd.to_numeric(raw_capacity, errors="coerce")
        invalid_text = raw_capacity.notna() & raw_capacity.astype(str).str.strip().ne("") & caps["capacity_per_day"].isna()
        invalid_capacity = invalid_text | (caps["capacity_per_day"].notna() & (~np.isfinite(caps["capacity_per_day"].fillna(0)) | (caps["capacity_per_day"] <= 0)))
        if invalid_capacity.any():
            raise ValueError("capacity_per_day must be finite and greater than zero when provided.")
    else:
        caps["capacity_per_day"] = np.nan
    load = load.merge(caps, on="rsrc_id", how="left")
    load["capacity_utilization_pct"] = np.where(
        load["capacity_per_day"].notna(),
        load["planned_load_per_day"] / load["capacity_per_day"] * 100,
        np.nan
    )
    load["over_capacity"] = (
        load["capacity_per_day"].notna()
        & (load["planned_load_per_day"] > load["capacity_per_day"] + 1e-9)
    )
    utilization = load.groupby("rsrc_id").agg(
        peak_daily_load=("planned_load_per_day", "max"),
        peak_capacity_utilization_pct=("capacity_utilization_pct", "max"),
        overloaded_days=("over_capacity", "sum")
    ).reset_index()
    summary = summary.merge(utilization, on="rsrc_id", how="left")
    return summary, load

def export_project_backup(project_id: str):
    import zipfile
    output=BytesIO()
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        manifest={"format":"AIProjectControlBackup","version":1,"project_id":project_id,
          "datasets":list_datasets(project_id)}
        archive.writestr("manifest.json",json.dumps(manifest,indent=2))
        for name in manifest["datasets"]:
            frame=load_dataset(project_id,name)
            archive.writestr(f"datasets/{name}",frame.to_csv(index=False))
    output.seek(0)
    return output.getvalue()

def import_project_backup(project_id: str, raw: bytes):
    """Validate a complete backup before writing; restore all datasets atomically."""
    import zipfile
    if not raw or len(raw) > 100 * 1024 * 1024:
        raise ValueError("Backup ZIP is empty or exceeds the 100 MB safety limit.")
    try:
        archive_file=BytesIO(raw)
        with zipfile.ZipFile(archive_file) as archive:
            infos=archive.infolist()
            if len(infos)>len(TEMPLATES)+1:
                raise ValueError("Backup contains too many archive entries.")
            if any(info.is_dir() for info in infos):
                raise ValueError("Backup must not contain directory entries.")
            names=[info.filename for info in infos]
            if len(names)!=len(set(names)):
                raise ValueError("Backup contains duplicate ZIP entries.")
            if sum(info.file_size for info in infos)>100*1024*1024:
                raise ValueError("Backup expands beyond the 100 MB total safety limit.")
            if any(info.file_size > 25 * 1024 * 1024 for info in infos):
                raise ValueError("A backup dataset exceeds the 25 MB per-file safety limit.")
            if "manifest.json" not in names:
                raise ValueError("Backup manifest not found.")
            manifest_info=next(info for info in infos if info.filename=="manifest.json")
            if manifest_info.file_size>1024*1024:
                raise ValueError("Backup manifest exceeds the 1 MB safety limit.")
            manifest=json.loads(archive.read("manifest.json"))
            if not isinstance(manifest,dict):
                raise ValueError("Backup manifest must be a JSON object.")
            if manifest.get("format")!="AIProjectControlBackup" or manifest.get("version")!=1:
                raise ValueError("Unsupported backup format or version.")
            listed=manifest.get("datasets")
            if (not isinstance(listed,list) or len(listed)>len(TEMPLATES)
                    or any(not isinstance(name,str) for name in listed)
                    or len(set(listed))!=len(listed)):
                raise ValueError("Backup dataset manifest is invalid.")
            for name in listed:
                if name not in TEMPLATES:
                    raise ValueError(f"Unsupported dataset in backup: {name!r}.")
            expected_names={"manifest.json"}|{f"datasets/{name}" for name in listed}
            if set(names)!=expected_names:
                raise ValueError("Backup contains missing or unexpected archive entries.")
            restored_frames={}
            for name in listed:
                member=f"datasets/{name}"
                if member not in names:
                    raise ValueError(f"Backup is missing {member}.")
                frame=pd.read_csv(BytesIO(archive.read(member)))
                # A restore may target a new project ID. Keep the master record
                # aligned with the project-scoped database key used below.
                if name=="project_master.csv" and "project_id" in frame.columns:
                    frame["project_id"]=str(project_id)
                restored_frames[name]=frame
    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError, TypeError, UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise ValueError(f"Backup archive is invalid: {exc}") from exc

    existing={name:load_dataset(project_id,name) for name in TEMPLATES}
    candidate={**existing,**restored_frames}
    # Validate against the complete incoming snapshot, not a partially restored DB.
    for name,frame in restored_frames.items():
        issues=validate_dataset(name,frame,candidate)
        if issues:
            raise ValueError(f"{name}: "+"; ".join(issues))

    init_db()
    with sqlite3.connect(DB_PATH) as con:
        con.execute("BEGIN IMMEDIATE")
        for name,frame in restored_frames.items():
            payload=frame.to_json(orient="records",date_format="iso")
            con.execute("""INSERT INTO datasets(project_id,dataset_name,payload,updated_at)
              VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(project_id,dataset_name)
              DO UPDATE SET payload=excluded.payload,updated_at=CURRENT_TIMESTAMP""",
              (project_id,name,payload))
    return list(restored_frames)


def _calendar_definition(calendar_id: str, calendars: pd.DataFrame | None = None):
    """Return a deterministic weekly work pattern and holiday set.

    workdays_per_week maps to Monday-first schedules: 5=Mon-Fri,
    6=Mon-Sat, 7=Mon-Sun. Custom weekday masks and shift calendars
    are intentionally not inferred from this simplified CSV schema.
    """
    days = 5
    holidays: set[date] = set()
    hours_per_day = 8.0
    if calendars is not None and not calendars.empty:
        if "calendar_id" not in calendars.columns:
            raise ValueError("calendars dataset requires calendar_id.")
        matches = calendars[calendars["calendar_id"].astype(str) == str(calendar_id)]
        if matches.empty:
            raise ValueError(f"Calendar {calendar_id!r} was not found.")
        if len(matches) > 1:
            raise ValueError(f"Calendar {calendar_id!r} is duplicated.")
        row = matches.iloc[0]
        raw_days = pd.to_numeric(row.get("workdays_per_week", 5), errors="coerce")
        raw_hours = pd.to_numeric(row.get("hours_per_day", 8), errors="coerce")
        if pd.isna(raw_days) or int(raw_days) not in (5, 6, 7):
            raise ValueError("workdays_per_week must be 5, 6 or 7.")
        if pd.isna(raw_hours) or float(raw_hours) <= 0:
            raise ValueError("hours_per_day must be greater than zero.")
        days, hours_per_day = int(raw_days), float(raw_hours)
        raw_holidays = str(row.get("holidays", "") or "").strip()
        for token in raw_holidays.replace(";", ",").split(","):
            token = token.strip()
            if token:
                parsed = pd.to_datetime(token, errors="coerce")
                if pd.isna(parsed):
                    raise ValueError(f"Invalid holiday date {token!r} in calendar {calendar_id!r}.")
                holidays.add(parsed.date())
    return set(range(days)), holidays, hours_per_day


def is_working_day(value, calendar_id: str, calendars: pd.DataFrame | None = None) -> bool:
    """Check a date against a simple Monday-first 5/6/7-day calendar."""
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        raise ValueError(f"Invalid date {value!r}.")
    weekdays, holidays, _ = _calendar_definition(calendar_id, calendars)
    day = dt.date()
    return day.weekday() in weekdays and day not in holidays


def add_working_days(start_date, duration_days, calendar_id: str,
                     calendars: pd.DataFrame | None = None):
    """Return inclusive finish date; a one-day task finishes on its start date."""
    start = pd.to_datetime(start_date, errors="coerce")
    duration = pd.to_numeric(duration_days, errors="coerce")
    if pd.isna(start):
        raise ValueError(f"Invalid start date {start_date!r}.")
    if pd.isna(duration) or float(duration) < 0 or not float(duration).is_integer():
        raise ValueError("duration_days must be a non-negative whole number.")
    weekdays, holidays, _ = _calendar_definition(calendar_id, calendars)
    current = start.date()
    remaining = int(duration)
    if remaining == 0:
        return current.isoformat()
    while current.weekday() not in weekdays or current in holidays:
        current += pd.Timedelta(days=1).to_pytimedelta()
    while remaining > 1:
        current += pd.Timedelta(days=1).to_pytimedelta()
        if current.weekday() in weekdays and current not in holidays:
            remaining -= 1
    return current.isoformat()


def calculate_calendar_schedule(activities: pd.DataFrame,
                                calendars: pd.DataFrame) -> pd.DataFrame:
    """Calculate inclusive planned finish dates from start, duration and calendar.

    This helper validates date arithmetic only. It does not perform CPM,
    relationship constraints, shifts, exceptions, or native Primavera calendar logic.
    """
    required = {"activity_id", "duration_days", "planned_start", "calendar_id"}
    missing = required - set(activities.columns)
    if missing:
        raise ValueError("Activities missing columns: " + ", ".join(sorted(missing)))
    if activities["activity_id"].astype(str).duplicated().any():
        raise ValueError("Duplicate activity_id values.")
    rows = []
    for _, row in activities.iterrows():
        cal_id = str(row["calendar_id"])
        _, _, hours = _calendar_definition(cal_id, calendars)
        finish = add_working_days(row["planned_start"], row["duration_days"], cal_id, calendars)
        rows.append({
            "activity_id": str(row["activity_id"]),
            "calendar_id": cal_id,
            "planned_start": pd.to_datetime(row["planned_start"]).date().isoformat(),
            "planned_finish_calculated": finish,
            "duration_days": int(row["duration_days"]),
            "hours_per_day": hours,
        })
    return pd.DataFrame(rows)


def analyze_commitments(commitments: pd.DataFrame, status_date, project_currency=None):
    """Reconcile approved/active purchase commitments without double-counting paid cost.

    Paid amounts are shown as a reconciliation field only; they are not added to
    actual cost. Outstanding commitment is committed_amount minus paid_amount.
    """
    if commitments.empty:
        empty=pd.DataFrame(columns=["commitment_id","committed_amount","paid_amount","outstanding_amount","status"])
        return empty,{"commitment_count":0,"committed_total":0.0,"paid_total":0.0,
          "outstanding_total":0.0,"overpaid_count":0,"currency":project_currency}
    required={"commitment_id","committed_amount","paid_amount","currency","status"}
    missing=required-set(commitments.columns)
    if missing:
        raise ValueError("Commitments missing columns: "+", ".join(sorted(missing)))
    df=commitments.copy()
    if df["commitment_id"].astype(str).duplicated().any():
        raise ValueError("Duplicate commitment_id values.")
    for col in ["committed_amount","paid_amount"]:
        df[col]=pd.to_numeric(df[col],errors="coerce")
        if df[col].isna().any() or (df[col]<0).any():
            raise ValueError(f"{col} must contain valid non-negative amounts.")
    if (df["paid_amount"]>df["committed_amount"]).any():
        raise ValueError("paid_amount cannot exceed committed_amount.")
    if "commitment_date" in df:
        df["commitment_date"]=pd.to_datetime(df["commitment_date"],errors="coerce")
        if df["commitment_date"].isna().any():
            raise ValueError("Commitment date contains invalid values.")
        sd=pd.to_datetime(status_date,errors="coerce")
        if pd.isna(sd): raise ValueError("Status date is invalid.")
        df=df[df["commitment_date"]<=sd].copy()
    currencies=set(df["currency"].dropna().astype(str).str.strip())-{"","nan"}
    if len(currencies)>1:
        raise ValueError("Commitments contain multiple currencies.")
    currency=next(iter(currencies)) if currencies else project_currency
    if project_currency and currency and str(project_currency).strip()!=currency:
        raise ValueError("Commitment currency does not match project currency.")
    status=df["status"].fillna("").astype(str).str.strip().str.lower()
    included=~status.isin(["cancelled","canceled","rejected","void"])
    df=df.loc[included].copy()
    df["outstanding_amount"]=df["committed_amount"]-df["paid_amount"]
    stats={"commitment_count":int(len(df)),
      "committed_total":float(df["committed_amount"].sum()),
      "paid_total":float(df["paid_amount"].sum()),
      "outstanding_total":float(df["outstanding_amount"].sum()),
      "overpaid_count":0,"currency":currency}
    return df.sort_values("outstanding_amount",ascending=False),stats


def build_cost_cashflow(project: pd.DataFrame, activities: pd.DataFrame,
                        boq: pd.DataFrame, actual: pd.DataFrame,
                        commitments: pd.DataFrame, status_date, progress: pd.DataFrame | None = None):
    """Build monthly baseline, actual and remaining EAC cash-cost profile.

    Baseline BOQ value is allocated to activities by WBS weight_pct and spread
    uniformly across each activity's inclusive planned dates. Remaining EAC
    (BAC/CPI less actual cost) is spread evenly over future project months.
    Commitment outstanding is reported separately and is never added to AC/EAC.
    """
    if project.empty or not {"planned_start","planned_finish"}.issubset(project.columns):
        raise ValueError("Project master needs planned_start and planned_finish.")
    if activities.empty or boq.empty:
        raise ValueError("Activities and BOQ are required for cost cash flow.")
    sd=pd.to_datetime(status_date,errors="coerce")
    ps=pd.to_datetime(project.iloc[0]["planned_start"],errors="coerce")
    pf=pd.to_datetime(project.iloc[0]["planned_finish"],errors="coerce")
    if pd.isna(sd) or pd.isna(ps) or pd.isna(pf) or pf<ps:
        raise ValueError("Project dates or status date are invalid.")
    a=activities.copy()
    b=boq.copy()
    for col in ["planned_start","planned_finish"]:
        a[col]=pd.to_datetime(a[col],errors="coerce")
    a["weight_pct"]=pd.to_numeric(a["weight_pct"],errors="coerce")
    if a[["planned_start","planned_finish","weight_pct"]].isna().any().any():
        raise ValueError("Activities need valid planned dates and weight_pct.")
    if (a["planned_finish"]<a["planned_start"]).any() or (a["weight_pct"]<0).any():
        raise ValueError("Activity dates or weights are invalid.")
    outside=a[(a["planned_start"]<ps)|(a["planned_finish"]>pf)]
    if not outside.empty:
        ids=outside["activity_id"].astype(str).tolist() if "activity_id" in outside else outside.index.astype(str).tolist()
        raise ValueError("Activity planned dates must fall within project master dates; review: "+", ".join(ids))
    b["budget_quantity"]=pd.to_numeric(b["budget_quantity"],errors="coerce")
    b["unit_rate"]=pd.to_numeric(b["unit_rate"],errors="coerce")
    if b[["budget_quantity","unit_rate"]].isna().any().any() or (b[["budget_quantity","unit_rate"]]<0).any().any():
        raise ValueError("BOQ quantity and unit rate must be valid non-negative numbers.")
    b["budget_amount"]=pd.to_numeric(b["budget_amount"],errors="coerce") if "budget_amount" in b else np.nan
    b["budget_amount"]=b["budget_amount"].where(b["budget_amount"].notna(),b["budget_quantity"]*b["unit_rate"])
    if (b["budget_amount"]<0).any(): raise ValueError("BOQ budget amount cannot be negative.")
    # Allocate each WBS budget exactly once to activities using normalized weights.
    wbs_weight=a.groupby("wbs_id")["weight_pct"].sum().to_dict()
    baseline={}
    for _,br in b.iterrows():
        pool=a[a["wbs_id"].astype(str)==str(br["wbs_id"])]
        if pool.empty: raise ValueError(f"No activities found for BOQ WBS {br['wbs_id']}.")
        total=float(pool["weight_pct"].sum())
        if total<=0: raise ValueError(f"Activity weights for WBS {br['wbs_id']} must sum above zero.")
        amount=float(br["budget_amount"])
        for _,ar in pool.iterrows():
            share=float(ar["weight_pct"])/total
            allocated=amount*share
            start=max(ar["planned_start"],ps)
            finish=min(ar["planned_finish"],pf)
            if finish<start: continue
            days=(finish-start).days+1
            month=start.to_period("M")
            while month<=finish.to_period("M"):
                mstart=month.start_time.normalize()
                mend=month.end_time.normalize()
                overlap=max(0,(min(finish,mend)-max(start,mstart)).days+1)
                if overlap:
                    baseline[month]=baseline.get(month,0.0)+allocated*overlap/days
                month+=1
    # Actual cost by transaction month up to status date.
    actual_month={}
    if not actual.empty:
        if not {"transaction_date","amount","currency"}.issubset(actual.columns):
            raise ValueError("Actual cost requires transaction_date, amount and currency.")
        ac=actual.copy()
        ac["transaction_date"]=pd.to_datetime(ac["transaction_date"],errors="coerce")
        ac["amount"]=pd.to_numeric(ac["amount"],errors="coerce")
        if ac[["transaction_date","amount"]].isna().any().any() or (ac["amount"]<0).any():
            raise ValueError("Actual cost dates and amounts must be valid and non-negative.")
        currencies=set(ac["currency"].dropna().astype(str).str.strip())-{"","nan"}
        currency=str(project.iloc[0].get("currency","")).strip()
        if len(currencies)>1 or (currencies and currency and currencies!={currency}):
            raise ValueError("Actual cost currency does not match project currency.")
        ac=ac[ac["transaction_date"]<=sd]
        for month,group in ac.groupby(ac["transaction_date"].dt.to_period("M")):
            actual_month[month]=float(group["amount"].sum())
    # Derive EAC from the same deterministic EVM engine when approved progress exists.
    bac=float(b["budget_amount"].sum())
    cumulative_actual=sum(actual_month.values())
    eac=bac
    forecast_note="No valid CPI available; remaining forecast uses BAC less actual cost."
    if progress is not None and not progress.empty:
        evm=calculate_evm(project,activities,boq,progress,actual,sd)
        if pd.notna(evm.get("CPI")) and float(evm["CPI"])>0:
            eac=float(evm["EAC"])
            forecast_note="EAC = BAC / CPI from validated cumulative progress and actual cost."
    remaining=max(0.0,eac-cumulative_actual)
    last_month=sd.to_period("M")
    future_months=[]
    m=last_month+1
    while m<=pf.to_period("M"):
        future_months.append(m); m+=1
    if future_months:
        monthly_forecast=remaining/len(future_months)
    else:
        monthly_forecast=0.0
        if remaining>0: forecast_note="Status date is at/after project finish; remaining cost is shown as unallocated."
    months=sorted(set(baseline)|set(actual_month)|set(future_months))
    rows=[]
    cum_base=cum_actual=cum_forecast=0.0
    for month in months:
        base=float(baseline.get(month,0.0))
        act=float(actual_month.get(month,0.0))
        fc=monthly_forecast if month in future_months else 0.0
        cum_base+=base; cum_actual+=act; cum_forecast+=act+fc
        rows.append({"period":str(month),"baseline_cost":base,"actual_cost":act,
          "remaining_forecast":fc,"forecast_total":act+fc,
          "cumulative_baseline":cum_base,"cumulative_actual":cum_actual,
          "cumulative_forecast":cum_forecast})
    cashflow=pd.DataFrame(rows)
    commit_detail,commit_stats=analyze_commitments(commitments,sd, str(project.iloc[0].get("currency","")) or None)
    stats={"BAC":bac,"actual_to_date":cumulative_actual,"forecast_at_completion":eac,
      "remaining_forecast":remaining,"unallocated_remaining":remaining if not future_months else 0.0,
      "commitment_outstanding":commit_stats["outstanding_total"],
      "commitment_paid_reconciliation":commit_stats["paid_total"],
      "currency":str(project.iloc[0].get("currency","")),"forecast_method":forecast_note}
    return cashflow,stats,commit_detail

def list_project_portfolio():
    """Return a local-DB portfolio screening table; metrics remain project/currency scoped."""
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        project_ids=[row[0] for row in con.execute(
            "SELECT DISTINCT project_id FROM datasets ORDER BY project_id"
        )]
    rows=[]
    for pid in project_ids:
        master=load_dataset(pid,"project_master.csv")
        activities=load_dataset(pid,"activities.csv")
        boq=load_dataset(pid,"boq_budget.csv")
        progress=load_dataset(pid,"progress.csv")
        actual=load_dataset(pid,"actual_cost.csv")
        if master.empty:
            rows.append({"project_id":pid,"project_name":"Project master missing",
                "status_date":None,"planned_start":None,"baseline_finish":None,
                "forecast_finish":None,"schedule_slip_days":None,"currency":"",
                "BAC":None,"AC":None,"EAC":None,"SPI":None,"CPI":None,"critical_activities":None,
                "activity_count":len(activities),"portfolio_status":"Data incomplete",
                "data_readiness":"Missing project_master.csv"})
            continue
        project_name=str(master.iloc[0].get("project_name",pid))
        currency=str(master.iloc[0].get("currency",""))
        status_date=pd.to_datetime(master.iloc[0].get("status_date"),errors="coerce")
        planned_start=pd.to_datetime(master.iloc[0].get("planned_start"),errors="coerce")
        baseline_finish=pd.to_datetime(master.iloc[0].get("planned_finish"),errors="coerce")
        row={"project_id":pid,"project_name":project_name,
            "status_date":status_date.date().isoformat() if pd.notna(status_date) else None,
            "planned_start":planned_start.date().isoformat() if pd.notna(planned_start) else None,
            "baseline_finish":baseline_finish.date().isoformat() if pd.notna(baseline_finish) else None,
            "forecast_finish":None,"schedule_slip_days":None,"currency":currency,
            "BAC":None,"AC":None,"EAC":None,"SPI":None,"CPI":None,
            "critical_activities":None,"activity_count":int(len(activities)),
            "portfolio_status":"Data incomplete","data_readiness":""}
        gaps=[]
        if boq.empty: gaps.append("BOQ missing")
        if activities.empty: gaps.append("Activities missing")
        if progress.empty: gaps.append("Progress missing")
        if actual.empty: gaps.append("Actual cost missing")
        if pd.isna(status_date): gaps.append("Status date invalid")
        if not boq.empty:
            b=boq.copy()
            if "budget_amount" in b:
                amounts=pd.to_numeric(b["budget_amount"],errors="coerce")
                if amounts.notna().all(): row["BAC"]=float(amounts.sum())
            elif {"budget_quantity","unit_rate"}.issubset(b.columns):
                q=pd.to_numeric(b["budget_quantity"],errors="coerce")
                rate=pd.to_numeric(b["unit_rate"],errors="coerce")
                if q.notna().all() and rate.notna().all(): row["BAC"]=float((q*rate).sum())
        if not actual.empty and "amount" in actual:
            dates=pd.to_datetime(actual.get("transaction_date"),errors="coerce")
            amounts=pd.to_numeric(actual["amount"],errors="coerce")
            if dates.notna().all() and amounts.notna().all() and pd.notna(status_date):
                row["AC"]=float(amounts[dates<=status_date].sum())
        if not activities.empty:
            try:
                cpm,cpm_stats=calculate_cpm(activities)
                row["critical_activities"]=int(cpm["is_critical"].astype(bool).sum())
            except Exception as exc:
                gaps.append("CPM: "+str(exc)[:120])
        if not boq.empty and not activities.empty and not progress.empty and not actual.empty and pd.notna(status_date):
            try:
                evm=calculate_evm(master,activities,boq,progress,actual,status_date)
                for key in ["BAC","AC","EAC","SPI","CPI"]:
                    value=evm.get(key)
                    row[key]=float(value) if value is not None and pd.notna(value) and np.isfinite(float(value)) else None
            except Exception as exc:
                gaps.append("EVM: "+str(exc)[:160])
        if row["SPI"] is not None and pd.notna(planned_start) and pd.notna(baseline_finish) and row["SPI"] > 0:
            forecast_finish = (planned_start + (baseline_finish - planned_start) / row["SPI"]).round("D")
            row["forecast_finish"] = forecast_finish.date().isoformat()
            row["schedule_slip_days"] = int((forecast_finish.normalize() - baseline_finish.normalize()).days)
        spi=row["SPI"]; cpi=row["CPI"]
        if spi is not None and cpi is not None:
            if spi<0.9 or cpi<0.9: row["portfolio_status"]="Critical"
            elif spi<1 or cpi<1: row["portfolio_status"]="At Risk"
            else: row["portfolio_status"]="Within KPI threshold"
        elif row["critical_activities"] is not None:
            row["portfolio_status"]="CPM only - EVM unavailable"
        row["data_readiness"]="; ".join(gaps) if gaps else "Core datasets available"
        rows.append(row)
    return pd.DataFrame(rows)
