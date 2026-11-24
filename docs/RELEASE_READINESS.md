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
