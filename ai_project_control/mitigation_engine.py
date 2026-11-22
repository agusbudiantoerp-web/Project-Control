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

def build_predictive_warnings(
    trend: dict | None,
    history: pd.DataFrame | None = None,
    cpm: pd.DataFrame | None = None,
    status_date=None,
    planned_finish=None,
    near_critical_threshold_days: float = 5.0,
) -> dict:
    """Create transparent trend-based warnings; require reporting history for trends."""
    warnings = []
    if trend:
        spi = pd.to_numeric(pd.Series([trend.get("latest_SPI")]), errors="coerce").iloc[0]
        cpi = pd.to_numeric(pd.Series([trend.get("latest_CPI")]), errors="coerce").iloc[0]
        finish = pd.to_datetime(trend.get("trend_finish_forecast"), errors="coerce")
        baseline_finish = pd.to_datetime(planned_finish, errors="coerce")
        if pd.notna(spi) and spi < 1:
            warnings.append({
                "priority": "High" if spi < 0.9 else "Medium",
                "signal": f"Latest SPI is {spi:.2f}, below 1.00.",
                "recommended_action": "Review remaining durations, logic, constraints and critical/near-critical work fronts; issue a dated recovery plan.",
                "evidence": "Latest approved EVM reporting period",
            })
        if pd.notna(cpi) and cpi < 1:
            warnings.append({
                "priority": "High" if cpi < 0.9 else "Medium",
                "signal": f"Latest CPI is {cpi:.2f}, below 1.00.",
                "recommended_action": "Reconcile actual cost and commitments, then validate productivity, quantities and remaining-cost assumptions.",
                "evidence": "Latest approved EVM reporting period",
            })
        if pd.notna(finish) and pd.notna(baseline_finish) and finish.normalize() > baseline_finish.normalize():
            warnings.append({
                "priority": "High",
                "signal": f"Trend finish forecast {finish.date()} is later than baseline finish {baseline_finish.date()}.",
                "recommended_action": "Validate the trend with the current CPM network and quantify recovery options before changing the approved forecast.",
                "evidence": "Linear trend of cumulative earned-value progress",
            })
        if history is not None and len(history) >= 4:
            recent = history.tail(4)
            for metric, label in [("SPI", "Schedule"), ("CPI", "Cost")]:
                values = pd.to_numeric(recent[metric], errors="coerce").dropna()
                if len(values) >= 4 and values.iloc[-1] < values.iloc[0] and values.iloc[-1] < 1:
                    warnings.append({
                        "priority": "High" if values.iloc[-1] < 0.9 else "Medium",
                        "signal": f"{label} efficiency has deteriorated across the latest four reporting periods.",
                        "recommended_action": f"Investigate the {label.lower()} performance trend and assign corrective actions with owners and due dates.",
                        "evidence": f"Four-period {metric} history",
                    })
    else:
        warnings.append({
            "priority": "Information",
            "signal": "Predictive trend unavailable: at least three valid approved reporting periods are required.",
            "recommended_action": "Load and validate dated progress, BOQ and actual-cost reporting periods before using trend forecasts.",
            "evidence": "Data readiness check",
        })

    if cpm is not None and not cpm.empty and "total_float_days" in cpm:
        float_values = pd.to_numeric(cpm["total_float_days"], errors="coerce")
        near = cpm.loc[float_values.ge(0) & float_values.le(float(near_critical_threshold_days))]
        if not near.empty:
            warnings.append({
                "priority": "Medium",
                "signal": f"{len(near)} activities have total float between 0 and {near_critical_threshold_days:g} days.",
                "recommended_action": "Monitor near-critical activities in the look-ahead plan and verify resource, access, permit and material constraints.",
                "evidence": "Current CPM total-float calculation",
            })
    return {
        "warnings": pd.DataFrame(warnings),
        "reporting_periods": int(trend.get("reporting_periods", 0)) if trend else 0,
        "method": "Rule-based screening of approved EVM trends and current CPM float; not a machine-learning probability model.",
    }

