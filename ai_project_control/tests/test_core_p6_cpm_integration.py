import pandas as pd

from ai_project_control.core import calculate_cpm


def test_workspace_cpm_uses_imported_p6_ss_relationship_and_lag():
    activities = pd.DataFrame([
        {
            "activity_id": "A",
            "duration_days": 5,
            "predecessor_ids": "",
            "predecessor_relationships": [],
        },
        {
            "activity_id": "B",
            "duration_days": 4,
            "predecessor_ids": "A",
            "predecessor_relationships": [{
                "predecessor_id": "A",
                "relationship_type": "SS",
                "lag_days": 1,
            }],
        },
    ])

    result, stats = calculate_cpm(activities)
    by_id = result.set_index("activity_id")

    assert by_id.loc["B", "early_start_day"] == 1
    assert stats["project_duration"] == 5
    assert stats["n_activities"] == 2
