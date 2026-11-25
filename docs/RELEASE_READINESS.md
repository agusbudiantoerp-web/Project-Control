# Release Readiness — AI Project Control

## Implemented scope on `ai-project-control-integration`

- Streamlit application entry point and dependency manifest
- Project workspace, import/data quality and workspace persistence modules
- Portfolio command center, portfolio snapshot monitoring, portfolio-wide risk aggregation by currency, shared-resource conflict checks, currency-safe portfolio cost/cashflow analysis, COO executive decision brief and recovery intelligence
- EVM, schedule, cost, resource and risk analytics
- Monte Carlo schedule/cost risk engines, combined marginal executive outlook and risk exposure matrix
- Recovery scenario planning, resource recovery estimate and executive decision brief
- Executive action register with risk-ID links, audit events and escalation
- Persistent risk mitigation tracker with residual exposure, owner/due date, evidence gate and append-only change history
- Cross-register risk governance view linking risks, executive actions and mitigation status
- Executive reporting and Telegram reporting integration modules
- Historical KPI snapshot storage and next-snapshot CSV dataset builder
- Chronological Random Forest KPI baseline training/evaluation with persistence benchmark
- Trend-based early warning using saved historical KPI snapshots
- User guide, README, local-data ignore rules and focused CI workflow

## Deliberately not represented as complete

- No live connection to an owner's production ERP, scheduling system, accounting ledger or equipment telemetry has been verified.
- No trained or validated machine-learning model is claimed. Current KPI early warning is linear trend extrapolation.
- No authenticated multi-user role/permission layer is claimed.
- No production database, backup/restore drill, disaster recovery or secrets deployment has been verified.
- No automatic approval, baseline change, dispatch, procurement or Telegram delivery is performed without configured credentials and explicit operations.
- No system-wide test result is claimed before the planned test phase.

## Final test phase — execute only after implementation freeze

1. Verify branch head, file inventory and dependency installation.
2. Run Python compile check for all application modules.
3. Run every focused unit test and resolve missing test paths/dependencies.
4. Run the complete test suite and inspect failures; do not treat skipped tests as passes.
5. Smoke-test `streamlit run app.py` from a clean Windows environment.
6. Exercise import, workspace persistence, EVM, CPM, cost, resource, risk, Monte Carlo, recovery, history and report export with controlled fixtures.
7. Verify SQLite backup/restore and duplicate/idempotency behavior.
8. Verify secrets are absent from tracked files and logs.
9. Review access control and deployment architecture before any multi-user/production release.
10. Record actual GitHub Actions run IDs, statuses and test evidence before declaring release readiness.

## Release gate

The system is not production-ready until the final test phase passes, critical defects are resolved, deployment security is reviewed, and project owners accept the outputs against known reference cases.


## Dated cash flow forecast addition

- Dated actual and forecast transaction input with unique transaction IDs.
- Opening cash balance required per currency; currencies are never combined or converted implicitly.
- Daily running balance, monthly flow summary and projected negative-balance date flags.
- This remains a user-supplied transaction forecast, not a bank-confirmed balance or an inferred payment prediction.
- Add clean-environment UI smoke testing and source-data reconciliation to the final release test evidence.


## EVM and cost control page addition

- Standalone Streamlit page connects source-record EVM calculations to CPI, budget-rate and CPI×SPI EAC scenarios.
- Missing/invalid source values remain unassessed; project currency is shown explicitly.
- Verify period semantics (delta versus cumulative snapshot), reference cases, zero/negative edge cases and Streamlit UI behavior in final test phase.
- Forecast scenarios are not approved budgets, cash-flow forecasts or commitments.


## Telegram report page addition

- Streamlit page composes a report from supplied JSON and requires explicit confirmation before external send.
- Bot token/chat ID are read from secrets or environment variables; UI errors avoid displaying exception text that could contain credential-bearing URLs.
- Live bot credential setup, private-chat delivery, group permissions, rate limits and retry behavior must be verified during the integration test phase.


## Local operator guide