def diagnose_project_drivers(
    activities: pd.DataFrame,
    boq: pd.DataFrame | None = None,
    progress: pd.DataFrame | None = None,
    actual_cost: pd.DataFrame | None = None,
    risk_register: pd.DataFrame | None = None,
) -> dict:
    """Build evidence-linked schedule, quantity, cost and risk driver findings."""
    findings = []
    if activities is None or activities.empty:
        return {"findings": pd.DataFrame(), "data_gaps": ["Activities dataset is missing."]}
    acts = activities.copy()
    acts["activity_id"] = acts["activity_id"].astype(str)
    if progress is not None and not progress.empty:
        p = progress.copy()
        p["activity_id"] = p["activity_id"].astype(str)
        p["actual_quantity_to_date"] = pd.to_numeric(p["actual_quantity_to_date"], errors="coerce")
        p["period_end"] = pd.to_datetime(p["period_end"], errors="coerce")
        p = p.dropna(subset=["actual_quantity_to_date", "period_end"])
        if not p.empty:
            latest = p.sort_values("period_end").groupby("activity_id", as_index=False).tail(1)
            if "planned_quantity_to_date" in latest:
                latest["planned_quantity_to_date"] = pd.to_numeric(latest["planned_quantity_to_date"], errors="coerce")
                lagging = latest[
                    latest["planned_quantity_to_date"].gt(0)
                    & latest["actual_quantity_to_date"].lt(latest["planned_quantity_to_date"])
                ]
                merged = lagging.merge(acts[["activity_id", "activity_name"]], on="activity_id", how="left")
                for row in merged.to_dict("records"):
                    variance = float(row["planned_quantity_to_date"] - row["actual_quantity_to_date"])
                    findings.append({
                        "domain": "Progress / Schedule", "priority": "High" if variance / row["planned_quantity_to_date"] >= 0.2 else "Medium",
                        "driver": f'Quantity behind plan on {row.get("activity_name", row["activity_id"])}',
                        "evidence": f'Planned {row["planned_quantity_to_date"]:,.2f}; actual {row["actual_quantity_to_date"]:,.2f}; variance {variance:,.2f}',
                        "recommended_action": "Validate measurement cut-off and installed quantities; investigate access, productivity, materials, permits and crew constraints.",
                        "owner": "Construction / Planning Manager",
                    })
    if boq is not None and not boq.empty and actual_cost is not None and not actual_cost.empty:
        b = boq.copy()
        a = actual_cost.copy()
        if {"boq_id", "budget_amount"}.issubset(b.columns) and {"boq_id", "amount"}.issubset(a.columns):
            b["budget_amount"] = pd.to_numeric(b["budget_amount"], errors="coerce")
            a["amount"] = pd.to_numeric(a["amount"], errors="coerce")
            budget = b.groupby("boq_id", as_index=False)["budget_amount"].sum()
            actual = a.groupby("boq_id", as_index=False)["amount"].sum()
            joined = budget.merge(actual, on="boq_id", how="left").fillna({"amount": 0})
            joined["cost_variance_to_budget"] = joined["amount"] - joined["budget_amount"]
            over = joined[joined["cost_variance_to_budget"] > 0]
            for row in over.to_dict("records"):
                findings.append({
                    "domain": "Cost", "priority": "High" if row["cost_variance_to_budget"] / max(abs(row["budget_amount"]), 1) >= 0.1 else "Medium",
                    "driver": f'Actual cost exceeds BOQ budget for {row["boq_id"]}',
                    "evidence": f'Budget {row["budget_amount"]:,.2f}; recorded actual {row["amount"]:,.2f}; variance {row["cost_variance_to_budget"]:,.2f}',
                    "recommended_action": "Reconcile actual cost cut-off, accruals, BOQ mapping, quantities installed and approved changes before concluding an overrun.",
                    "owner": "Cost Control Manager",
                })
    if risk_register is not None and not risk_register.empty:
        risks = risk_register.copy()
        needed = {"risk_description", "probability", "cost_impact", "schedule_impact_days"}
        if needed.issubset(risks.columns):
            for _, row in risks.iterrows():
                probability = pd.to_numeric(pd.Series([row["probability"]]), errors="coerce").iloc[0]
                cost = pd.to_numeric(pd.Series([row["cost_impact"]]), errors="coerce").iloc[0]
                days = pd.to_numeric(pd.Series([row["schedule_impact_days"]]), errors="coerce").iloc[0]
                if pd.notna(probability) and pd.notna(cost) and pd.notna(days) and probability > 0 and (cost > 0 or days > 0):
                    findings.append({
                        "domain": "Risk", "priority": "High" if probability >= 0.5 or days >= 10 else "Medium",
                        "driver": str(row["risk_description"]),
                        "evidence": f"Probability {probability:.0%}; cost impact {cost:,.2f}; schedule impact {days:,.1f} days",
                        "recommended_action": "Confirm risk owner, response funding, trigger, due date and residual exposure; escalate overdue mitigations.",
                        "owner": str(row.get("owner", "Risk Owner") or "Risk Owner"),
                    })
    gaps = []
    if progress is None or progress.empty:
        gaps.append("Progress history is unavailable; activity-level delay drivers cannot be confirmed.")
    elif "planned_quantity_to_date" not in progress.columns:
        gaps.append("Planned quantity-to-date is unavailable; quantity variance cannot be calculated.")
    if boq is None or boq.empty or actual_cost is None or actual_cost.empty:
        gaps.append("BOQ budget or actual-cost data is unavailable; cost driver analysis is incomplete.")
    return {"findings": pd.DataFrame(findings), "data_gaps": gaps}
