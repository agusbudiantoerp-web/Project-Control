"""Resource capacity smoothing scenarios; recommendations never overwrite baseline data."""
from __future__ import annotations
import pandas as pd
import numpy as np
from core import calculate_cpm


def simulate_resource_smoothing(
    activities: pd.DataFrame,
    resources: pd.DataFrame,
    assignments: pd.DataFrame,
    max_shift_days: int = 30,
) -> dict:
    """Greedy, auditable what-if allocation within CPM total float.

    It shifts resource demand only; it does not alter activity logic, durations,
    or approved baseline dates. A result is a planning suggestion, not leveling.
    """
    if activities.empty or assignments.empty or resources.empty:
        return {"available": False, "reason": "Activities, resources, and assignments are required.",
                "baseline_overloaded_days": 0, "scenario_overloaded_days": 0,
                "scenario": pd.DataFrame(), "summary": pd.DataFrame()}
    required_a={"task_id","rsrc_id","target_qty","target_start_date","target_end_date"}
    required_r={"rsrc_id","capacity_per_day"}
    if required_a-set(assignments.columns):
        raise ValueError("Resource assignments missing: "+", ".join(sorted(required_a-set(assignments.columns))))
    if required_r-set(resources.columns):
        raise ValueError("Resources missing: "+", ".join(sorted(required_r-set(resources.columns))))
    cpm,_=calculate_cpm(activities)
    float_map=dict(zip(cpm["activity_id"].astype(str),pd.to_numeric(cpm["total_float_days"],errors="coerce").fillna(0).clip(lower=0)))
    cap_map=dict(zip(resources["rsrc_id"].astype(str),pd.to_numeric(resources["capacity_per_day"],errors="coerce")))
    rows=assignments.copy().reset_index(drop=True)
    rows["task_id"]=rows["task_id"].astype(str)
    rows["rsrc_id"]=rows["rsrc_id"].astype(str)
    rows["target_qty"]=pd.to_numeric(rows["target_qty"],errors="coerce")
    rows["base_start"]=pd.to_datetime(rows["target_start_date"],errors="coerce").dt.normalize()
    rows["base_finish"]=pd.to_datetime(rows["target_end_date"],errors="coerce").dt.normalize()
    if rows[["target_qty","base_start","base_finish"]].isna().any().any() or (rows["target_qty"]<0).any() or (rows["base_finish"]<rows["base_start"]).any():
        raise ValueError("Resource assignment quantity/date range is invalid.")
    unknown=set(rows["rsrc_id"])-set(cap_map)
    if unknown: raise ValueError("Unknown resource IDs: "+", ".join(sorted(unknown)))
    if any(pd.isna(cap_map[x]) or not np.isfinite(cap_map[x]) or cap_map[x]<=0 for x in rows["rsrc_id"].unique()):
        raise ValueError("Resource capacity must be finite and greater than zero.")
    rows["float_days"]=rows["task_id"].map(float_map).fillna(0).clip(lower=0).astype(int)
    rows["critical"]=rows["float_days"].eq(0)
    # Baseline daily demand map
    def daily_map(frame, start_col, finish_col):
        load={}
        for row in frame.itertuples():
            days=pd.date_range(getattr(row,start_col),getattr(row,finish_col),freq="D")
            per_day=float(row.target_qty)/len(days)
            for day in days:
                key=(row.rsrc_id,day)
                load[key]=load.get(key,0.0)+per_day
        return load
    baseline=daily_map(rows,"base_start","base_finish")
    # Place critical work first, then least-float tasks; ties preserve original order.
    ordered=rows.sort_values(["critical","float_days"],ascending=[False,True],kind="stable")
    placed={}
    scenario_load={}
    for idx,row in ordered.iterrows():
        duration=int((row["base_finish"]-row["base_start"]).days)+1
        allowance=min(int(row["float_days"]),int(max_shift_days))
        best=None
        for shift in range(allowance+1):
            start=row["base_start"]+pd.Timedelta(days=shift)
            finish=start+pd.Timedelta(days=duration-1)
            demand=float(row["target_qty"])/duration
            keys=[(row["rsrc_id"],d) for d in pd.date_range(start,finish,freq="D")]
            overload=sum(max(0.0,scenario_load.get(k,0.0)+demand-cap_map[row["rsrc_id"]]) for k in keys)
            if best is None or overload<best[0]:
                best=(overload,shift,start,finish,keys,demand)
            if overload<=1e-9: break
        _,shift,start,finish,keys,demand=best
        for key in keys: scenario_load[key]=scenario_load.get(key,0.0)+demand
        placed[idx]={"suggested_start":start,"suggested_finish":finish,"shift_days":shift,
                     "remaining_float_days":max(0,int(row["float_days"])-shift)}
    out=rows.copy()
    for idx,vals in placed.items():
        for k,v in vals.items(): out.loc[idx,k]=v
    out["baseline_start"]=out["base_start"]
    out["baseline_finish"]=out["base_finish"]
    out["status"]=np.where(out["shift_days"]>0,"Suggested shift","No shift")
    def overloaded_days(load):
        count=0
        for (rid,day),qty in load.items():
            if qty>cap_map[rid]+1e-9: count+=1
        return count
    baseline_over=overloaded_days(baseline)
    scenario_over=overloaded_days(scenario_load)
    summary=pd.DataFrame([
        {"scenario":"Baseline","overloaded_resource_days":baseline_over},
        {"scenario":"Smoothed suggestion","overloaded_resource_days":scenario_over},
    ])
    return {"available":True,"reason":"What-if only; original baseline and activity logic remain unchanged.",
            "baseline_overloaded_days":baseline_over,"scenario_overloaded_days":scenario_over,
            "scenario":out[["task_id","rsrc_id","target_qty","baseline_start","baseline_finish","suggested_start","suggested_finish","float_days","shift_days","remaining_float_days","status"]],
            "summary":summary}
