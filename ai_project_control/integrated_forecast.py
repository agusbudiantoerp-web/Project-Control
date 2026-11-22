"""Integrated project forecast engine.

Combines schedule, earned value, resource capacity and quantified risk into
one deterministic baseline forecast plus reproducible Monte Carlo scenarios.
This module is deliberately independent from the Streamlit UI.
"""
from __future__ import annotations

from datetime import date
import numpy as np
import pandas as pd
from core import calculate_cpm, build_cost_cashflow


def _number(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default).astype(float)


def _date(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
    return pd.to_datetime(frame[column], errors="coerce")


def build_integrated_forecast(
    activities: pd.DataFrame,
    boq_budget: pd.DataFrame | None = None,
    progress: pd.DataFrame | None = None,
    actual_cost: pd.DataFrame | None = None,
    resources: pd.DataFrame | None = None,
    resource_assignments: pd.DataFrame | None = None,
    risk_register: pd.DataFrame | None = None,
    project_master: pd.DataFrame | None = None,
    commitments: pd.DataFrame | None = None,
    status_date: str | date | pd.Timestamp | None = None,
    simulations: int = 5000,
    seed: int = 42,
) -> dict:
    """Return integrated schedule/cost/resource/risk forecast.

    Required schedule columns: activity_id, planned_start, planned_finish.
    EVM is calculated when BOQ, progress and actual-cost inputs are supplied.
    Resource overload is a screening metric, not resource leveling.
    Risk impacts are sampled as independent Bernoulli events.
    """
    frames = [activities, boq_budget, progress, actual_cost, resources,
              resource_assignments, risk_register]
    activities = activities.copy() if activities is not None else pd.DataFrame()
    boq_budget = boq_budget.copy() if boq_budget is not None else pd.DataFrame()
    progress = progress.copy() if progress is not None else pd.DataFrame()
    actual_cost = actual_cost.copy() if actual_cost is not None else pd.DataFrame()
    resources = resources.copy() if resources is not None else pd.DataFrame()
    resource_assignments = resource_assignments.copy() if resource_assignments is not None else pd.DataFrame()
    risk_register = risk_register.copy() if risk_register is not None else pd.DataFrame()
    project_master = project_master.copy() if project_master is not None else pd.DataFrame()
    commitments = commitments.copy() if commitments is not None else pd.DataFrame()

    if activities.empty:
        raise ValueError("Dataset activities kosong; forecast tidak dapat dihitung.")
    missing = {"activity_id", "planned_start", "planned_finish"} - set(activities.columns)
    if missing:
        raise ValueError("Kolom activities wajib tidak ada: " + ", ".join(sorted(missing)))

    starts, finishes = _date(activities, "planned_start"), _date(activities, "planned_finish")
    valid = starts.notna() & finishes.notna() & (finishes >= starts)
    if not valid.all():
        raise ValueError("Tanggal planned_start/planned_finish tidak valid atau finish lebih awal dari start.")
    status = pd.Timestamp(status_date).normalize() if status_date is not None else pd.Timestamp.today().normalize()
    project_start, baseline_finish = starts.min().normalize(), finishes.max().normalize()
    remaining = max(0, int((baseline_finish - status).days))
    elapsed = max(0, int((status - project_start).days))
    total_baseline_days = max(1, int((baseline_finish - project_start).days))

    # Earned value: budget is allocated to progress rows through BOQ item.
    bac = pv = ev = ac = float("nan")
    cpi = spi = eac = etc = forecast_cost = float("nan")
    evm_ready = {"boq_budget.csv", "progress.csv", "actual_cost.csv"}
    if (not boq_budget.empty and not progress.empty and not actual_cost.empty
            and {"boq_id", "budget_quantity", "unit_rate"} <= set(boq_budget.columns)
            and {"boq_id", "actual_quantity_to_date"} <= set(progress.columns)
            and "amount" in actual_cost.columns):
        boq = boq_budget.copy()
        boq["budget_quantity"] = _number(boq, "budget_quantity")
        boq["unit_rate"] = _number(boq, "unit_rate")
        if "budget_amount" in boq:
            amount = _number(boq, "budget_amount")
            boq["budget_amount_calc"] = amount.where(amount > 0, boq["budget_quantity"] * boq["unit_rate"])
        else:
            boq["budget_amount_calc"] = boq["budget_quantity"] * boq["unit_rate"]
        bac = float(boq["budget_amount_calc"].sum())
        joined = progress.merge(boq[["boq_id", "budget_quantity", "budget_amount_calc"]],
                                on="boq_id", how="inner")
        joined["actual_quantity_to_date"] = _number(joined, "actual_quantity_to_date")
        joined["earned"] = np.where(joined["budget_quantity"] > 0,
            np.minimum(joined["actual_quantity_to_date"] / joined["budget_quantity"], 1.0)
            * joined["budget_amount_calc"], 0.0)
        ev = float(joined["earned"].sum())
        if "planned_quantity_to_date" in joined:
            joined["planned_quantity_to_date"] = _number(joined, "planned_quantity_to_date")
            joined["planned_value"] = np.where(joined["budget_quantity"] > 0,
                np.minimum(joined["planned_quantity_to_date"] / joined["budget_quantity"], 1.0)
                * joined["budget_amount_calc"], 0.0)
            pv = float(joined["planned_value"].sum())
        ac = float(_number(actual_cost, "amount").sum())
        cpi = ev / ac if ac > 0 else float("nan")
        spi = ev / pv if pv > 0 else float("nan")
        eac = ac + (bac - ev) / cpi if cpi > 0 else float("nan")
        etc = eac - ac if np.isfinite(eac) else float("nan")
        forecast_cost = eac

    # CPM baseline: identify critical path and total network duration.
    cpm_frame = activities.copy()
    if "activity_name" not in cpm_frame:
        cpm_frame["activity_name"] = cpm_frame["activity_id"].astype(str)
    if "wbs_id" not in cpm_frame:
        cpm_frame["wbs_id"] = ""
    if "duration_days" not in cpm_frame:
        cpm_frame["duration_days"] = (
            (_date(cpm_frame, "planned_finish") - _date(cpm_frame, "planned_start")).dt.days + 1
        )
    cpm_result, cpm_stats = calculate_cpm(cpm_frame)
    cpm_duration = float(cpm_stats.get("project_duration", 0.0))
    critical_count = int(cpm_result["is_critical"].sum()) if "is_critical" in cpm_result else 0
    critical_ids = cpm_result.loc[cpm_result["is_critical"], "activity_id"].astype(str).tolist() if "is_critical" in cpm_result else []

    # Trend forecast uses measured progress; CPM remains the network baseline.
    physical_progress = (ev / bac) if np.isfinite(ev) and bac > 0 else float("nan")
    if np.isfinite(spi) and spi > 0:
        forecast_finish = status + pd.Timedelta(days=int(np.ceil(remaining / spi)))
        schedule_basis = "CPM network + EVM SPI adjustment"
    else:
        forecast_finish = baseline_finish
        schedule_basis = "CPM network baseline (SPI unavailable)"

    # Resource load screening: spread each assignment over its activity's planned span.
    overload_rows = 0
    resource_summary = pd.DataFrame()
    if not resources.empty and not resource_assignments.empty:
        ra = resource_assignments.copy()
        act_dates = activities[["activity_id", "planned_start", "planned_finish"]].copy()
        ra = ra.merge(act_dates, left_on="task_id", right_on="activity_id", how="left")
        ra = ra.merge(resources[["rsrc_id", "capacity_per_day"]], on="rsrc_id", how="left")
        ra["target_qty"] = _number(ra, "target_qty")
        ra["capacity_per_day"] = _number(ra, "capacity_per_day")
        span = (_date(ra, "planned_end_date") - _date(ra, "planned_start_date")).dt.days if "planned_end_date" in ra else (_date(ra, "planned_finish") - _date(ra, "planned_start")).dt.days
        span = span.fillna(0).clip(lower=1) + 1
        ra["planned_daily_load"] = ra["target_qty"] / span
        ra["capacity_utilization_pct"] = np.where(ra["capacity_per_day"] > 0,
            ra["planned_daily_load"] / ra["capacity_per_day"] * 100, np.nan)
        overload_rows = int((ra["capacity_utilization_pct"] > 100).sum())
        resource_summary = ra.groupby("rsrc_id", dropna=False).agg(
            assignments=("task_id", "count"),
            peak_daily_load=("planned_daily_load", "max"),
            capacity_per_day=("capacity_per_day", "max"),
            peak_utilization_pct=("capacity_utilization_pct", "max"),
        ).reset_index()

    # Independent risk occurrence simulation. Negative impacts are floored at zero.
    risk_cost_p50 = risk_cost_p80 = risk_days_p50 = risk_days_p80 = 0.0
    risk_count = len(risk_register)
    if risk_count:
        if not {"probability", "cost_impact", "schedule_impact_days"} <= set(risk_register.columns):
            raise ValueError("Risk register membutuhkan probability, cost_impact, schedule_impact_days.")
        probs = _number(risk_register, "probability").clip(0, 1).to_numpy()
        costs = _number(risk_register, "cost_impact").clip(lower=0).to_numpy()
        days = _number(risk_register, "schedule_impact_days").clip(lower=0).to_numpy()
        rng = np.random.default_rng(seed)
        events = rng.random((max(100, int(simulations)), risk_count)) < probs
        cost_samples = events @ costs
        day_samples = events @ days
        risk_cost_p50, risk_cost_p80 = [float(x) for x in np.quantile(cost_samples, [0.50, 0.80])]
        risk_days_p50, risk_days_p80 = [float(x) for x in np.quantile(day_samples, [0.50, 0.80])]

    risk_adjusted_finish_p80 = forecast_finish + pd.Timedelta(days=int(np.ceil(risk_days_p80)))
    risk_adjusted_cost_p80 = (forecast_cost + risk_cost_p80
                              if np.isfinite(forecast_cost) else float("nan"))
    cashflow = pd.DataFrame()
    cashflow_stats = {}
    cashflow_commitments = pd.DataFrame()
    if not project_master.empty and not boq_budget.empty:
        cashflow, cashflow_stats, cashflow_commitments = build_cost_cashflow(
            project_master, activities, boq_budget, actual_cost, commitments,
            status, progress
        )
    return {
        "status_date": status.date().isoformat(),
        "baseline_start": project_start.date().isoformat(),
        "baseline_finish": baseline_finish.date().isoformat(),
        "forecast_finish": forecast_finish.date().isoformat(),
        "risk_adjusted_finish_p80": risk_adjusted_finish_p80.date().isoformat(),
        "schedule_basis": schedule_basis,
        "cpm_project_duration_days": cpm_duration,
        "critical_activity_count": critical_count,
        "critical_activity_ids": critical_ids,
        "cpm_activity_detail": cpm_result,
        "baseline_duration_days": total_baseline_days,
        "remaining_baseline_days": remaining,
        "bac": bac, "pv": pv, "ev": ev, "ac": ac,
        "physical_progress_pct": physical_progress * 100 if np.isfinite(physical_progress) else float("nan"),
        "cpi": cpi, "spi": spi, "eac": eac, "etc": etc,
        "risk_cost_p50": risk_cost_p50, "risk_cost_p80": risk_cost_p80,
        "risk_days_p50": risk_days_p50, "risk_days_p80": risk_days_p80,
        "risk_adjusted_cost_p80": risk_adjusted_cost_p80,
        "resource_overload_assignments": overload_rows,
        "resource_summary": resource_summary,
        "cashflow": cashflow,
        "cashflow_stats": cashflow_stats,
        "cashflow_commitments": cashflow_commitments,
        "risk_count": risk_count,
        "evm_available": bool(np.isfinite(bac) and np.isfinite(ev) and np.isfinite(ac)),
        "assumptions": [
            "Forecast SPI memakai rasio EV/PV; jika PV belum tersedia, tanggal memakai baseline.",
            "Risiko dianggap independen dan dampak dijumlahkan; korelasi risiko belum dimodelkan.",
            "Resource load adalah screening kapasitas rata-rata, bukan resource leveling harian.",
            "P80 risiko adalah kuantil simulasi risiko, bukan jaminan penyelesaian.",
        ],
    }
