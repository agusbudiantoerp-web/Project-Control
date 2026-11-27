# AI Project Control System — Repository Audit & Integration Plan

Audit date: 2026-11-22
Repository: agusbudiantoerp-web/Project-Control
Default branch: main
Working branch: ai-project-control-integration

## 1. Repository baseline

The repository contains four source projects:

- `tppsci-project-controls-suite-master/`
- `pmcontrols-main/`
- `project-controls-dashboard-main/`
- `EVM_Project-main/`

The integration will be a new application in `ai_project_control/`. Existing upstream projects remain intact and are treated as reference/engine components.

## 2. Audited components

### A. TPPSCI — Primavera P6 schedule intelligence

Location: `tppsci-project-controls-suite-master/`

Verified source files include:

- `src/xerParser.ts`: parses XER text records (%T, %F, %R) and maps PROJECT, PROJWBS, TASK, TASKPRED.
- `src/cpm.ts`: CPM/network calculations.
- `src/dcmaEngine.ts`: DCMA 14-point assessment and Monte Carlo schedule risk.
- `src/types.ts`: typed project, WBS, activity, relationship, and risk result structures.
- `src/main.ts`: browser UI and module wiring.
- `src/cpm.test.ts`: CPM tests.
- `package.json`: Vite/TypeScript browser application; Node.js 20+ is required per README.

Verified capabilities described by its README:

- XER viewer and Gantt
- DCMA 14-point schedule assessment
- QSRA Monte Carlo using triangular or Beta-PERT duration sampling
- Longest-path analysis
- Schedule mentor
- XER anonymization

Important limitation: the README labels Schedule Comparison, Progress Roll-Up, Time-Chainage, and MS Project Fixer as prototype tabs that are not yet computed from the loaded schedule. Its CPM engine is screening-grade and calendar-free, not a replacement for Primavera recalculation.

### B. pmcontrols — Python calculation library

Location: `pmcontrols-main/`

Verified source files include:

- `pmcontrols/network.py`
- `pmcontrols/evm.py`
- `pmcontrols/crash.py`
- `pmcontrols/plot.py`
- `tests/test_cpm.py`
- `tests/test_evm.py`
- `tests/test_pert.py`
- `tests/test_crash.py`
- `tests/validation_cases.json`
- `pyproject.toml`

Package metadata identifies MIT licensing and dependencies numpy, pandas, scipy. Documented capabilities include CPM, PERT schedule risk, Monte Carlo completion percentiles, minimum-cost schedule crashing, EVM, earned schedule, EAC/ETC/VAC/TCPI, and optional charts.

Integration recommendation: candidate deterministic Python calculation service. Preserve its validation tests. Confirm API and data assumptions before connecting it to the application.

### C. Project Controls Dashboard — management reporting and registers

Location: `project-controls-dashboard-main/`

Verified source files include:

- `dashboard.py`
- `src/metrics.py`
- `data/cost_schedule_timeseries.csv`
- `data/risk_register.csv`
- `data/change_register.csv`
- `data/milestones.csv`
- `requirements.txt`
- `tests/`

Dependencies include pandas and matplotlib. The metrics module calculates cumulative PV/EV/AC, SV/CV, SPI/CPI, EAC/ETC/VAC/TCPI, milestone slippage, risk exposure/overdue mitigation, and approved versus pending change impacts.

Integration recommendation: reuse data model, reporting concepts, and visual patterns after reconciling formulas with the selected calculation engine. Avoid competing EVM implementations.

### D. EVM_Project — reference workflow and sample files

Location: `EVM_Project-main/`

Verified files include:

- `main.py`
- `msp_export.xlsx`
- `evm_processed_data.xlsx`
- `Project_Schedule_EVM.mpp`
- `EVM_Performance_Dashboard.pbix`
- `README.md`

The Python script reads a Microsoft Project Excel export and computes basic PV, EV, AC, CV, SV, CPI, and SPI. This is a reference workflow, not a complete platform. Review formula assumptions and zero-denominator handling before reuse.

## 3. New application architecture

The new application will live in `ai_project_control/` and will be built incrementally:

1. Project Data Hub: validated imports for XER, Excel/CSV, PDF, and drawings.
2. Planning Engine: XER parsing, WBS, CPM, float, critical path, DCMA checks, schedule risk.
3. Cost & EVM Engine: one authoritative PV/EV/AC and EVM calculation path, with baseline/version control.
4. Progress Engine: time-phased planned and actual quantities, weighted progress, productivity evidence.
5. Risk Engine: risk register, PERT/QSRA, Monte Carlo cost and schedule scenarios.
6. AI Prediction: delay/cost prediction only after sufficient historical, labeled project data is available.
7. Optimization Engine: schedule crashing and later resource/capacity optimization.
8. AI Reporting: source-linked explanations, management report, Excel/PDF exports, and optional Telegram delivery.

## 4. Integration rules

