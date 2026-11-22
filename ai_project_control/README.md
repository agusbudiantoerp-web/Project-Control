# AI Project Control System — Integrated V1

Local-first Streamlit application consolidating compatible project-control capabilities from the source projects in this repository.

## Integrated features
- Project Data Hub: CSV / Excel templates, project-wide cross-dataset business validation, local SQLite persistence per project, and validated atomic ZIP backup / restore.
- Primavera P6 XER: PyP6Xer v2 object-model parser for projects, activities, WBS, relationships, resources, assignments, calendars and DCMA14; plus %T/%F/%R raw-table parser and conversion.
- CSV schedule CPM: forward/backward pass, early/late dates, total float, critical path and Gantt using pmcontrols.
- XER CPM: FS / SS / FF / SF relationships and lag on a calendar-free day scale.
- Full PyP6Xer DCMA14 schedule-quality analysis plus TPPSCI DCMA-style screening fallback.
- Cost & EVM: BAC, PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC, TCPI and earned-schedule ES / SV(t) / SPI(t) / IEAC(t) when baseline inputs support it.
- Progress quantities by activity / BOQ / reporting period, with weighted physical progress based on cumulative quantities against BOQ budget quantities.
- Resource, manpower and equipment assignments with planned daily load, capacity-overload screening, and a float-constrained resource-smoothing what-if that never overwrites baseline dates or activity logic.
- Milestone slippage and change-control impact (approved vs pending cost / schedule changes).
- Risk register exposure Monte Carlo and activity three-point PERT schedule Monte Carlo.
- Minimum-cost schedule crashing with scipy.optimize.linprog when approved crash assumptions are supplied.
- Executive Project Health dashboard with CPM critical activity count, SPI/CPI warning indicators and separate commitment exposure.
- Management-report integration: CPM activity detail, risk-adjusted P80 finish/cost metrics, forecast cash flow and mitigation action register are added to Excel/PDF report analysis when the underlying inputs are available.
- Rules-based mitigation action register for schedule, cost, risk and resource findings; recovery scenario cost, days saved and cost per day saved are shown only when crash duration and crash cost inputs are available and the target is feasible.
- Optional AI Project Advisor through Groq or Google Gemini; API keys are read from environment variables or Streamlit secrets (`GROQ_API_KEY`, `GEMINI_API_KEY`), sent only to the selected provider, and are not stored in SQLite. User explicitly initiates transmission.
- Trend-based completion and EAC projection from at least three valid progress reporting periods; clearly labelled as trend projection, not ML.
- PDF management report and optional Telegram document delivery; bot token and chat ID are not saved by the application.
- PDF drawing-to-BOQ draft extraction through Gemini vision, with editable takeoff review and BOQ draft export.
- Multi-sheet Excel workbook, PDF management report and optional Telegram document delivery.

## Source integration map
- PyP6Xer: LGPL-2.1-or-later library dependency for full P6 object-model parsing and DCMA14; not copied into this repository.
- pmcontrols-main/pmcontrols: integrated Python package copy for CPM, PERT / Monte Carlo, EVM / earned schedule primitives and schedule crashing; MIT.
- tppsci-project-controls-suite-master: XER record model, relationship-aware CPM concepts and DCMA / QSRA schedule-health methods; MIT. Python adapters are in core.py.
- project-controls-dashboard-main/src/metrics.py: adapted EVM performance indices and SPI finish forecast in dashboard_metrics.py; MIT.
- EVM_Project-main: reference-only workbook EVM workflow; not used as the authoritative calculation engine.

## Release readiness

This branch contains the integrated V1 application and automated deterministic-engine tests, including project-wide dataset validation and export/API-key security regressions. GitHub Actions is the source of truth for the latest test status. CI confirms the automated tests and module imports only; it does not replace end-to-end acceptance testing with representative Primavera XER, project BOQ, progress, cost, resource, and risk datasets. Do not treat the system as production-certified until those acceptance tests and operational deployment checks are completed.

## Engineering boundaries
- CSV CPM uses FS links and relative working periods. XER CPM supports FS / SS / FF / SF and lag but is calendar-free. Neither replaces native P6 recalculation with calendars, constraints, resource levelling and full project settings.
- PyP6Xer DCMA14 uses the upstream library's own analysis model. Validate source data and P6 settings before treating any quality score as contractual evidence.
- EVM allocates each WBS BOQ budget across activities using activity weight shares, then calculates earned value from reported quantities. It requires valid BOQ budget, activity weights, quantity progress, status date and actual-cost transactions.
- Monte Carlo assumes independent risk occurrence and uses supplied three-point duration multipliers for PERT unless richer uncertainty data is provided.
- AI output is advisory and depends on external provider credentials. Drawing pages are sent to Gemini only after explicit user action. Takeoff quantities require human verification and must not replace signed measurements.
- AI output must not replace deterministic calculations or professional review.
- Drawing-to-BOQ is an assisted draft workflow, not an automatic certified quantity survey. Resource capacity screening and float-constrained smoothing are planning aids, not full resource leveling or a substitute for Primavera P6 resource leveling. Telegram delivery is optional and user-triggered. PDF output is a management report, not a signed contractual report. Full P6 calendar/resource semantics remain outside the current release.

## Optional AI provider configuration

AI narrative analysis is disabled until a provider key is configured. The user must explicitly click **Generate AI project analysis** before project context is sent to the selected provider.

Configure one or both keys using environment variables:
- `GROQ_API_KEY`
- `GEMINI_API_KEY`

Or create `.streamlit/secrets.toml` in this application folder with:
```toml
GROQ_API_KEY = "your-groq-api-key"
GEMINI_API_KEY = "your-gemini-api-key"
```

Never commit `secrets.toml`, paste keys into source code, or include keys in screenshots. The repository ignores the local `.streamlit` directory. The Groq default model is `llama-3.3-70b-versatile`; Gemini default is `gemini-2.5-flash`. Model names can be overridden in the AI Advisor UI. Provider requests require internet access and may incur provider usage charges.

## Run

### Windows — one-click launcher

Double-click `START_AI_PROJECT_CONTROL.bat` inside the `ai_project_control` folder. The launcher creates the local virtual environment if needed, installs the pinned-range requirements, and starts Streamlit in the browser. Python 3.11 and an internet connection are required for first-time setup. Keep the console window open while using the application.

If you prefer PowerShell, from the `ai_project_control` folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

On macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Automated tests

```bash
python -m pytest -q tests
python -m compileall -q .
```

GitHub Actions runs the deterministic test suite on pushes to this integration branch. Keep sample project data synthetic; never commit real client data, API keys, Telegram tokens, or the SQLite database.

## Local data
SQLite file: %LOCALAPPDATA%\\AIProjectControl\\project_control.db on Windows (or the user's home directory on other platforms). The database is stored outside the PyInstaller bundle so application updates do not overwrite project records. Back it up. Never commit confidential project data or the database to a public repository.

See THIRD_PARTY_NOTICES.md for source attribution and licensing.