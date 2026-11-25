# AI Project Control

Integrated Streamlit workspace for project execution control, portfolio governance, risk assessment, forecasting and recovery decision support.

## Scope

- Project workspace and structured dataset import/validation
- Primavera P6 XER import into the primary ProjectStore (WBS and Activities)
- PDF drawing-page takeoff drafts with Gemini, explicit data-sharing consent and quantity-surveyor verification before BOQ save
- BOQ, schedule, resource and manpower/equipment planning
- EVM performance review (SPI, CPI, EAC and related indicators)
- Cost and schedule forecasting, Monte Carlo risk assessment
- Combined marginal cost and schedule outlook with explicit non-correlation caveat
- Risk exposure matrix, WBS/activity traceability, persistent mitigation execution tracker, append-only mitigation change history and cross-register governance view
- Recovery scenario comparison and resource-based recovery estimates
- Executive action register with optional risk-ID links, audit events and escalation review
- Portfolio command center, snapshot monitoring, portfolio-wide risk aggregation by currency, cross-project shared-resource capacity checks, currency-safe portfolio cost/cashflow analysis, COO executive decision brief and executive reporting
- Historical KPI snapshot store, next-snapshot dataset export, chronological Random Forest baseline evaluation and trend-based early warning
- Telegram executive reporting and authorized-chat PDF document intake (requires explicit bot configuration and user action)

## Panduan

- [Panduan pengguna Bahasa Indonesia](docs/PANDUAN_PENGGUNA.md)
- [Release readiness dan rencana pengujian akhir](docs/RELEASE_READINESS.md)

## Requirements

- Python 3.11
- Dependencies listed in `requirements.txt`

## Run locally

Windows PowerShell (atau klik dua kali `START_AI_PROJECT_CONTROL.bat` dari folder repository):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

The primary application uses one shared SQLite workspace path across the root app and all primary pages. By default it is `.project_control/project_control.sqlite3`; set `PROJECT_CONTROL_DB` to override it consistently.

For Gemini drawing takeoff, set `GEMINI_API_KEY` securely as an environment variable or Streamlit secret. The selected PDF page is transmitted to Google only after the in-app consent checkbox and Analyze button are used. Never commit real API keys.

The historical V1 application remains available from `ai_project_control/START_AI_PROJECT_CONTROL.bat` for compatibility. It uses a separate database under `%LOCALAPPDATA%\\AIProjectControl\\project_control.db` and is not synchronized with the primary workspace. Use the root launcher for the primary unified workspace.
Keep this folder backed up. Do not commit live project data, credentials, exports or database files.

## Historical performance workflow

1. Open **Historical Project Performance & Dataset Builder**.
2. Save actual KPI snapshots using the project's reporting date and currency.
3. Use consistent KPI definitions and reporting cut-offs.
4. Build the next-snapshot dataset after at least two snapshots exist for a project.
5. Export CSV and review data completeness, currency consistency and time ordering.
6. Use project/time-based validation when training any future predictive model; do not randomly split adjacent observations.

The current early-warning engine is transparent linear trend extrapolation. It is not a trained ML model or a calibrated probability of project failure.

## Governance and deployment notes

- Decision support only: no automatic approval, baseline change, procurement, resource dispatch or contractual instruction.
- Validate CPM calendars, dependencies, critical path, resource availability, HSE, quality and workface constraints before acting on recovery estimates.
- Monte Carlo cost and schedule percentiles must not be treated as a joint correlated distribution unless a correlated model is implemented and validated.
- Local SQLite and actor-name fields do not provide authentication or multi-user authorization.
- For hosted multi-user use, configure authentication, role-based access, shared durable database, backups, secrets management, audit retention and operational monitoring first.
- Telegram integration requires bot token and destination configuration supplied securely through deployment secrets; never commit secrets.

## Tests

Focused tests are configured in `.github/workflows/project-control-focused-tests.yml`.
Run locally after installing requirements:

```powershell
python -m compileall -q app.py ai_project_control pages
python -m pytest -q
```

A green focused workflow is necessary but not sufficient for production readiness. Complete the integration, security, data migration, deployment and user acceptance checks before operational use.


## Dated cash flow forecast

Open the Streamlit page **Dated Cash Flow Forecast** from the sidebar. Supply reconciled opening cash by currency and dated transaction rows. Actual and forecast transactions remain separate; currencies are never silently converted. The forecast is a model from supplied transactions, not a bank balance or inferred payment prediction.


## Dated cash flow forecasting

The multipage Streamlit application includes **Dated Cash Flow Forecast**. Enter reconciled opening cash by currency and dated actual/forecast transactions to calculate daily running balances, monthly flow summaries and projected negative-balance dates. The engine keeps currencies separate and does not infer invoice payment dates, collections, financing or FX conversion. Its output is a scenario based on supplied inputs, not a bank-confirmed cash position.


## EVM and cost forecast control

