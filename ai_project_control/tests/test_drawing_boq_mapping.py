import pandas as pd

from core import takeoff_to_boq_draft


def test_reviewed_drawing_takeoff_preserves_wbs_and_draft_values():
    takeoff = pd.DataFrame([
        {
            "drawing_id": "STRUCT-S01.pdf",
            "page": 2,
            "wbs_id": "1.2.3",
            "item_code": "CONC-01",
            "description": "Concrete footing",
            "unit": "m3",
            "quantity": 12.5,
            "confidence": "Medium",
            "review_status": "Reviewed",
        }
    ])

    draft = takeoff_to_boq_draft(takeoff)

    assert draft.loc[0, "wbs_id"] == "1.2.3"
    assert draft.loc[0, "item_code"] == "CONC-01"
    assert draft.loc[0, "budget_quantity"] == 12.5
    assert draft.loc[0, "unit_rate"] == ""
    assert draft.loc[0, "budget_amount"] == ""


def test_unassigned_takeoff_remains_unassigned_draft():
    takeoff = pd.DataFrame([
        {"item_code": "ITEM-01", "description": "Unmeasured item", "unit": "m",
         "quantity": None, "wbs_id": None}
    ])

    draft = takeoff_to_boq_draft(takeoff)

    assert draft.loc[0, "wbs_id"] == ""
    assert pd.isna(draft.loc[0, "budget_quantity"])
    assert draft.loc[0, "unit_rate"] == ""