- Added Windows local installation instructions for Python 3.11, venv, requirements and Streamlit startup.
- Added optional Telegram environment-variable guidance and local SQLite data-handling cautions.
- Local startup instructions do not establish successful execution, deployment readiness or multi-user security. Those require the final acceptance test phase.


## Persisted financial workspace integration

- Added a read-only service that loads one project from the local SQLite workspace and builds EVM plus cost forecast scenarios.
- Added a Streamlit page that uses saved records rather than unrelated manually pasted JSON.
- Explicit cost/progress row currency mismatches are rejected against Project Master currency.
- Unit tests were added to focused CI; execution status must be checked in the final test phase.
- Period delta versus cumulative snapshot semantics remain a data-owner responsibility and must be reconciled before operational use.


## Saved financial-control report exports

- Saved project financial-control page now offers PDF, XLSX and JSON downloads from the same calculated result.
- Verify PDF rendering, workbook readability, special characters, large reports and output consistency during the final test phase.
- Exports are unsigned decision-support documents; approval/signature workflow is not implemented by this export feature.


## Saved portfolio COO cockpit

- Added project discovery from the local SQLite workspace and a read-only portfolio calculation service.
- Added per-project EVM status, RED/AMBER/INSUFFICIENT_DATA scorecard, currency-separated BAC summary, project details and bilingual report exports.
- Added tests to focused CI; execution and UI behavior remain unverified until final testing.
- Cockpit is limited to one local SQLite workspace; shared multi-user persistence, authentication, authorization, audit identity and server backup remain deployment blockers.


## Workspace backup and import history

- Added consistent SQLite online-backup snapshot utility and project-scoped import history page.
- Added restoration-oriented tests to focused CI; execution status remains pending verification.
- Automatic backup scheduling, encryption-at-rest for exported backup files, retention, restore UI and disaster-recovery drills are not implemented.
- Operators must protect backup files as sensitive project data.


## Risk governance in saved COO cockpit

- Saved portfolio service now loads the risk register, linked executive actions and mitigation tracker for each project.
- COO page shows risk governance counts, risk-by-risk action/mitigation status, risk exposure ranking and activity/WBS traceability.
- Integration tests added for a linked schedule risk, overdue action and mitigation; execution remains pending.
- Risk matrix assumes consistent impact units within a project. Identity/authentication, authorization, cross-project risk acceptance and formal approval workflows remain outstanding.


## Dated portfolio health monitoring

- Added `portfolio_snapshots` as a persisted, project/date-keyed dataset.
- Saved COO report and page compare the latest two distinct snapshots, expose missing baselines and data conflicts, and include trend summaries in executive output.
- Tests cover dated trend integration and missing baseline handling; execution remains pending.
- Trend output depends on users capturing dated snapshots over time. It does not reconstruct historical EVM or infer missing values.


- Added import-column aliases for portfolio snapshots in English and Indonesian.
- Added validation for ISO snapshot dates, non-negative SPI/CPI and risk score range 0–100.
- Added mapping/validation tests to the focused suite; execution remains unverified.


## Cross-project resource intelligence

- Saved COO report now joins resource records across projects and exposes shared-capacity conflicts.
- A conflict is asserted only for exact resource ID, period, unit and capacity agreement across at least two projects.
- Added service-level integration test for a 20-unit shared-resource overload; test execution remains pending.
- Resource IDs must be confirmed as the same physical pool by the project organization before action.


## Integrated schedule and cost outlook

- Saved portfolio service now computes the existing EVM cost scenarios and activity finish-date assessment for each project when an explicit `as_of_date` is supplied.
- COO cockpit exposes cost scenarios, delayed activities, schedule finish dates and missing evidence.
- Without an as-of date, the outlook is explicitly `NOT_RUN`; missing inputs are not inferred.
- Added tests for an assessed schedule/cost case and the required as-of date. Execution remains pending.


## Project resource loading integration

- Saved portfolio service now calls the existing resource loading summary for each saved project.
- COO cockpit displays resource/period utilization, overload counts and unassessed counts.
- Added integration tests for overload and missing capacity; execution remains pending.
- Per-project resource loading does not substitute for a fully levelled cross-project schedule or resource-constrained critical path.


