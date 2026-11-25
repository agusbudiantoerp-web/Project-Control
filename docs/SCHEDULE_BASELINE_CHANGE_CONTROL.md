# Schedule Baseline & Change Control

## Purpose

The Project Workspace supports a controlled schedule baseline workflow. A baseline is a saved snapshot of the activity schedule at a point in time. It is not silently rewritten when the working schedule changes.

## Workflow

1. Import and validate the project's WBS and activity schedule.
2. Open **Project Workspace** and select the project.
3. Under **Approved Schedule Baseline & Change Control**, capture the current schedule as a draft. Use a new, unique baseline ID for each snapshot.
4. Review the draft schedule snapshot. Approve it with the accountable approver's name.
5. The workspace compares the current activity schedule with the latest approved baseline and reports added, removed, and changed activities.
6. Raise a schedule change request against an approved baseline. Enter the description and estimated cost and schedule impacts.
7. A reviewer records an **APPROVED** or **REJECTED** decision with their name and written rationale.

## Governance rules

- Draft baselines are not used as the official comparison baseline.
- An approved baseline is not overwritten by the workspace capture workflow. A new baseline requires a new ID.
- A change request approval or rejection does not automatically alter the baseline, current schedule, budget, or contract.
- An approved change must be implemented in the relevant project datasets through the project's controlled update process. Capture a new baseline only when the authorized project governance process requires it.
- Change requests retain the baseline ID, decision maker, decision time, and rationale.
- The comparison checks activity identity, WBS, planned start/finish, duration, and predecessor fields. It does not independently resolve calendars, contractual entitlement, cost impacts, or resource feasibility.

## Data and deployment limitations

- Baselines and change requests are stored in the local Project Workspace SQLite database and are scoped by project ID.
- This local SQLite store is intended for a single-user workspace. It is not a multi-user server database and should not be exposed directly to the public internet.
- The workflow provides application-level decision records. It is not a substitute for a signed contract variation, formal document management, or an enterprise approval/signature service.
- Validate imported dates, calendars, working time, and project data dictionaries before relying on schedule variance reports.
