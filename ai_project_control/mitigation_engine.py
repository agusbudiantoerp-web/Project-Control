"""Decision-support layer for project recovery and mitigation scenarios.

Rules-based findings are auditable and available without an AI key. Scenario
costs are estimates based on explicitly supplied crash cost data only.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from core import calculate_cpm, optimize_crash


def build_mitigation_advice(
    activities: pd.DataFrame,
    evm: dict | None = None,
    risk_register: pd.DataFrame | None = None,
    resource_summary: pd.DataFrame | None = None,
    status_date=None,
) -> dict:
    evm = evm or {}
    risks = risk_register.copy() if risk_register is not None else pd.DataFrame()
    resources = resource_summary.copy() if resource_summary is not None else pd.DataFrame()
    cpm, stats = calculate_cpm(activities)
    critical = cpm[cpm["is_critical"].astype(bool)].copy()
    actions = []

    spi = pd.to_numeric(pd.Series([evm.get("SPI", evm.get("spi", np.nan))]), errors="coerce").iloc[0]
    cpi = pd.to_numeric(pd.Series([evm.get("CPI", evm.get("cpi", np.nan))]), errors="coerce").iloc[0]
    if pd.notna(spi) and spi < 1:
        actions.append({"priority":"High","finding":f"Schedule performance below plan (SPI {spi:.2f}).",
          "recommended_action":"Review critical-path logic, actual remaining durations and near-critical float; prepare a time-impact recovery plan.",
          "owner":"Planning Manager","timing":"Within 48 hours","expected_measure":"SPI trend and forecast finish","evidence":"Validated EVM SPI"})
    if pd.notna(cpi) and cpi < 1:
        actions.append({"priority":"High","finding":f"Cost efficiency below plan (CPI {cpi:.2f}).",
          "recommended_action":"Reconcile commitments, actual cost coding, productivity and quantity installed; freeze unapproved discretionary spend.",
          "owner":"Cost Control Manager","timing":"Within 3 working days","expected_measure":"CPI, EAC and cost variance","evidence":"Validated EVM CPI"})
    if not critical.empty:
        ids=critical["activity_id"].astype(str).tolist()
        actions.append({"priority":"High","finding":f"{len(ids)} activities are currently critical.",
          "recommended_action":"Run a focused constraint-removal review for critical activities; validate predecessor logic, access, permits, materials and crew availability before adding resources.",
          "owner":"Construction Manager","timing":"Daily until float is recovered","expected_measure":"Critical-path duration and total float","evidence":"CPM calculation"})
    if not risks.empty and {"probability","cost_impact","schedule_impact_days"}.issubset(risks.columns):
        p=pd.to_numeric(risks["probability"],errors="coerce").fillna(0).clip(0,1)
        cost=pd.to_numeric(risks["cost_impact"],errors="coerce").fillna(0).clip(lower=0)
        days=pd.to_numeric(risks["schedule_impact_days"],errors="coerce").fillna(0).clip(lower=0)
        exposure=float((p*cost).sum())
        weighted_days=float((p*days).sum())
        if exposure>0 or weighted_days>0:
            actions.append({"priority":"High" if weighted_days>=5 else "Medium",
              "finding":f"Expected-value risk exposure: cost {exposure:,.0f}; schedule {weighted_days:.1f} days.",
              "recommended_action":"Assign a named owner and due date to the highest probability-impact risks; verify response readiness and track residual exposure weekly.",
              "owner":"Risk Manager / Risk Owners","timing":"Review weekly; escalate overdue actions","expected_measure":"Residual expected cost and schedule exposure","evidence":"Risk register probability × impact"})
    if not resources.empty and "peak_utilization_pct" in resources:
        util=pd.to_numeric(resources["peak_utilization_pct"],errors="coerce")
        overloaded=resources.loc[util>100]
        if not overloaded.empty:
            actions.append({"priority":"Medium","finding":f"{len(overloaded)} resource types/assignments exceed 100% capacity.",
              "recommended_action":"Validate work fronts and dates; evaluate shift changes, resequencing or temporary capacity only after checking critical-path contribution and marginal cost.",
              "owner":"Resource Manager","timing":"Before next weekly look-ahead","expected_measure":"Peak utilization at or below approved capacity","evidence":"Resource capacity screening"})
    if not actions:
        actions.append({"priority":"Monitor","finding":"No rule-based red flag detected from the supplied metrics.",
          "recommended_action":"Maintain weekly schedule, cost, risk and resource reviews; confirm source data is current and approved.",
          "owner":"Project Manager","timing":"Weekly","expected_measure":"Stable SPI/CPI, float and risk exposure","evidence":"Available project data"})
    return {"critical_activity_ids":critical["activity_id"].astype(str).tolist(),
            "cpm_project_duration_days":float(stats.get("project_duration",0)),
            "actions":pd.DataFrame(actions)}


def compare_recovery_scenarios(activities: pd.DataFrame, target_reduction_days: int = 5) -> dict:
    """Compare baseline with a costed crash scenario; never invent crash rates."""
    cpm, stats = calculate_cpm(activities)
    baseline=float(stats.get("project_duration",0))
    result={"baseline_duration_days":baseline,"target_duration_days":max(0,baseline-int(target_reduction_days)),
            "scenario_available":False,"scenario_duration_days":np.nan,"incremental_crash_cost":np.nan,
            "crash_detail":pd.DataFrame(),"note":"Crash duration and crash cost per day data are required."}
    if {"crash_duration_days","crash_cost_per_day"}.issubset(activities.columns):
        crash, crash_stats=optimize_crash(activities, result["target_duration_days"])
        duration_key=next((k for k in ["project_duration","duration","total_duration"] if k in crash_stats),None)
        cost_key=next((k for k in ["total_crash_cost","crash_cost","total_cost"] if k in crash_stats),None)
        if duration_key and cost_key:
            result.update({"scenario_available":True,"scenario_duration_days":float(crash_stats[duration_key]),
                "incremental_crash_cost":float(crash_stats[cost_key]),"crash_detail":crash,
                "note":"Cost and duration are calculated from supplied crash limits and unit costs."})
        else:
            result["note"]="Crash engine returned an unrecognized summary schema; review output before using."
    return result
