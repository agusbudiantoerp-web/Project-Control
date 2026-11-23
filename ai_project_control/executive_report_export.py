"""Export executive report text to XLSX and PDF documents."""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape


def build_executive_report_xlsx(report_text: str) -> bytes:
    """Return an XLSX workbook containing the report line-by-line."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    if not str(report_text).strip():
        raise ValueError("report_text must not be empty")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Executive Report"
    sheet.append(["AI PROJECT CONTROL — EXECUTIVE REPORT"])
    sheet["A1"].font = Font(bold=True, size=14)
    sheet["A1"].fill = PatternFill("solid", fgColor="D9EAF7")
    sheet.append(["Report content"])
    sheet["A2"].font = Font(bold=True)
    for line in str(report_text).splitlines():
        sheet.append([line])
    sheet.column_dimensions["A"].width = 110
    for row in sheet.iter_rows(min_row=2, max_col=1):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A3"
    sheet.sheet_view.showGridLines = False
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def build_executive_report_pdf(report_text: str) -> bytes:
    """Return a simple readable PDF rendition of a Markdown-like report."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    if not str(report_text).strip():
        raise ValueError("report_text must not be empty")
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="AI Project Control Executive Report",
    )
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "ReportBody", parent=base["BodyText"], fontName="Helvetica",
        fontSize=8.5, leading=12, alignment=TA_LEFT, spaceAfter=4,
    )
    heading = ParagraphStyle(
        "ReportHeading", parent=base["Heading2"], fontSize=12,
        leading=15, spaceBefore=8, spaceAfter=5,
    )
    title = ParagraphStyle(
        "ReportTitle", parent=base["Title"], fontSize=16,
        leading=20, textColor=colors.HexColor("#17365D"), spaceAfter=10,
    )
    story = []
    for index, raw_line in enumerate(str(report_text).splitlines()):
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 3))
            continue
        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), title))
        elif line.startswith("## "):
            story.append(Paragraph(escape(line[3:]), heading))
        elif line.startswith("|"):
            story.append(Paragraph(escape(line.replace("|", "   •   ")), body))
        elif line.startswith("- "):
            story.append(Paragraph("&#8226; " + escape(line[2:]), body))
        else:
            cleaned = line.replace("**", "")
            story.append(Paragraph(escape(cleaned), body))
    document.build(story)
    return output.getvalue()