## Portfolio financial position

- Saved portfolio service now aggregates supplied project BAC (or BOQ amount fallback) and actual-cost records into currency-separated financial position.
- COO cockpit shows assessed/unassessed projects, projects above budget, and per-currency totals.
- Projects without actual-cost evidence remain unassessed; this view is explicitly not a dated cash forecast.
- Added integration tests for currency separation and missing actual-cost evidence; execution remains pending.


## COO decision brief integration

- Saved portfolio service now derives Project Director priority rows from available EVM, recorded risk score, dated delay and resource loading evidence.
- COO decision brief consolidates portfolio review flags, cross-project resource conflicts, currency-separated exposure and action register summary.
- COO cockpit displays project review queues and recommendations.
- Added tests for priority flags and project-isolated missing EVM evidence; execution remains pending.
- The decision brief is not an ML probability forecast and does not approve recovery actions, spending, staffing or baseline changes.


## Predictive early warning and recovery review

- Portfolio service now runs dated trend extrapolation from stored `portfolio_snapshots`; duplicate/invalid snapshot history is returned as REVIEW_REQUIRED rather than silently forecast.
- Recovery decision review combines project EVM and risk matrix evidence and lists missing Monte Carlo, scenario-comparison and resource-recovery inputs.
- COO cockpit exposes trend metric statuses and per-project recovery signals/recommendations.
- Added integration tests for minimum three-snapshot history, duplicate dates, and partial recovery inputs; execution remains pending.
- Linear extrapolation is a transparent trend screen, not ML or a calibrated failure probability.


## CI manifest audit

- Audited all 54 test paths originally listed in the focused workflow against the integration branch.
- Found one nonexistent path (`tests/test_integrated_forecast.py`) and removed that reference so pytest is not asked to collect a missing file.
- The associated `ai_project_control/integrated_forecast.py` module imports `core`, which was not found at the repository root during this audit; this module remains an isolated dependency issue to resolve before claiming full repository readiness.
- The remaining workflow test paths were checked and found in the branch. This is a file-existence audit only; no test execution is implied.

## CI evidence update — 2026-11-24

Latest verified integration-branch evidence:

- Focused tests on commit `900b22a9de41ef5cb8543791e63492671d59c073`: **326 passed, 10 warnings**. Run: https://github.com/agusbudiantoerp-web/Project-Control/actions/runs/45388268910
- Recovery tests on the same commit: **40 passed**. Run: https://github.com/agusbudiantoerp-web/Project-Control/actions/runs/45388269115
- Automated tests on code commit `b94103fd`: passed. Run: https://github.com/agusbudiantoerp-web/Project-Control/actions/runs/45386542598
- AI Project Control CI on code commit `b94103fd`: passed. Run: https://github.com/agusbudiantoerp-web/Project-Control/actions/runs/45386542636

The only change between `b94103fd` and `900b22a` was a correction to the recovery CPI test expectation (CPI increases from 0.70 to 0.95 when EV rises from 70 to 95 with AC fixed at 100). Therefore the application code covered by the two broader successful workflows is unchanged at `900b22a`; nevertheless, all four workflow families have not yet been executed successfully on one identical commit SHA.

This evidence is **not** a production release sign-off. No clean Windows installation, representative owner-data acceptance, live Telegram delivery, authenticated multi-user deployment, or disaster-recovery drill has been verified. Branch comparison remains divergent: integration branch is 729 commits ahead of and 13 commits behind `main`. Do not merge automatically; review the 13 main-only commits and the resulting file-level differences first.

## Branch reconciliation audit — 2026-11-24 (20:36 UTC+8)

Verified branch comparison:
- Integration head: `4ba4c0e716319a6a2f21beea95df999cb6f86dc9`.
- Main head: `0423b83f377d67c5c2682e125d2bf9ab923623cb`.
- Branches are divergent: integration is 733 commits ahead and 13 commits behind main.
- No open pull request was returned by the repository PR search at the time of this audit.

