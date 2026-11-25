# EVM Source Record Modes

Project Workspace reads PV and EV from the `progress` dataset, AC from `actual_cost`, and BAC from Project Master.

Project Master may include these optional fields:

- `progress_record_mode`
- `actual_cost_record_mode`

Each field accepts:

- `period_delta` — default. Rows are period movements and are summed through the reporting cutoff.
- `cumulative_snapshot` — rows are cumulative snapshots. Only the latest period for each identifiable activity/BOQ or cost identity is selected before aggregation.

Example Project Master configuration for cumulative imports:

```json
{
  "project_id": "PRJ-001",
  "progress_record_mode": "cumulative_snapshot",
  "actual_cost_record_mode": "cumulative_snapshot"
}
```

Use the mode that matches the source export. Do not select snapshot mode for additive transactions or delta mode for cumulative-to-date exports; doing so can double-count or understate EVM.

Snapshot mode requires a nonblank `period` in every row. Progress identity is activity + BOQ when both are present, otherwise activity identity is used. Actual-cost identity uses available transaction/cost identifiers. If the source does not provide stable identity fields, review the import mapping before relying on the result.

The workspace displays the configured modes beside EVM metrics. Missing values remain unavailable; the system does not silently convert missing PV, EV, AC, or BAC to zero.


## Progress detail level and BOQ identity

Progress can be recorded at either of two levels for one activity and period:

- Activity total: one progress row without `boq_id`.
- BOQ detail: one row per `boq_id` for that activity and period.

Do not mix these two levels for the same activity and period. The workspace rejects mixed activity-total and BOQ-detail rows because adding both would double-count PV/EV. When BOQ-detail rows are used, each activity + BOQ + period combination must be unique. Project Workspace stores and aggregates those BOQ rows independently.
