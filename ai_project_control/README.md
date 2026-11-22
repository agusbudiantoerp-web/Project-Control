# AI Project Control System — Integrated V1

Local-first Streamlit application consolidating compatible project-control capabilities from the source projects in this repository.

## Integrated features
- Project Data Hub: CSV / Excel templates, business validation and SQLite persistence per project.
- Primavera P6 XER: PyP6Xer v2 object-model parser for projects, activities, WBS, relationships, resources, assignments, calendars and DCMA14; plus %T/%F/%R raw-table parser and conversion.
- CSV schedule CPM: forward/backward pass, early/late dates, total float, critical path and Gantt using pmcontrols.
- XER CPM: FS / SS / FF / SF relationships and lag on a calendar-free day scale.
- Full PyP6Xer DCMA14 schedule-quality analysis plus TPPSCI DCMA-style screening fallback.
- Cost & EVM: BAC, PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC, TCPI and earned-schedule ES / SV(t) / SPI(t) / IEAC(t) when baseline inputs support it.
- Progress quantities by activity / BOQ / reporting period.
- Resource, manpower and equipment assignments with planned daily load and capacity-overload screening.
- Milestone slippage and change-control impact (approved vs pending cost / schedule changes).
- Risk register exposure Monte Carlo and activity three-point PERT schedule Monte Carlo.
- Minimum-cost schedule crashing with scipy.optimize.linprog when approved crash assumptions are supplied.
- Optional AI Project Advisor through Groq or Google Gemini; API key is entered per session and is not stored in SQLite. User explicitly initiates transmission.
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

## Engineering boundaries
- CSV CPM uses FS links and relative working periods. XER CPM supports FS / SS / FF / SF and lag but is calendar-free. Neither replaces native P6 recalculation with calendars, constraints, resource levelling and full project settings.
- PyP6Xer DCMA14 uses the upstream library's own analysis model. Validate source data and P6 settings before treating any quality score as contractual evidence.
- EVM allocates each WBS BOQ budget across activities using activity weight shares, then calculates earned value from reported quantities. It requires valid BOQ budget, activity weights, quantity progress, status date and actual-cost transactions.
- Monte Carlo assumes independent risk occurrence and uses supplied three-point duration multipliers for PERT unless richer uncertainty data is provided.
- AI output is advisory and depends on external provider credentials. Drawing pages are sent to Gemini only after explicit user action. Takeoff quantities require human verification and must not replace signed measurements.
- AI output must not replace deterministic calculations or professional review.
- Drawing-to-BOQ, full resource optimization, Telegram automation, PDF output, and full P6 calendar/resource semantics remain subsequent releases.

## Run
Install requirements.txt and run: streamlit run app.py

## Local data
SQLite file: %LOCALAPPDATA%\\AIProjectControl\\project_control.db on Windows (or the user's home directory on other platforms). The database is stored outside the PyInstaller bundle so application updates do not overwrite project records. Back it up. Never commit confidential project data or the database to a public repository.

See THIRD_PARTY_NOTICES.md for source attribution and licensing.