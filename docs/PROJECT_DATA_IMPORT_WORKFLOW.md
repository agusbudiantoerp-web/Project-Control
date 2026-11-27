# Project Data Import Workflow

## Recommended order

Import records in this order so cross-dataset references can be checked as the workspace is built:

1. Project Master — create the project ID and define currency and EVM record modes.
2. WBS — import WBS IDs and parent WBS IDs.
3. Activities — import activity IDs, WBS IDs, durations and predecessor IDs.
4. BOQ — include explicit WBS and activity IDs wherever the project data provides them.
5. Resources — include activity IDs when assignments are activity-specific.
6. Progress — use either activity-total rows or BOQ-detail rows for a given activity and period; never mix the two.
7. Actual Cost — include cost code and any available BOQ/WBS/activity references.
8. Risk, baseline and change-control records.

## Validation and persistence

- Column mapping is conservative. Ambiguous source columns require user review.
- Each uploaded dataset is validated before persistence.
- The candidate dataset is also checked against the existing project workspace before an import is committed.
- Atomic multi-dataset imports validate the proposed merged workspace, including existing project records, before writing.
- Invalid cross-project or cross-dataset links block the import. The import is not committed.
- Upsert updates/adds matching natural keys. Replace requires explicit confirmation in the Streamlit UI and replaces only the selected dataset.
- An empty upload never clears existing records.
- A project with existing inconsistent records may need those records corrected before a related import can pass cross-dataset validation.

## Identity rules

- WBS identity is project + WBS ID.
- Activity identity is project + activity ID.
- BOQ identity is project + BOQ ID.
- Progress identity is project + activity + period for activity-total records, or project + activity + BOQ + period for BOQ-detail records.
- Do not mix activity-total and BOQ-detail progress for the same activity and period; the workspace flags this to prevent EVM double counting.

## Operational review

A technically valid import does not prove that quantities, rates, calendars, productivity, earned-value rules or contractual classifications are correct. A project controls/QS reviewer must reconcile imported source documents and approve the reporting basis before using the dashboard for commercial or executive decisions.