File-level comparison of the 13 main-only commits:
- `tests/test_coo_portfolio_decision_brief.py` is identical on both branches.
- `tests/test_project_store.py` is identical on both branches.
- `ai_project_control/streamlit_workspace_dashboard.py` differs substantially: integration has the larger workspace implementation (80,194 characters versus 3,208 on main). Do not replace it with main's version.
- `ai_project_control/executive_reporting.py`, `ai_project_control/streamlit_persistent_import_ui.py`, `tests/test_import_service.py`, and the focused workflow differ. Integration versions contain additional report metrics, import safeguards/tests, broader test coverage and dependency installation. These differences require semantic review; they are not safe candidates for blind overwrite.
- Main contains a short focused workflow with a narrower test list; integration contains the broader test list and installs both root and app dependencies.

Decision:
- Do not merge or reset either branch automatically. Preserve the integration branch's larger dashboard and broader test workflow.
- The 13 main-only commits have not been fully replayed or semantically merged. This audit identifies overlap and risk but is not a completed reconciliation.
- Latest combined status query for commit `4ba4c0e716319a6a2f21beea95df999cb6f86dc9` returned no status entries; this is not evidence of passing CI.
- Latest main commit `0423b83f377d67c5c2682e125d2bf9ab923623cb` adds a COO portfolio decision brief test; that test file is identical on both branches.

Release gate remains closed: no final same-SHA success evidence for all workflow families, clean Windows installation, full UI acceptance, live Telegram delivery, authenticated multi-user deployment, or disaster-recovery drill has been verified.

## Follow-up verification — 2026-11-24

A fresh compare after the audit documentation commit reports:
- Integration branch is **734 commits ahead** and **13 commits behind** `main`; status remains `diverged`.
- The audit document update is commit `aeddc0b5f863f5613a50d6eb4f19cd4c3f7c0d03`.
- Combined commit status for `aeddc0b5f863f5613a50d6eb4f19cd4c3f7c0d03` returned an empty status list. This means no status evidence was returned; it does not mean checks passed.
- The previously recorded CI successes remain tied to their stated older SHAs. They must not be represented as results for this documentation commit.
- The branch comparison remains a full-history divergence from merge base `86851692422f3615f933d005a184028bce2ea14f`. The 13 main-only commits still require a controlled semantic reconciliation; no merge, rebase, or cherry-pick was performed in this audit.

Release decision: **NOT READY**. Keep `main` unchanged. Before integration, obtain current CI results for one candidate SHA, reconcile the 13 main-only commits with targeted tests for import/report/dashboard behavior, and complete Windows/runtime acceptance.

## Targeted code-contract review — 2026-11-24

Compared the following files on `main` and `ai-project-control-integration`:

### Import service
- `ai_project_control/import_service.py` does not exist at the root of `main`; it exists on the integration branch.
- Integration implementation rewinds seekable upload streams before parsing, validates project scope, and only persists after mapping/validation. Its test suite includes the preview-read/rewind regression case.
- The corresponding `tests/test_import_service.py` on `main` lacks the stream-rewind regression test; integration has it.
- Keep the integration implementation and its regression test. There is no main-side implementation to merge for this path.

### Executive reporting
- `main` version SHA: `703daacc884e58a30c9974ed06c585c2694fad9a`.
- Integration version SHA: `3e7b430f04ef2bc334631d9be8eaef06403acda3`.
- Integration adds P80 schedule-risk exposure and corresponding management-attention logic. Main does not expose that metric.
- Integration currently emits some bilingual labels redundantly in Indonesian mode (for example English and Indonesian schedule/risk labels, and repeated CPI-unavailable wording). This is a real report-quality issue to address with a targeted regression test and a cleanup that preserves the additional P80 metric; do not replace the integration file with main's older version.

### Focused workflow
- Main workflow SHA: `d34d4da395032d4b3fd19bb7d51bb9994c4f595e`.
- Integration workflow SHA: `81e709f0c81c91c7925bc8ce62bdbf416e968470`.
- Integration runs a broader test set and installs root plus app requirements.
- Main workflow runs a narrower list and includes malformed trailing continuation escapes in the shell command. Keep integration workflow; do not copy main workflow.

