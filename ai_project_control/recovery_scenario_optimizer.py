"""Constraint-aware optimizer for explicitly costed schedule recovery scenarios."""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


def optimize_recovery_scenarios(
    scenarios: pd.DataFrame,
    budget_limit: float | None = None,
    minimum_days_saved: float = 0.0,
    maximum_cost_per_day: float | None = None,
) -> dict[str, Any]:
    """Filter, Pareto-rank and recommend verified recovery alternatives.

    Only scenarios marked feasible with finite non-negative costs and positive
    realized time savings can be economically recommended. No missing costs
    or schedule benefits are imputed.
    """
    empty = pd.DataFrame()
    if not isinstance(scenarios, pd.DataFrame) or scenarios.empty:
        return {"available": False, "eligible": empty, "pareto": empty,
                "recommended": None, "excluded": empty,
                "assumptions": ["No recovery scenario rows were supplied."]}
    required = {"scenario", "actual_days_saved", "incremental_cost", "feasible"}
    missing = required - set(scenarios.columns)
    if missing:
        return {"available": False, "eligible": empty, "pareto": empty,
                "recommended": None, "excluded": empty,
                "assumptions": ["Missing required columns: " + ", ".join(sorted(missing))]}
    if budget_limit is not None and (not np.isfinite(float(budget_limit)) or float(budget_limit) < 0):
        raise ValueError("budget_limit must be finite and non-negative.")
    if not np.isfinite(float(minimum_days_saved)) or float(minimum_days_saved) < 0:
        raise ValueError("minimum_days_saved must be finite and non-negative.")
    if maximum_cost_per_day is not None and (
        not np.isfinite(float(maximum_cost_per_day)) or float(maximum_cost_per_day) < 0
    ):
        raise ValueError("maximum_cost_per_day must be finite and non-negative.")

    data = scenarios.copy()
    data["actual_days_saved"] = pd.to_numeric(data["actual_days_saved"], errors="coerce")
    data["incremental_cost"] = pd.to_numeric(data["incremental_cost"], errors="coerce")
    data["feasible"] = data["feasible"].fillna(False).astype(bool)
    data["cost_per_day_saved"] = data["incremental_cost"] / data["actual_days_saved"].where(data["actual_days_saved"] > 0)
    data["exclusion_reason"] = ""
    data.loc[~data["feasible"], "exclusion_reason"] = "Schedule model marked scenario infeasible"
    invalid = (
        data["actual_days_saved"].isna() | ~np.isfinite(data["actual_days_saved"])
        | data["actual_days_saved"].le(0)
        | data["incremental_cost"].isna() | ~np.isfinite(data["incremental_cost"])
        | data["incremental_cost"].lt(0)
    )
    data.loc[invalid & data["exclusion_reason"].eq(""), "exclusion_reason"] = "Missing or invalid verified duration/cost"
    valid = data[data["exclusion_reason"].eq("")].copy()
    valid.loc[valid["actual_days_saved"] < float(minimum_days_saved), "exclusion_reason"] = "Below minimum days-saved target"
    if budget_limit is not None:
        valid.loc[valid["incremental_cost"] > float(budget_limit), "exclusion_reason"] = "Over budget limit"
    if maximum_cost_per_day is not None:
        valid.loc[valid["cost_per_day_saved"] > float(maximum_cost_per_day), "exclusion_reason"] = "Over maximum cost per day saved"
    eligible = valid[valid["exclusion_reason"].eq("")].copy()
    excluded = data[~data.index.isin(eligible.index)].copy()
    # Pareto-efficient options: no other option costs less and saves at least as many days.
    pareto_indices = []
    for idx, row in eligible.iterrows():
        dominated = (
            (eligible["incremental_cost"] <= row["incremental_cost"])
            & (eligible["actual_days_saved"] >= row["actual_days_saved"])
            & (
                (eligible["incremental_cost"] < row["incremental_cost"])
                | (eligible["actual_days_saved"] > row["actual_days_saved"])
            )
        ).any()
        if not dominated:
            pareto_indices.append(idx)
    pareto = eligible.loc[pareto_indices].sort_values(
        ["incremental_cost", "cost_per_day_saved", "actual_days_saved"],
        ascending=[True, True, False], kind="stable"
    ).reset_index(drop=True)
    ranked = eligible.sort_values(
        ["cost_per_day_saved", "incremental_cost", "actual_days_saved"],
        ascending=[True, True, False], kind="stable"
    ).reset_index(drop=True)
    if not ranked.empty:
        ranked.insert(0, "economic_rank", np.arange(1, len(ranked) + 1))
        recommended = ranked.iloc[0].to_dict()
        basis = "Lowest verified cost per day saved among alternatives that meet all user constraints."
    else:
        recommended = None
        basis = "No alternative meets the supplied constraints with verified feasible duration and cost."
    return {
        "available": True, "eligible": ranked, "pareto": pareto,
        "recommended": recommended, "excluded": excluded,
        "recommendation_basis": basis,
        "assumptions": [
            "Only feasible scenarios with positive realized days saved and finite non-negative incremental cost are ranked.",
            "Budget and cost-per-day constraints use the same project currency; no currency conversion is performed.",
            "Pareto options minimize incremental cost while maximizing realized days saved.",
            "The recommended option minimizes cost per day saved among options meeting all constraints; it is not automatically approved.",
            "Resource capacity, safety, quality, contract constraints and indirect costs remain separate validation gates unless explicitly modeled in the input scenario.",
            "Missing or invalid scenario metrics are excluded, not estimated.",
        ],
    }
