# AI Project Control System — Integrated V1

Local-first Streamlit application consolidating compatible project-control capabilities from the source projects in this repository.

## Integrated features
- Project Data Hub: CSV / Excel templates, business validation and SQLite persistence per project.
- Primavera P6 XER: %T/%F/%R parser, PROJECT / PROJWBS / TASK / TASKPRED inspection and conversion.
- CSV schedule CPM: forward/backward pass, early/late dates, total float, critical path and Gantt using pmcontrols.
- XER CPM: FS / SS / FF / SF relationships and lag on a calendar-free day scale.
- DCMA-style 14-point schedule-health screen adapted from TPPSCI. Points 12–14 remain explicitly Not Assessed until baseline continuity/reference data is implemented.
- Cost & EVM: BAC, PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC, TCPI and earned-schedule ES / SV(t) / SPI(t) / IEAC(t) when baseline inputs support it.
- Progress quantities by activity / BOQ / reporting period.
- Risk register exposure Monte Carlo and activity three-point PERT schedule Monte Carlo.
- Minimum-cost schedule crashing with scipy.optimize.linprog when approved crash assumptions are supplied.
- Optional AI Project Advisor through Groq or Google Gemini; API key is entered per session and is not stored in SQLite. User explicitly initiates transmission.
- Excel workbook and CSV report exports.

## Source integration map
- pmcontrols-main/pmcontrols: integrated Python package copy for CPM, PERT / Monte Carlo, EVM / earned schedule primitives and schedule crashing; MIT.
- tppsci-project-controls-suite-master: XER record model, relationship-aware CPM concepts and DCMA / QSRA schedule-health methods; MIT. Python adapters are in core.py.
- project-controls-dashboard-main/src/metrics.py: adapted EVM performance indices and SPI finish forecast in dashboard_metrics.py; MIT.
- EVM_Project-main: reference-only workbook EVM workflow; not used as the authoritative calculation engine.

## Engineering boundaries
- CSV CPM uses FS links and relative working periods. XER CPM supports FS / SS / FF / SF and lag but is calendar-free. Neither replaces native P6 recalculation with calendars, constraints, resource levelling and full project settings.
- DCMA points 12–14 are intentionally Not Assessed without a validated baseline/continuity basis; the UI does not invent those scores.
- EVM requires valid BOQ budget, activity weights, quantity progress, status date and actual-cost transactions.
- Monte Carlo assumes independent risk occurrence and uses supplied three-point duration multipliers for PERT unless richer uncertainty data is provided.
- AI output is advisory and depends on external provider credentials. It must not replace deterministic calculations or professional review.
- Drawing-to-BOQ, full resource optimization, Telegram automation, PDF output, and full P6 calendar/resource semantics remain subsequent releases.

## Run
Install requirements.txt and run: streamlit run app.py

## Local data
SQLite file: project_control.db in this application directory. Back it up. Never commit confidential project data or the database to a public repository.

See THIRD_PARTY_NOTICES.md for source attribution and licensing.