- Keep `main` unchanged; all new work is on `ai-project-control-integration`.
- Do not copy entire repositories into one runtime without dependency and license review.
- Keep source attribution and upstream LICENSE files.
- Establish one canonical project/activity/WBS identifier mapping.
- Store baseline, status date, source file, import timestamp, and data provenance.
- Validate imported data; never silently convert missing or invalid inputs to zero.
- Keep deterministic calculations separate from LLM interpretation.
- Treat photo-based progress and drawing-derived quantities as estimates requiring human review.
- Do not claim a module is integrated until its code path and tests are connected.

## 5. Implementation sequence

### Phase 1 — new application foundation and data templates
- Create an independent Streamlit application shell.
- Provide downloadable CSV/Excel input templates with field descriptions.
- Validate uploaded files and report missing/invalid columns.
- Keep sample data separate from real project data.

### Phase 2 — schedule intelligence
- Import XER.
- Map project/WBS/activity/relationship fields to canonical records.
- Expose CPM, float, critical path, DCMA checks, and QSRA outputs.
- Reconcile screening-grade results against P6 dates and disclose differences.

### Phase 3 — cost, progress, and EVM
- Define baseline and reporting-period data contracts.
- Connect progress and actual cost inputs.
- Use one authoritative EVM engine.
- Add EAC/ETC/VAC/TCPI and traceable management reporting.

### Phase 4 — risk, AI, and decision support
- Connect risk register and cost/schedule uncertainty.
- Add AI explanations grounded in source records and calculated metrics.
- Add predictions only after model validation and sufficient historical data.

### Phase 5 — drawings, resources, and outputs
- Evaluate drawing takeoff separately.
- Add human-reviewed quantity extraction.
- Add manpower/equipment productivity and optimization when required data exists.
- Add approved Excel/PDF/Telegram reporting.

## 6. Immediate next step

Build and validate the independent Data Hub and its input templates first. Then connect the existing calculation engines behind stable, tested data contracts.


## 7. Integrated V1 implementation status (2026-11-22)

The following implementation has now been committed to the working branch. This section supersedes the earlier immediate-next-step note above.

### Integrated application paths

- Project Data Hub: CSV / Excel templates, business validation, and per-project SQLite persistence. Database is stored under the user's LOCALAPPDATA\AIProjectControl directory on Windows so PyInstaller bundle updates do not replace project data.
- pmcontrols: source package copied into ai_project_control/pmcontrols and used by the application for CSV CPM, PERT Monte Carlo, EVM / earned schedule primitives, and schedule crashing.
- TPPSCI: its XER parsing model and relationship-aware FS/SS/FF/SF CPM approach are adapted in core.py; the DCMA-style screening fallback is also present.
- Project Controls Dashboard: EVM metric and SPI-based finish-forecast functions are adapted in dashboard_metrics.py; milestone and change-register metrics are connected in the app.
- PyP6Xer 2.x: installed as a runtime dependency (LGPL-2.1-or-later) and used for full XER object parsing, resources, assignments, calendars, relationships, and the upstream DCMA14 analysis. The LGPL license text and distribution note are included in ai_project_control/licenses and THIRD_PARTY_NOTICES.md.
- EVM_Project: retained as a reference workflow only. Its simple row-level calculation is not the authoritative EVM engine; no unlicensed source code is copied from that directory.

### User-facing modules in the integrated app

- Overview and Project Data Hub
- Planning & CPM
- Cost & EVM, including WBS-weighted BOQ allocation and earned-schedule metrics where baseline inputs permit
- Progress tracking
- Risk register exposure Monte Carlo and activity PERT schedule Monte Carlo
- Schedule crashing optimization when crash duration/cost assumptions are supplied
- Primavera XER parsing, object-model inspection, relationship-aware CPM and DCMA14
- Resources & Manpower loading / capacity screening
- Milestones & Change Control
- PDF Drawing to BOQ draft extraction through Gemini vision with editable human review
- AI Project Advisor through Groq or Gemini
- Historical trend forecast when at least three valid progress reporting periods exist
- Excel / PDF reports and optional Telegram delivery

### Known boundaries before production sign-off

- No integrated runtime test suite has been executed yet; automated tests have been added and are intentionally awaiting the consolidated test phase.
- CSV CPM uses FS relationships on relative working periods. XER CPM preserves FS/SS/FF/SF and lag but remains calendar-free. Neither replaces Primavera P6 native recalculation.
- Resource loading is a capacity-screening calculation, not a full P6 resource-leveling solver.
- Drawing-to-BOQ is a draft extraction assistant. Quantities, scale, units, scope and assumptions require human quantity-surveyor verification.
- Historical trend forecasting is a transparent linear trend projection, not a trained ML model. Reliable AI/ML prediction requires validated historical project outcomes.
- AI API credentials are entered per session and are not stored by the app. Drawing pages and project summaries are sent to the selected external AI provider only after explicit user action.
- PDF/Telegram, PyP6Xer LGPL bundling, and PyInstaller packaging still require consolidated Windows distribution review.

### Next development work

1. Complete static review and data-contract reconciliation across modules.
2. Finish remaining production safeguards, import/export consistency, and backup/restore controls.
3. Run the consolidated automated tests once feature development is frozen.
4. Fix all test/runtime issues, then perform one integrated acceptance test.
5. Produce the final Windows Standalone distribution and user guide.
