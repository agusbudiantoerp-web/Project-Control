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
    utilization_column = next((name for name in ["peak_utilization_pct", "peak_capacity_utilization_pct"] if name in resources), None)
    if not resources.empty and utilization_column:
        util=pd.to_numeric(resources[utilization_column],errors="coerce")
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
            "scenario_available":False,"scenario_duration_days":np.nan,"days_saved":np.nan,
            "incremental_crash_cost":np.nan,"cost_per_day_saved":np.nan,
            "crash_detail":pd.DataFrame(),"note":"Crash duration and crash cost per day data are required."}
    if {"crash_duration_days","crash_cost_per_day"}.issubset(activities.columns):
        try:
            crash, crash_stats=optimize_crash(activities, result["target_duration_days"])
            duration_key=next((k for k in ["achieved_duration","project_duration","duration","total_duration"] if k in crash_stats),None)
            cost_key=next((k for k in ["total_crash_cost","crash_cost","total_cost"] if k in crash_stats),None)
            if duration_key and cost_key:
                scenario_duration=float(crash_stats[duration_key])
                scenario_cost=float(crash_stats[cost_key])
                if not np.isfinite(scenario_duration) or not np.isfinite(scenario_cost) or scenario_cost < 0:
                    result["note"]="Crash engine returned non-finite or invalid scenario metrics."
                else:
                    days_saved=max(0.0,baseline-scenario_duration)
                    result.update({"scenario_available":True,"scenario_duration_days":scenario_duration,
                        "days_saved":days_saved,"incremental_crash_cost":scenario_cost,
                        "cost_per_day_saved":scenario_cost/days_saved if days_saved>0 else np.nan,
                        "crash_detail":crash,
                        "note":"Cost and duration are calculated from supplied crash limits and unit costs."})
            else:
                result["note"]="Crash engine returned an unrecognized summary schema; review output before using."
        except (ValueError, RuntimeError, KeyError, TypeError) as exc:
            result["note"]=f"Recovery target is infeasible or crash inputs are invalid: {exc}"
    return result

def compare_multiple_recovery_scenarios(
    activities: pd.DataFrame,
    target_reductions_days=(1, 3, 5, 7, 10),
) -> dict:
    """Compare several feasible schedule-crashing targets against one CPM baseline.

    Each alternative is independently optimized by the existing minimum-cost
    crash solver. No unit costs, crash limits, or savings are inferred.
    """
    if not isinstance(activities, pd.DataFrame) or activities.empty:
        raise ValueError("Activities must be a non-empty DataFrame.")
    try:
        reductions = sorted({int(value) for value in target_reductions_days})
    except (TypeError, ValueError) as exc:
        raise ValueError("Target reductions must be positive whole numbers.") from exc
    if not reductions or any(value <= 0 for value in reductions):
        raise ValueError("At least one positive target reduction is required.")

    baseline_cpm, baseline_stats = calculate_cpm(activities)
    baseline = float(baseline_stats.get("project_duration", 0.0))
    if not np.isfinite(baseline) or baseline <= 0:
        raise ValueError("CPM baseline duration must be finite and greater than zero.")

    scenarios = []
    details = {}
    for reduction in reductions:
        target = max(0.0, baseline - reduction)
        result = compare_recovery_scenarios(activities, int(np.ceil(reduction)))
        achieved = result.get("scenario_duration_days", np.nan)
        cost = result.get("incremental_crash_cost", np.nan)
        saved = result.get("days_saved", np.nan)
        feasible = bool(result.get("scenario_available", False))
        scenarios.append({
            "scenario": f"Recover {reduction} day(s)",
            "requested_days_saved": reduction,
            "target_duration_days": target,
            "achieved_duration_days": achieved,
            "actual_days_saved": saved,
            "incremental_cost": cost,
            "cost_per_day_saved": result.get("cost_per_day_saved", np.nan),
            "feasible": feasible,
            "note": result.get("note", ""),
        })
        details[f"reduction_{reduction}_days"] = result.get("crash_detail", pd.DataFrame())

    table = pd.DataFrame(scenarios)
    feasible_rows = table[table["feasible"]].copy()
    if not feasible_rows.empty:
        feasible_rows = feasible_rows.sort_values(
            ["incremental_cost", "cost_per_day_saved", "actual_days_saved"],
            ascending=[True, True, False], kind="stable"
        )
        recommended = feasible_rows.iloc[0].to_dict()
        recommendation_basis = "Lowest incremental crash cost among feasible scenarios."
    else:
        recommended = None
        recommendation_basis = (
            "No feasible costed scenario. Confirm crash duration and crash cost/day "
            "inputs, and review the requested recovery targets."
        )
    return {
        "baseline_duration_days": baseline,
        "critical_activity_ids": baseline_cpm.loc[
            baseline_cpm["is_critical"].astype(bool), "activity_id"
        ].astype(str).tolist(),
        "scenarios": table,
        "scenario_details": details,
        "recommended_scenario": recommended,
        "recommendation_basis": recommendation_basis,
        "assumptions": [
            "Each target is optimized independently from the same uncrashed baseline.",
            "Crash cost/day is assumed linear as supplied by the user.",
            "Resource availability, calendars, indirect cost and time-dependent penalties are not inferred.",
            "A scenario is decision support only and does not change the approved baseline.",
        ],
    }

