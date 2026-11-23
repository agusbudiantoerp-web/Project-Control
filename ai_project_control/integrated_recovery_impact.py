"""Integrated schedule, cost, resource and risk impact comparison."""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


def build_integrated_recovery_impact(
    scenarios: pd.DataFrame,
    resource_assessment: pd.DataFrame | None = None,
    risk_assessment: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Assemble scenario impacts only from explicit, scenario-linked evidence.

    Optional resource_assessment and risk_assessment must contain a scenario
    column. Missing domain data is labelled NOT ASSESSED, never assumed clear.
    """
    empty = pd.DataFrame()
    required = {"scenario", "actual_days_saved", "incremental_cost", "feasible"}
    if not isinstance(scenarios, pd.DataFrame) or scenarios.empty:
        return {"available": False, "comparison": empty, "assumptions": ["No recovery scenarios supplied."]}
    missing = required - set(scenarios.columns)
    if missing:
        return {"available": False, "comparison": empty,
                "assumptions": ["Missing scenario fields: " + ", ".join(sorted(missing))]}
    result = scenarios.copy()
    result["actual_days_saved"] = pd.to_numeric(result["actual_days_saved"], errors="coerce")
    result["incremental_cost"] = pd.to_numeric(result["incremental_cost"], errors="coerce")
    result["feasible"] = result["feasible"].fillna(False).astype(bool)
    result["cost_per_day_saved"] = result["incremental_cost"] / result["actual_days_saved"].where(result["actual_days_saved"] > 0)
    result["schedule_assessment"] = np.where(
        result["feasible"] & result["actual_days_saved"].gt(0),
        "FEASIBLE — modeled schedule benefit",
        "NOT FEASIBLE / NO VERIFIED TIME BENEFIT",
    )
    result["resource_assessment_status"] = "NOT ASSESSED"
    result["resource_shortfall"] = np.nan
    result["resource_notes"] = "No scenario-linked resource assessment supplied."
    if isinstance(resource_assessment, pd.DataFrame) and not resource_assessment.empty:
        if "scenario" not in resource_assessment.columns:
            return {"available": False, "comparison": empty,
                    "assumptions": ["Resource assessment must include a scenario key."]}
        resource = resource_assessment.drop_duplicates("scenario", keep="last").copy()
        if "resource_feasible" in resource:
            resource["resource_assessment_status"] = resource["resource_feasible"].map(
                lambda v: "FEASIBLE" if bool(v) else "RESOURCE CONSTRAINT"
            )
        elif "overloaded_resource_days" in resource:
            overload = pd.to_numeric(resource["overloaded_resource_days"], errors="coerce")
            resource["resource_assessment_status"] = np.where(overload.eq(0), "NO OVERLOAD REPORTED", "RESOURCE CONSTRAINT")
        else:
            resource["resource_assessment_status"] = "ASSESSED — FEASIBILITY NOT CLASSIFIED"
        if "resource_shortfall" not in resource:
            resource["resource_shortfall"] = np.nan
        if "resource_notes" not in resource:
            resource["resource_notes"] = "See resource assessment source."
        resource = resource.rename(columns={
            "resource_assessment_status": "_incoming_resource_status",
            "resource_shortfall": "_incoming_resource_shortfall",
            "resource_notes": "_incoming_resource_notes",
        })
        result = result.merge(
            resource[["scenario", "_incoming_resource_status", "_incoming_resource_shortfall", "_incoming_resource_notes"]],
            on="scenario", how="left",
        )
        result["resource_assessment_status"] = result["_incoming_resource_status"].fillna(result["resource_assessment_status"])
        result["resource_shortfall"] = result["_incoming_resource_shortfall"].combine_first(result["resource_shortfall"])
        result["resource_notes"] = result["_incoming_resource_notes"].fillna(result["resource_notes"])
        result = result.drop(columns=["_incoming_resource_status", "_incoming_resource_shortfall", "_incoming_resource_notes"])

    result["risk_assessment_status"] = "NOT ASSESSED"
    result["baseline_expected_risk_cost"] = np.nan
    result["residual_expected_risk_cost"] = np.nan
    result["risk_cost_change"] = np.nan
    result["baseline_expected_risk_days"] = np.nan
    result["residual_expected_risk_days"] = np.nan
    result["risk_days_change"] = np.nan
    if isinstance(risk_assessment, pd.DataFrame) and not risk_assessment.empty:
        if "scenario" not in risk_assessment.columns:
            return {"available": False, "comparison": empty,
                    "assumptions": ["Risk assessment must include a scenario key."]}
        risk = risk_assessment.drop_duplicates("scenario", keep="last").copy()
        pairs = [
            ("baseline_expected_risk_cost", "residual_expected_risk_cost", "risk_cost_change"),
            ("baseline_expected_risk_days", "residual_expected_risk_days", "risk_days_change"),
        ]
        for base, residual, delta in pairs:
            if base in risk and residual in risk:
                risk[base] = pd.to_numeric(risk[base], errors="coerce")
                risk[residual] = pd.to_numeric(risk[residual], errors="coerce")
                risk[delta] = risk[residual] - risk[base]
        risk_fields = ["scenario"] + [c for pair in pairs for c in pair if c in risk]
        result = result.merge(risk[risk_fields], on="scenario", how="left", suffixes=("", "_risk"))
        for base, residual, delta in pairs:
            for field in (base, residual, delta):
                risk_field = field + "_risk"
                if risk_field in result:
                    result[field] = result[risk_field].combine_first(result[field])
                    result = result.drop(columns=[risk_field])
        if "residual_expected_risk_cost" in risk and "baseline_expected_risk_cost" in risk:
            result["risk_assessment_status"] = np.where(
                result["risk_cost_change"].notna(), "QUANTIFIED — scenario-linked expected cost exposure",
                result["risk_assessment_status"],
            )
        if "residual_expected_risk_days" in risk and "baseline_expected_risk_days" in risk:
            result["risk_assessment_status"] = np.where(
                result["risk_days_change"].notna(), "QUANTIFIED — scenario-linked expected schedule exposure",
                result["risk_assessment_status"],
            )
    result["overall_review_status"] = np.where(~result["feasible"], "REJECT — schedule scenario infeasible",
        np.where(result["resource_assessment_status"].eq("RESOURCE CONSTRAINT"),
                 "HOLD — resource feasibility issue",
                 np.where(result["resource_assessment_status"].eq("NOT ASSESSED"),
                          "CONDITIONAL — resource review required", "REVIEW — governance approval required")))
    result = result.sort_values(["feasible", "cost_per_day_saved"], ascending=[False, True], na_position="last")
    assumptions = [
        "Schedule duration and incremental cost come from the supplied schedule scenario model.",
        "Resource feasibility is considered only when a scenario-linked resource assessment is supplied; missing assessment is NOT ASSESSED.",
        "Risk exposure changes are shown only when baseline and residual expected exposure are explicitly supplied per scenario.",
        "Expected risk exposure is not deducted from recovery cost and is not treated as guaranteed savings.",
        "Resource units, currencies, productivity, safety, quality and contract constraints must be validated by their source models and responsible disciplines.",
        "No scenario is approved or applied automatically; the output is a decision-support comparison.",
    ]
    return {"available": True, "comparison": result.reset_index(drop=True), "assumptions": assumptions}