### Current branch and release gate
- Latest branch compare: integration is 735 commits ahead and 13 commits behind main; status `diverged`.
- No open pull request was returned by the latest PR search.
- No merge/rebase/cherry-pick was performed. The 13 main-only commits are not yet fully reconciled.
- Release remains NOT READY pending cleanup of bilingual report duplication, fresh all-workflow CI on one exact candidate SHA, Windows installation/runtime acceptance, owner-data acceptance, Telegram delivery test, and backup/restore drill.

## Executive report bilingual cleanup — 2026-11-24

- Updated `ai_project_control/executive_reporting.py` in commit `d7c08799d9ee357545827f60a2d9a1ed35c76e31`.
- Removed English-only duplicate schedule/CPI lines from Indonesian reports.
- Made cost P80, schedule P80 and overloaded-resource labels language-selective rather than emitting both English and Indonesian variants.
- Preserved P80 metrics and their underlying calculations.
- This is a code change committed to the integration branch; no test result is claimed yet. A fresh CI result for this exact SHA is required.
- Release remains NOT READY until report-language regression tests, all workflow families on one candidate SHA, Windows acceptance, and the outstanding 13-commit branch reconciliation are completed.

## Bilingual report regression tests — 2026-11-24

- Added Indonesian and English regression cases in `ai_project_control/tests/test_executive_reporting.py`.
- Indonesian assertions require Indonesian SPI/CPI, P80 cost, P80 schedule and resource-overload labels and reject English duplicates.
- English assertions require English labels and reject Indonesian duplicates.
- Existing source-aware tests remain unchanged and continue checking that missing metrics are not invented.
- Test commit: `e4055637c6cd15b7cb7571999ba1470ba312ff2e`.
- CI status lookup for this SHA returned an empty status list; no pass is claimed. The AI Project Control CI workflow watches `ai_project_control/**`, so this test change is in its configured push path.
- Branch compare after the test commit: integration is 739 commits ahead and 13 behind `main`; status remains diverged.
- Release remains NOT READY until the regression suite and all required workflow families pass on one candidate SHA, and Windows/runtime acceptance and branch reconciliation are complete.

## Report header localization regression — 2026-11-24

- Updated `ai_project_control/executive_reporting.py` in commit `8b00066d4bf2a81994819aba612df6b5dc559315`: Indonesian reports now label project and reporting date as `Proyek` and `Tanggal pelaporan`; English reports retain `Project` and `Status date`.
- Added regression assertions for both languages in `ai_project_control/tests/test_executive_reporting.py`, commit `e686a8ba6838c13fa894e49a318a60d8db19919c`.
- Combined status queries for both commits returned empty status arrays. No CI pass is claimed.
- Current branch compare: integration is 744 commits ahead and 13 behind `main`, still diverged.
- Release remains NOT READY. Run targeted tests and all workflow families on one exact candidate SHA before release.

## Test contract correction — 2026-11-24

- Reviewed the bilingual executive report regression suite and found the original English-label assertions invoked the report builder without an explicit language, while its default is Indonesian.
- Updated the English metrics test and missing-metrics test to pass `language="en"` explicitly. Indonesian tests continue to pass `language="id"`.
- Test update commit: `e5e05e73548f81a42710b4368c35d7aab155a115`.
- Combined status lookup for this SHA returned an empty list. No CI success is claimed.
- Current branch comparison: integration is 746 commits ahead and 13 behind `main`, status `diverged`.
- Release remains NOT READY pending CI on a single candidate SHA, full branch reconciliation, and Windows/runtime acceptance.


## Additional implementation hardening — 2026-11-25

- Upload reader now validates trimmed, case-insensitive unique headers and rejects malformed CSV rows with surplus values before data is accepted.
- ProjectStore now closes operation connections, supports explicit in-memory database cleanup, and refuses databases with a newer schema version.
- EVM, CPM, schedule-risk, risk-cost, risk-exposure and resource-loading inputs reject booleans where numeric values are required; invalid or overflowing aggregates are not published as valid metrics.
- Dashboard metric formatting now renders non-finite values as unavailable rather than displaying "nan".
- Portfolio cash-flow aggregation no longer converts missing BOQ/actual-cost values to zero and rejects explicit row currencies that conflict with Project Master.
- Added regression tests for these cases and included the new test files in the focused workflow manifest.
- Added one root Windows launcher for the documented root Streamlit application; the historical nested launcher delegates to it.
- These are implementation and test-coverage additions only. They have not yet been executed as a final test run on one commit SHA.


