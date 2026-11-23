# AI Project Control

Integrated Streamlit workspace for project execution control, portfolio governance, risk assessment, forecasting and recovery decision support.

## Scope

- Project workspace and structured dataset import/validation
- BOQ, schedule, resource and manpower/equipment planning
- EVM performance review (SPI, CPI, EAC and related indicators)
- Cost and schedule forecasting, Monte Carlo risk assessment
- Combined marginal cost and schedule outlook with explicit non-correlation caveat
- Risk exposure matrix, WBS/activity traceability and mitigation review
- Recovery scenario comparison and resource-based recovery estimates
- Executive action register, audit events and escalation review
- Portfolio command center, snapshot monitoring and executive reporting
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
