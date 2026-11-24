# AI Project Control

Integrated Streamlit workspace for project execution control, portfolio governance, risk assessment, forecasting and recovery decision support.

## Scope

- Project workspace and structured dataset import/validation
- BOQ, schedule, resource and manpower/equipment planning
- EVM performance review (SPI, CPI, EAC and related indicators)
- Cost and schedule forecasting, Monte Carlo risk assessment
- Combined marginal cost and schedule outlook with explicit non-correlation caveat
- Risk exposure matrix, WBS/activity traceability, persistent mitigation execution tracker, append-only mitigation change history and cross-register governance view
- Recovery scenario comparison and resource-based recovery estimates
- Executive action register with optional risk-ID links, audit events and escalation review
- Portfolio command center, snapshot monitoring, portfolio-wide risk aggregation by currency, cross-project shared-resource capacity checks, currency-safe portfolio cost/cashflow analysis, COO executive decision brief and executive reporting
- Historical KPI snapshot store, next-snapshot dataset export, chronological Random Forest baseline evaluation and trend-based early warning
- Telegram executive reporting integration (requires explicit bot configuration)

## Panduan

- [Panduan pengguna Bahasa Indonesia](docs/PANDUAN_PENGGUNA.md)
- [Release readiness dan rencana pengujian akhir](docs/RELEASE_READINESS.md)

## Requirements

- Python 3.11
- Dependencies listed in `requirements.txt`

## Run locally

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

The default SQLite workspace is created at `.project_control/project_control.sqlite3`.
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
python -m compileall -q ai_project_control
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