## Advanced source intake and unified primary storage — 2026-11-25

- Added Primavera P6 XER parsing with explicit source-project selection for multi-project files.
- Added atomic multi-dataset SQLite commits so Project Master, WBS and Activities are saved together or rolled back together.
- Added a primary-workspace XER import page with preview, Upsert/Replace choice and an explicit destructive-replacement confirmation.
- Added PDF drawing-page preview and Gemini draft takeoff. Transmission requires explicit consent; every row remains PENDING_REVIEW until a quantity surveyor verifies it. Saved BOQ quantity is retained while unit rate and amount remain blank.
- Centralized the primary SQLite path across root app, import page, financial page, COO cockpit, backup page and advanced intake page via `PROJECT_CONTROL_DB`.
- Added PyMuPDF dependency and optional `GEMINI_API_KEY` configuration example.
- The historical V1 launcher remains separate for compatibility and uses `%LOCALAPPDATA%\\AIProjectControl\\project_control.db`; it is not synchronized with the primary workspace. The root launcher is the primary workspace entry point.
- Added focused tests for XER parsing, multi-project scoping, atomic workspace import and Gemini input validation. These tests have not yet been executed.


## Engineering audit update — 2026-11-25 (integration branch)

Additional defensive changes recorded during the implementation audit:

- CSV/Excel upload headers are validated before row processing. Blank headers, duplicate headers after whitespace/case normalization, and excessive column counts are rejected. CSV rows containing more values than the header are rejected instead of silently dropping overflow values.
- Focused CI explicitly includes the Telegram notification regression tests, including token-redaction behavior.
- SQLite project storage closes per-operation connections after transaction completion, retains a shared in-memory database for the lifetime of an in-memory store, and refuses to open a database whose recorded schema version is newer than the application.
- Dashboard EVM forecasts treat zero CPI and invalid/non-positive BAC as unassessed rather than dividing by zero or publishing unsupported forecasts. Non-finite ratio/percentage outputs are suppressed.
- The EVM engine requires positive BAC before issuing EAC/VAC forecasts and records the data gap.
- Cost forecast allows a valid zero actual-cost input: the budget-rate scenario remains available, while CPI-based scenarios are unassessed because CPI cannot be calculated from zero AC.
- Dated cash-flow validation rejects boolean/non-numeric opening balances and boolean transaction amounts, and guards daily/monthly aggregation and running balances against numeric overflow.
- Regression tests were added for the above edge cases and the focused workflow includes the new dashboard EVM regression test.

### Verification boundary

The implementation files were re-read through the repository API. GitHub Actions completed the focused project-control suite successfully on the latest branch SHA 1704ba5: **469 passed, zero warnings**. The suite includes smoke tests for the repository-root Streamlit app, the P6/drawing intake page, and the backup/restore page. The recovery test workflow completed successfully on the same SHA. The AI Project Control CI and automated module tests completed successfully on SHA e8e1948 using the updated Node 24-compatible GitHub Actions releases. Remaining acceptance checks are a real-project end-to-end walkthrough and local Windows launch/restore on the operator's machine.

### Integration boundary

The integration branch remains divergent from main. Main-only commits and file-level differences must be reconciled deliberately; do not merge, reset or overwrite the larger integrated application with main as a shortcut. Local SQLite remains a single-user/local-first store, not a production multi-user database. Monte Carlo cost and schedule percentiles remain separate marginal distributions, not a correlated joint forecast.


## Telegram inbound drawing PDF