def build_recovery_decision_matrix(
    recovery_scenarios: pd.DataFrame,
    resource_scenarios: pd.DataFrame | None = None,
    risk_register: pd.DataFrame | None = None,
) -> dict:
    """Rank costed schedule-recovery options and disclose non-costed constraints.

    Resource and shift scenarios are supporting feasibility screens only.
    They are never assigned invented costs or blended into a false optimum.
    """
    if not isinstance(recovery_scenarios, pd.DataFrame) or recovery_scenarios.empty:
        raise ValueError("Recovery scenario comparison is required.")
    required = {"scenario", "actual_days_saved", "incremental_cost", "feasible"}
    missing = required - set(recovery_scenarios.columns)
    if missing:
        raise ValueError("Recovery scenarios missing: " + ", ".join(sorted(missing)))
    ranked = recovery_scenarios.copy()
    ranked["actual_days_saved"] = pd.to_numeric(ranked["actual_days_saved"], errors="coerce")
    ranked["incremental_cost"] = pd.to_numeric(ranked["incremental_cost"], errors="coerce")
    ranked["feasible"] = ranked["feasible"].fillna(False).astype(bool)
    valid = ranked[
        ranked["feasible"] & ranked["actual_days_saved"].gt(0)
        & ranked["incremental_cost"].ge(0)
        & np.isfinite(ranked["incremental_cost"])
    ].copy()
    if not valid.empty:
        valid["cost_per_day_saved"] = valid["incremental_cost"] / valid["actual_days_saved"]
        valid = valid.sort_values(
            ["incremental_cost", "cost_per_day_saved", "actual_days_saved"],
            ascending=[True, True, False], kind="stable"
        ).reset_index(drop=True)
        valid["rank"] = np.arange(1, len(valid) + 1)
        recommendation = valid.iloc[0].to_dict()
        decision = "Ranked by lowest verified incremental crash cost; tie-break by cost/day saved."
    else:
        valid["cost_per_day_saved"] = pd.Series(dtype=float)
        valid["rank"] = pd.Series(dtype=int)
        recommendation = None
        decision = "No costed feasible recovery option. Complete crash inputs before selecting a cost optimum."

    resource_notes = []
    if resource_scenarios is not None and not resource_scenarios.empty:
        if {"shifts_per_day", "overloaded_resource_days"}.issubset(resource_scenarios.columns):
            for row in resource_scenarios.to_dict("records"):
                resource_notes.append({
                    "option": f'{row["shifts_per_day"]} shift(s)',
                    "overloaded_resource_days": row.get("overloaded_resource_days"),
                    "incremental_cost": row.get("incremental_cost", np.nan),
                    "decision_status": "Capacity screen only; cost inputs required before economic ranking.",
                })
        else:
            resource_notes.append({
                "option": "Resource scenario",
                "decision_status": "Resource scenario schema not recognized; not used in ranking.",
            })

    risk_exposure = None
    if risk_register is not None and not risk_register.empty:
        needed = {"probability", "cost_impact", "schedule_impact_days"}
        if needed.issubset(risk_register.columns):
            probability = pd.to_numeric(risk_register["probability"], errors="coerce").clip(0, 1)
            cost = pd.to_numeric(risk_register["cost_impact"], errors="coerce").clip(lower=0)
            days = pd.to_numeric(risk_register["schedule_impact_days"], errors="coerce").clip(lower=0)
            risk_exposure = {
                "expected_cost_exposure": float((probability * cost).sum()),
                "expected_schedule_exposure_days": float((probability * days).sum()),
                "method": "Sum of probability × impact; independent additive screening, not a Monte Carlo percentile.",
            }
    return {
        "ranked_options": valid,
        "recommended_option": recommendation,
        "decision_basis": decision,
        "resource_screening": pd.DataFrame(resource_notes),
        "risk_exposure": risk_exposure,
        "limitations": [
            "Only feasible scenarios with explicit finite crash costs are economically ranked.",
            "Shift and resource capacity factors are not converted to cost without approved rates.",
            "Risk exposure is shown separately and is not deducted from or added to crash cost.",
            "This is decision support; approval and baseline changes remain under project governance.",
        ],
    }
