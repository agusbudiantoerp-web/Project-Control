# AI Project Control System

New independent application inside the existing Project-Control repository.

## Current status
Phase 1 — Project Data Hub foundation:
- Project metadata
- Downloadable CSV templates for WBS, activities, BOQ, progress, actual cost, risks, and commitments
- CSV/XLSX preview and basic column validation
- Basic Primavera P6 XER raw-table reader

This scaffold does not yet claim full CPM, EVM, Monte Carlo, drawing takeoff, AI prediction, or production-ready P6 calendar logic.

## Run on Windows
1. Install Python 3.11 or newer.
2. Open PowerShell in this folder.
3. Run:

    py -3.11 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    streamlit run app.py

If activation is blocked, run:
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

## Important
- Start with synthetic test data.
- Do not upload confidential client data to a public repository.
- Uploaded files are previewed in memory; this scaffold does not persist project data.
- Validate business rules and source records before relying on reports.
