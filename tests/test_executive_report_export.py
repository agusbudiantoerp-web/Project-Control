from io import BytesIO

import pytest

from ai_project_control.executive_report_export import (
    build_executive_report_pdf,
    build_executive_report_xlsx,
)


SAMPLE = """# Executive Report

**Reporting date:** 2026-11-23

## Portfolio
- Projects: 2
| Project | Status |
| A-01 | AT RISK |
"""


def test_xlsx_export_contains_report_text():
    from openpyxl import load_workbook

    payload = build_executive_report_xlsx(SAMPLE)
    workbook = load_workbook(BytesIO(payload), read_only=True)
    values = [row[0] for row in workbook["Executive Report"].iter_rows(values_only=True)]
    assert values[0].startswith("AI PROJECT CONTROL")
    assert any("Executive Report" in str(value) for value in values)
    assert any("A-01" in str(value) for value in values)


@pytest.mark.parametrize("untrusted_line", [
    "=HYPERLINK(\"https://example.invalid\",\"open\")",
    "+SUM(1,1)",
    "-1+2",
    "@SUM(1,1)",
])
def test_xlsx_export_keeps_formula_like_report_lines_as_text(untrusted_line):
    from openpyxl import load_workbook

    payload = build_executive_report_xlsx("Executive report\n" + untrusted_line)
    workbook = load_workbook(BytesIO(payload), data_only=False)
    cell = workbook["Executive Report"]["A4"]
    assert cell.value == untrusted_line
    assert cell.data_type == "s"


def test_pdf_export_returns_valid_pdf_bytes():
    payload = build_executive_report_pdf(SAMPLE)
    assert payload.startswith(b"%PDF")
    assert len(payload) > 500


@pytest.mark.parametrize("builder", [build_executive_report_xlsx, build_executive_report_pdf])
def test_empty_report_rejected(builder):
    with pytest.raises(ValueError, match="report_text"):
        builder("  ")