Open the **EVM & Cost Forecast Control** page. Provide project BAC and currency, progress records with PV/EV, and actual cost records. The page calculates EVM indicators and three transparent EAC scenarios (CPI, budget-rate, and CPI×SPI). Missing inputs remain unassessed; scenarios are not approved budget revisions. Period records must use a consistent delta or snapshot convention as described by the EVM engine.


## Telegram executive report

Open **Telegram Executive Report** to compose a factual message from supplied portfolio intelligence and action-register JSON. Delivery is explicit and requires a reviewed confirmation checkbox plus `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` configured as deployment secrets or environment variables. The `.env.example` file contains blank placeholders only. Never commit real credentials. Telegram delivery has not been validated against a live bot in this repository review.


## Windows local installation

See [`docs/PANDUAN_INSTALASI_WINDOWS.md`](docs/PANDUAN_INSTALASI_WINDOWS.md) for Python 3.11 setup, virtual environment, dependency installation, local Streamlit startup, optional Telegram secrets and data-handling limitations.


## Saved Project Financial Control

Open **Saved Project Financial Control** after importing a project into the local Project Workspace. Enter its Project ID to calculate EVM and EAC scenarios from persisted progress and actual-cost records. The page is read-only and project-scoped. Explicit row currency mismatches are rejected; missing currency fields remain an assumption to review. See the user guide for period semantics and limitations.


The saved financial-control page can export the calculated project brief as PDF, Excel and JSON. The PDF/Excel outputs are generated from the same displayed report content; they are not signed or approved records.


## Saved Portfolio COO Executive Cockpit

Open **Saved Portfolio — COO Executive Cockpit** to discover projects saved in the local SQLite workspace, calculate each project's EVM indicators, review RED/AMBER/INSUFFICIENT_DATA states, compare budgets by currency without implicit FX conversion, and export an Indonesian or English executive report as PDF, XLSX or JSON. Only projects present in this local workspace are included; this is not a synchronized multi-user portfolio database.


## Workspace Backup & Import History

Open **Workspace Backup & Import History** to review the latest 100 import events for a selected project and prepare a consistent SQLite snapshot using SQLite's online backup API. Backups may contain sensitive commercial and project data: store them encrypted with restricted access and never commit them to a public repository. Restore procedures and backup retention remain organizational responsibilities.


The saved COO cockpit now joins the imported risk register with persisted executive actions and mitigation tracking. It displays risk exposure ranking, activity/WBS link status, overdue or blocked linked actions, mitigation coverage and residual exposure. Risk impact values must use consistent units within each project. Actor names remain attribution fields only; they do not authenticate users.


## Portfolio health trend monitoring

The COO cockpit can compare the latest two distinct dated `portfolio_snapshots` per project. Save records with `project_id`, `snapshot_date` (YYYY-MM-DD), and available `SPI`, `CPI`, and `risk_score` values. Missing metrics remain unavailable; a single snapshot is marked NO_BASELINE and duplicate project/date records are flagged as conflicts. Trend thresholds are screening indicators, not automated decisions.


The saved COO cockpit also reviews cross-project shared-resource demand. It flags overload only when resource ID, period, unit and declared capacity match across at least two projects. Confirm that identical resource IDs refer to the same real-world pool before acting on a flag. Monetary risk exposure is grouped by currency and is meaningful only when impact values are monetary amounts.


The COO cockpit can combine saved project EVM cost scenarios with explicit activity finish-date forecasts. Provide an as-of date to run it; the output separates schedule delay evidence from cost scenarios and never claims a probabilistic joint forecast.


The saved COO cockpit includes per-project resource loading and capacity alerts by resource ID, unit and period. Missing capacity or demand is shown as unassessed rather than treated as available capacity.


The COO portfolio view includes a currency-separated budget-versus-actual-cost position. Projects with missing actual-cost evidence are reported as unassessed, not as zero spend. This financial position is distinct from dated cash-flow forecasting.


The Saved Portfolio COO Cockpit includes a Project Director decision matrix and COO management-review brief derived from stored EVM, risk, dated schedule and resource evidence. Missing indicators remain unassessed; recommendations are review prompts, not automatic approvals.


The COO portfolio cockpit includes a dated snapshot trend-warning view and a recovery decision review. Trend forecasts require at least three dated observations per metric; missing Monte Carlo or recovery scenario evidence is explicitly surfaced as incomplete.


## Primavera P6 and drawing intake

Open **Primavera P6 XER & Drawing-to-BOQ Intake** from the sidebar. A selected XER project is imported atomically into Project Master, WBS and Activities. A selected PDF drawing page can be sent to Gemini for a quantity-takeoff draft only after explicit consent. Review and verify every quantity before saving it to BOQ; unit rates and amounts remain blank until supplied and approved.


### Telegram drawing intake

Send a PDF to the configured private bot chat as a Document, then use **Fetch latest Telegram PDF** on the drawing intake page. The bot token and allowed chat ID are read from environment variables or Streamlit secrets. The page polls with `getUpdates`, so an active webhook must be disabled for polling. Telegram PDF bytes stay in the Streamlit session; a selected page is sent to Gemini only after explicit consent.