- Added explicit `getUpdates` polling for PDF documents from one configured chat ID, with update offset, file-size limit, PDF signature check and safe generic errors.
- PDF bytes are held in Streamlit session state only; the selected page is sent to Gemini only after a separate consent checkbox and Analyze action.
- Polling requires no active Telegram webhook. The same token/chat configuration supports outbound executive reports and inbound PDF intake.
- Tests cover authorized-chat filtering, offset handling, PDF signature validation and credential validation. Not yet executed.


## Implementation checkpoint — 2026-11-25 (pre-test freeze candidate)

### Integrated primary workflows

- The root Streamlit application remains the primary workspace entry point. The historical V1 launcher is preserved for compatibility and is explicitly documented as a separate, unsynchronized local database.
- Added a primary-workspace Primavera P6 XER intake page. It scopes multi-project XER files explicitly, validates activity IDs, WBS parent links, dependency cycles, relationship types and non-zero lags, then atomically saves Project Master, WBS and Activities.
- Added drawing PDF page preview, explicit Telegram PDF polling from one configured chat, and Gemini draft takeoff. The PDF page is sent to Gemini only after separate explicit consent. BOQ rows remain pending review until a quantity surveyor marks them VERIFIED; unit rates and amounts are not fabricated.
- Added persistent Telegram update offsets in workspace metadata so restarting Streamlit does not replay old bot updates.
- Centralized the primary SQLite database path across root app, workspace import, financial control, COO cockpit, backup and advanced intake pages.
- Added atomic multi-dataset workspace writes and tests for rollback when a later dataset write fails.
- Hardened local SQLite connection lifecycles for ProjectStore, ActionRegisterStore and RiskMitigationStore, including shared in-memory database behavior.
- Added numeric-range protections across EVM, cost forecast, Monte Carlo schedule/cost, resource utilization and portfolio financial/risk aggregation.
- Hardened CSV/XLSX intake, destructive Replace confirmation, Telegram credential handling, and backup integrity verification.

### Current repository state

- Branch: `ai-project-control-integration`
- Compared with `main`: **941 commits ahead, 13 commits behind**; branch remains diverged.
- Open pull requests: none found.
- Combined status for the checked latest commit: no status entries returned. This is not a passing CI result.
- Focused workflow now compiles `app.py`, `ai_project_control` and `pages`, and is configured for pull requests targeting both the integration branch and `main`.
- New regression tests are included in the focused workflow for XER import, Telegram PDF intake, workspace configuration, atomic storage, import validation and numerical edge cases.

### Verification boundary — unchanged

Implementation changes have been committed and selected files/workflows have been re-read through the repository API. **No test suite has been executed in this implementation phase.** Do not describe the application as tested, production-ready or fully released until the planned test phase has completed. The branch divergence must also be reconciled deliberately; do not merge or reset it blindly.


### Drawing-to-BOQ intake hardening

- PDF drawing intake now rejects empty/invalid uploads, files over 50 MB, documents outside the 1–500 page range, invalid page indexes, and render zoom outside 0.25–4.0. PDF document handles are closed after each render; rendered page images are capped at 12 MB.
- Gemini drawing requests validate the model identifier, API key, and image size before sending. Provider response text is bounded to 1 MB and takeoff output is capped at 500 rows.
- Gemini takeoff values are treated as untrusted suggestions. Invalid, negative, boolean, or non-finite quantities are left blank; generated BOQ drafts have blank unit rates and amounts and remain marked **Pending Review**.
- These controls do not certify quantities. Drawing scale, measurement method, scope, units, WBS assignment, and every quantity still require professional review.


### Primary application entry point and local launch

- The repository-root app.py is the primary unified workspace and loads the shared ProjectStore through ai_project_control.streamlit_workspace_dashboard.
- The root Windows launcher now installs both requirements.txt and ai_project_control/requirements.txt before starting the root app. The PowerShell instructions in the root README use the same dependency set.
- ai_project_control/app.py and its nested launcher are retained as a historical V1 compatibility application. They use a separate local database and are not synchronized with the primary workspace; use the repository-root launcher for the current application.
- The primary P6 XER and drawing-to-BOQ workflow is the root pages/08_Primavera_XER_Drawing_BOQ_Intake.py page. Drawing PDF preview is bounded by a 20 MB / 300-page intake limit in the UI; rendered images are capped at 12 MB. Gemini transmission requires explicit page-specific consent. BOQ rows require a valid project WBS, explicit VERIFIED review status, quantity, description and unit before persistence.


