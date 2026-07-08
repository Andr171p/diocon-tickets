from __future__ import annotations

from typing import TYPE_CHECKING

from io import BytesIO

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Cm, Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

if TYPE_CHECKING:
    from .services.stage_export import ProjectStagesReport

HEADERS = [
    "№",
    "Этап",
    "Статус",
    "Плановое начало",
    "Плановое завершение",
    "Фактическое начало",
    "Фактическое завершение",
    "Ответственный",
    "Просрочен",
    "Длительность (дни)",
    "Описание",
    "Критерии завершения",
]


def export_project_stages_to_excel(report: ProjectStagesReport) -> bytes:
    """
    Сформировать Excel-файл отчета по этапам проекта.
    """

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Этапы проекта"

    worksheet["A1"] = f"Отчет по этапам проекта: {report.project_name}"
    worksheet["A2"] = f"Ключ проекта: {report.project_key}"
    worksheet["A3"] = f"Статус проекта: {report.project_status}"
    worksheet["A4"] = f"Дата формирования: {report.generated_at:%d.%m.%Y %H:%M}"

    for cell in ("A1", "A2", "A3", "A4"):
        worksheet[cell].font = Font(bold=True)

    header_row = 6
    for column_index, header in enumerate(HEADERS, start=1):
        cell = worksheet.cell(row=header_row, column=column_index, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4F81BD")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_index, row in enumerate(report.rows, start=header_row + 1):
        values = [
            row.number,
            row.name,
            row.status,
            row.planned_start,
            row.planned_end,
            row.started_at,
            row.completed_at,
            row.responsible_id,
            row.is_overdue,
            row.planned_duration_days,
            row.description,
            row.completion_criteria,
        ]

        for column_index, value in enumerate(values, start=1):
            cell = worksheet.cell(row=row_index, column=column_index, value=value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    worksheet.freeze_panes = "A7"
    worksheet.auto_filter.ref = (
        f"A{header_row}:{get_column_letter(len(HEADERS))}{max(header_row, header_row + len(report.rows))}"
    )

    column_widths = [6, 28, 16, 18, 20, 20, 22, 38, 14, 18, 42, 42]
    for column_index, width in enumerate(column_widths, start=1):
        worksheet.column_dimensions[get_column_letter(column_index)].width = width

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()

def export_project_stages_to_pdf(report: ProjectStagesReport) -> bytes:
    """
    Сформировтаь PDF-файл отчета по этапам проекта.
    """

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Отчет по этапам проекта: {report.project_name}", styles["Title"]),
        Paragraph(f"Ключ проекта: {report.project_key}", styles["Normal"]),
        Paragraph(f"Статус проекта: {report.project_status}", styles["Normal"]),
        Paragraph(f"Дата формирования: {report.generated_at:%d.%m.%Y %H:%M}", styles["Normal"]),
        Spacer(1, 12),
    ]

    data = [HEADERS]
    for row in report.rows:
        data.append([
            row.number,
            row.name,
            row.status,
            row.planned_start,
            row.planned_end,
            row.started_at,
            row.completed_at,
            row.responsible_id,
            row.is_overdue,
            row.planned_duration_days,
            row.description,
            row.completion_criteria,
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]))

    elements.append(table)
    document.build(elements)

    return output.getvalue()

def export_project_stages_to_word(report: ProjectStagesReport) -> bytes:
    """
    Сформировать Word-файл отчета по этапам проекта.
    """

    document = Document()

    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Cm(1.0)
    section.right_margin = Cm(1.0)
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(1.0)

    title = document.add_heading(f"Отчет по этапам проекта: {report.project_name}", level=1)
    title.alignment = 1
    document.add_paragraph(f"Ключ проекта: {report.project_key}")
    document.add_paragraph(f"Статус проекта: {report.project_status}")
    document.add_paragraph(f"Дата формирования: {report.generated_at:%d.%m.%Y %H:%M}")

    table = document.add_table(rows=1, cols=len(HEADERS))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    header_cells = table.rows[0].cells
    for index, header in enumerate(HEADERS):
        paragraph = header_cells[index].paragraphs[0]
        run = paragraph.add_run(header)
        run.bold = True
        run.font.size = Pt(8)

    for row in report.rows:
        cells = table.add_row().cells
        values = [
            row.number,
            row.name,
            row.status,
            row.planned_start,
            row.planned_end,
            row.started_at,
            row.completed_at,
            row.responsible_id,
            row.is_overdue,
            row.planned_duration_days,
            row.description,
            row.completion_criteria,
        ]

        for index, value in enumerate(values):
            paragraph = cells[index].paragraphs[0]
            run = paragraph.add_run(str(value))
            run.font.size = Pt(8)

    output = BytesIO()
    document.save(output)
    return output.getvalue()