# AI Project Control System — Repository Audit & Integration Plan

Audit date: 2026-11-21
Repository: agusbudiantoerp-web/Project-Control
Default branch: main
Working branch: ai-project-control-integration

## 1. Repository baseline

The repository is public and currently contains four project folders:

- `tppsci-project-controls-suite-master/`
- `pmcontrols-main/`
- `project-controls-dashboard-main/`
- `EVM_Project-main/`

The file `Manajemen Proyek` is a 1-byte file and is not a usable project module.

The screenshot titled PROJECT CONTROL V10 was supplied in conversation, but its source code is not present in the repository root or the four audited project folders as currently indexed. The V10 application must be located before its importer, database, and module contracts can be integrated safely.

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

Important limitation: the README explicitly labels Schedule Comparison, Progress Roll-Up, Time-Chainage, and MS Project Fixer as prototype tabs that are not yet computed from the loaded schedule. The CPM engine is described as screening-grade and calendar-free, not a replacement for Primavera recalculation.

### B. pmcontrols — validated Python calculation library

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

The README and package metadata identify MIT licensing and dependencies numpy, pandas, scipy. The documented capabilities include CPM, PERT schedule risk, Monte Carlo completion percentiles, minimum-cost schedule crashing, EVM, earned schedule, EAC/ETC/VAC/TCPI, and optional charts. Results include structured alerts and provenance metadata.

Integration recommendation: use this as the first candidate for a deterministic Python calculation service. Keep its validation tests and do not replace calculations with LLM-generated arithmetic.

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

Dependencies in requirements.txt: pandas and matplotlib.

The metrics module calculates cumulative PV/EV/AC, SV/CV, SPI/CPI, EAC/ETC/VAC/TCPI, milestone slippage, risk exposure/overdue mitigation, and approved versus pending change impacts. The README describes the application as a project-controls reporting cycle based on timeseries, milestone, risk, and change-register inputs.

Integration recommendation: reuse the data model, reporting concepts, and visual/reporting patterns after reconciling them with the selected calculation engine. Avoid running duplicate EVM formulas in two competing places.

### D. EVM_Project — reference workflow and sample files

Location: `EVM_Project-main/`

Verified files include:

- `main.py`
- `msp_export.xlsx`
- `evm_processed_data.xlsx`
- `Project_Schedule_EVM.mpp`
- `EVM_Performance_Dashboard.pbix`
- `README.md`

The Python script reads a Microsoft Project Excel export and computes basic PV, EV, AC, CV, SV, CPI, and SPI. The README describes a Power BI dashboard.

Important limitation: this is a simple example workflow, not a complete integrated project-control platform. Its EVM formula assumptions and zero-denominator fallback values must be reviewed before production use.

## 3. Proposed target architecture

1. Project Data Hub: validated imports for XER, Excel/CSV, PDF, and drawings.
2. Planning Engine: XER parsing, WBS, CPM, float, critical path, DCMA checks, schedule risk.
3. Cost & EVM Engine: one authoritative PV/EV/AC and EVM calculation path, with baseline/version control.
4. Progress Engine: time-phased planned and actual quantities, weighted progress, productivity evidence.
5. Risk Engine: risk register, PERT/QSRA, Monte Carlo cost and schedule scenarios.
6. AI Prediction: delay/cost prediction only after sufficient historical, labeled project data is available.
7. Optimization Engine: schedule crashing and later resource/capacity optimization.
8. AI Reporting: source-linked explanations, management report, Excel/PDF exports, and optional Telegram delivery.

## 4. Integration rules

- Keep `main` unchanged; all work begins on `ai-project-control-integration`.
- Do not copy entire repositories into one runtime without dependency and license review.
- Keep source attribution and each upstream LICENSE file.
- Establish one canonical project/activity/WBS identifier mapping.
- Store baseline, status date, source file, import timestamp, and data provenance.
- Validate imported data before calculations; never silently convert missing or invalid inputs to zero.
- Keep deterministic CPM/EVM/Monte Carlo calculations separate from LLM interpretation.
- Treat photo-based progress and drawing-derived quantities as estimates requiring human review.
- Do not claim the V10 application is integrated until its source code and import contracts are located.

## 5. Proposed implementation sequence

### Phase 0 — locate and understand V10
Required: V10 source folder/repository, entry point, import/export handlers, database/storage implementation, dependency file, and sample input files. Confirm whether the screenshot application is a separate local project.

### Phase 1 — establish an integration test harness
- Run and preserve upstream tests for pmcontrols.
- Run TPPSCI typecheck/build/tests.
- Record dashboard test results and supported input schemas.
- Create synthetic test data with known expected CPM and EVM results.

### Phase 2 — connect schedule intelligence
- Import XER.
- Map project/WBS/activity/relationship fields to canonical records.
- Expose CPM, float, critical path, DCMA checks, and QSRA outputs.
- Reconcile screening-grade results against P6 dates and disclose differences.

### Phase 3 — connect cost, progress, and EVM
- Define baseline and reporting-period data contracts.
- Connect progress and actual cost inputs.
- Use one authoritative EVM engine.
- Add EAC/ETC/VAC/TCPI and traceable management reporting.

### Phase 4 — risk, AI, and decision support
- Connect risk register and cost/schedule uncertainty.
- Add AI explanations with citations to source records and calculated metrics.
- Add predictions only after model validation and sufficient historical data.

### Phase 5 — drawings, resources, and outputs
- Evaluate drawing takeoff separately.
- Add human-reviewed quantity extraction.
- Add manpower/equipment productivity and optimization only when the required resource data exists.
- Add approved Excel/PDF/Telegram reporting.

## 6. Immediate next requirement

The user must identify where the PROJECT CONTROL V10 source code is stored. The screenshot alone is not enough to determine accepted file formats, mandatory fields, database schema, or upload sequence.

No application code has been changed in this audit step. This file is an audit and implementation plan only.
