# Third-party notices

Retain these notices when redistributing relevant adapted source components.

## pmcontrols
- Upstream: https://github.com/arikanatakan/pmcontrols
- License: MIT
- Copyright: Atakan Arikan
- Integrated modules: CPM/PERT network, EVM/earned schedule, schedule crashing and result types. Source copy is in ai_project_control/pmcontrols/.

## TPPSCI Project Controls Suite
- Source directory: tppsci-project-controls-suite-master/
- License: MIT
- Copyright: Tahir Yamin (2026)
- Adapted capabilities: XER record model, P6 relationship-aware CPM (FS/SS/FF/SF and lag), DCMA-style schedule health screening. Python adapters are in core.py.

## Project Controls Dashboard
- Source directory: project-controls-dashboard-main/
- License: MIT
- Copyright: Alex
- Adapted metrics: EVM performance indices and SPI-based finish forecasting. Adapted module is dashboard_metrics.py.

## EVM_Project
- Source directory: EVM_Project-main/
- No standalone LICENSE file was present in the audited source directory.
- Treated as a reference only; its source code is not copied into the integrated calculation engine. Verify upstream licensing before redistributing that source.

## General
Upstream components are provided under their respective licenses and without warranty. This integrated application is not a certified replacement for Primavera P6 or an independently validated commercial project-controls system.

## PyP6Xer
- Upstream: https://github.com/HassanEmam/PyP6Xer
- Package: PyP6XER 2.0 or later
- License: GNU Lesser General Public License v2.1 or later (LGPL-2.1-or-later)
- Copyright: Hassan Emam and contributors
- Used at runtime for full P6 XER object parsing and DCMA14 analysis; installed as a dependency, not copied into the application source.
- Full license text is included at licenses/PyP6Xer-LGPL-2.1.txt. When distributing a PyInstaller build, preserve the LGPL license and the user's ability to replace/relink the LGPL library as required by the license.