### Primary workspace restore controls

- Workspace restore now validates the SQLite file header, integrity check, required ProjectStore tables and exact supported schema version before touching the active database.
- Restore creates a timestamped pre-restore SQLite safety snapshot when a current database exists, writes the candidate to the same filesystem, validates it again, and then replaces the active file atomically.
- The Backup & Audit page requires an explicit confirmation and warns operators to stop other processes writing to the local SQLite database during restore.
- Restore is limited to 200 MB and is not a migration tool; backups from a different or newer schema version are rejected. The workspace remains local-first and single-user.


### XLSX upload archive safety

- XLSX uploads are inspected as ZIP containers before openpyxl parses them. The reader rejects malformed workbooks, duplicate or unsafe archive paths, encrypted entries, excessive member counts, expansion above 100 MB, and compression ratios above the configured threshold.
- External workbook links are not retained, and defusedxml is installed for hardened XML parsing. CSV and XLSX data remain preview-only until mapping and validation are explicitly completed.


### Primavera XER parser bounds

- The XER parser now caps the source file at 30 MB, table count at 100, rows per table at 100,000, fields per table at 300, and individual line length at 1,000,000 characters.
- The parser rejects over-wide rows rather than silently dropping extra values. P6 import still supports only Finish-to-Start relationships in the primary intake path and converts P6 hours to nominal 8-hour days; calendars, lag, constraints, resource leveling and other relationship types require Primavera review.


### Telegram message-size handling

- Executive escalation messages are truncated using a UTF-16 code-unit budget below Telegram's 4,096-unit ceiling, preserving a safe suffix and avoiding a split surrogate pair.
- The transport adapter also validates the UTF-16 length before sending. Regression coverage includes emoji-heavy messages.


### Local workspace file permissions

- On POSIX systems, newly created workspace directories use owner-only permissions and SQLite database files are restricted to owner read/write (0700 directory, 0600 database).
- Pre-restore safety snapshots are also restricted to owner read/write. Windows ACLs remain governed by the local account and machine policy.


## Import workflow hardening — 2026-11-25

- XLSX imports expose an explicit worksheet selector when a workbook contains multiple sheets. The selected worksheet is passed through to the persistence service, so the saved data matches the preview.
- Column mapping rejects empty source-column names and reuse of one source column for multiple target fields. The Streamlit import form warns about missing required fields or reused columns and disables submission until corrected.
- Empty data uploads return EMPTY_DATASET without creating an import event or changing existing records, including when the operator selected Replace. This prevents a header-only workbook/CSV from clearing a populated dataset.
- Regression tests cover selected-sheet persistence, ambiguous/reused source mappings, and empty upload behavior for both upsert and replace modes.
- These are source-level implementation changes; the final test phase must execute the focused and complete suites and verify the Streamlit interaction.


## Restore destination privacy — 2026-11-25

- Restore now creates a missing workspace parent directory with restrictive POSIX permissions (0700). The restore database is staged using a private temporary file before atomic replacement.
- POSIX regression coverage asserts the restored directory is 0700 and the restored database is 0600.
- This does not replace host-level disk encryption, backups outside the machine, access control or a tested disaster-recovery procedure.


## Drawing takeoff and XER import safeguards — 2026-11-25

- Gemini takeoff response rows must be JSON objects. Nested/non-scalar text fields are rejected, and item code, discipline, description, unit, measurement method and assumptions have explicit character limits before they reach the review editor.
- Gemini request timeout is validated as a finite positive number, including oversized numeric input handling.
- Primavera XER import rejects duplicate WBS IDs.
- Replace mode refuses to clear a populated WBS dataset when the selected XER has no WBS rows; the import is stopped before the atomic save.
- Regression tests cover malformed Gemini rows, timeout edge cases, duplicate WBS IDs and safe XER Replace behavior.
- These are source changes and test additions only. CI execution and real Primavera/Gemini integration remain to be verified during the final test phase.
