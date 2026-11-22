# AI Project Control System — Integrated V1

A local-first Streamlit application consolidating compatible project-control capabilities from the source projects stored in this repository.

## Integrated capabilities
- Project Data Hub: CSV / Excel templates, structural and business validation, SQLite persistence per project.
- Primavera P6 XER: %T/%F/%R parser, PROJECT / PROJWBS / TASK / TASKPRED inspection and conversion.
- Planning: CPM forward/backward pass, early/late dates, total float, critical path and Gantt using the audited pmcontrols engine.
- XER network screening: FS / SS / FF / SF relationships and lag on a calendar-free day scale.
- DCMA-style schedule health screen: 14-point view; checks 12–14 explicitly Not Assessed until baseline continuity/reference data is available.
- Cost & EVM: BAC, PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC, TCPI and SPI-based finish forecast.
- Progress quantities by activity / BOQ / reporting period.
- Risk expected exposure and seeded Monte Carlo cost / schedule scenarios.
- Minimum-cost schedule crashing using scipy.optimize.linprog when crash assumptions are supplied.
- Multi-sheet Excel export and individual CSV exports.
- SQLite local persistence.

## Source integration map
- pmcontrols-main/pmcontrols: CPM, PERT / Monte Carlo, EVM / earned schedule primitives and schedule crashing; MIT.
- tppsci-project-controls-suite-master: XER parsing model, relationship-aware CPM concepts and DCMA / QSRA schedule-quality methods; MIT. Python adapters are in core.py.
- project-controls-dashboard-main/src/metrics.py: EVM performance and SPI finish forecasting; MIT.
- EVM_Project-main: reference-only EVM workbook workflow; not used as the authoritative calculation engine.

## Engineering boundaries
- CSV activity CPM uses FS relationships and relative working periods. XER CPM supports FS / SS / FF / SF plus lag but is calendar-free. Neither replaces native P6 recalculation with calendars, constraints, resource levelling and all project settings.
- EVM depends on a valid BOQ budget, activity weights, quantity progress, status date and actual-cost transactions.
- Monte Carlo uses independent risk occurrence unless correlation data is provided.
- AI prediction / LLM advisor is not represented as active without historical reporting data and configured provider credentials. AI will explain and recommend; deterministic engineering calculations remain authoritative.
- Drawing-to-BOQ, detailed resource optimization, Telegram automation, PDF generation, and full P6 calendar/resource semantics remain subsequent releases.

## Run
Install requirements.txt and run: streamlit run app.py

## Local data
SQLite file: project_control.db in this application directory. Back it up. Do not commit confidential project data or the database to a public repository.

See THIRD_PARTY_NOTICES.md for source attribution and licensing.