"""Generates Excel, CSV (zipped), and PDF reports from report_service data.
Everything is produced in-memory (BytesIO) — nothing is written permanently
to disk, and filenames are always application-controlled.
"""
import csv
import io
import zipfile
from datetime import datetime

from flask import current_app
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils.date_utils import format_date_for_display

TASK_HEADERS = ["Date", "Time", "Title", "Project", "Priority", "Status", "Due Date", "Estimated", "Spent", "Notes"]
MEETING_HEADERS = ["Date", "Time", "Title", "Project", "My Points", "Meeting Points", "Decisions", "Notes"]


def _task_headers(show_owner):
    headers = list(TASK_HEADERS)
    if show_owner:
        headers.insert(4, "Owner")
    return headers


def _meeting_headers(show_owner):
    headers = list(MEETING_HEADERS)
    if show_owner:
        headers.insert(4, "Owner")
    return headers


def _owner_name(row):
    return row["owner_full_name"] or row["owner_username"]


def _project_name(row):
    return row["project_name"] or ""


def _task_row(t, show_owner=False):
    row = [
        format_date_for_display(t["task_date"]),
        t["task_time"] or "",
        t["title"],
        _project_name(t),
    ]
    if show_owner:
        row.append(_owner_name(t))
    row += [
        t["priority"],
        t["status"].replace("_", " ").title(),
        format_date_for_display(t["due_date"]) if t["due_date"] else "",
        t["estimated_hours"] if t["estimated_hours"] is not None else "",
        t["time_spent_hours"] if t["time_spent_hours"] is not None else "",
        t["notes"] or "",
    ]
    return row


def _meeting_row(m, show_owner=False):
    row = [
        format_date_for_display(m["meeting_date"]),
        m["meeting_time"] or "",
        m["title"],
        _project_name(m),
    ]
    if show_owner:
        row.append(_owner_name(m))
    row += [
        m["my_points"] or "",
        m["meeting_points"] or "",
        m["decisions"] or "",
        m["notes"] or "",
    ]
    return row


# ---------------------------------------------------------------- Excel ----

def generate_excel(report_data):
    show_owner = report_data.get("show_owner", False)
    wb = Workbook()

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")

    summary_ws = wb.active
    summary_ws.title = "Summary"
    summary_ws["A1"] = f"{current_app.config['APP_NAME']} - Report"
    summary_ws["A1"].font = Font(bold=True, size=14)
    summary_ws["A2"] = f"Report Period: {report_data['range_label']}"
    summary_ws["A3"] = f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}"

    summary_rows = [
        ("Total Tasks", report_data["summary"]["total_tasks"]),
        ("Completed", report_data["summary"]["completed"]),
        ("In Progress", report_data["summary"]["in_progress"]),
        ("TODO", report_data["summary"]["todo"]),
        ("On Hold", report_data["summary"]["on_hold"]),
        ("Cancelled", report_data["summary"]["cancelled"]),
        ("Overdue", report_data["summary"]["overdue"]),
        ("Total Meetings", report_data["summary"]["total_meetings"]),
        ("Total Hours Estimated", report_data["summary"]["total_estimated"]),
        ("Total Hours Logged", report_data["summary"]["total_time_spent"]),
    ]
    start_row = 5
    summary_ws.cell(row=start_row, column=1, value="Metric").font = header_font
    summary_ws.cell(row=start_row, column=1).fill = header_fill
    summary_ws.cell(row=start_row, column=2, value="Value").font = header_font
    summary_ws.cell(row=start_row, column=2).fill = header_fill
    for i, (label, value) in enumerate(summary_rows, start=start_row + 1):
        summary_ws.cell(row=i, column=1, value=label)
        summary_ws.cell(row=i, column=2, value=value)
    summary_ws.column_dimensions["A"].width = 22
    summary_ws.column_dimensions["B"].width = 15

    def build_sheet(name, headers, rows, row_builder):
        ws = wb.create_sheet(name)
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        for r, item in enumerate(rows, start=2):
            for c, value in enumerate(row_builder(item), start=1):
                ws.cell(row=r, column=c, value=value)
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20
        if rows:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"
        ws.freeze_panes = "A2"
        return ws

    build_sheet("Tasks", _task_headers(show_owner), report_data["tasks"], lambda item: _task_row(item, show_owner))
    build_sheet("Meetings", _meeting_headers(show_owner), report_data["meetings"], lambda item: _meeting_row(item, show_owner))

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# ------------------------------------------------------------------ CSV ----

def generate_csv_zip(report_data):
    show_owner = report_data.get("show_owner", False)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        tasks_csv = io.StringIO()
        writer = csv.writer(tasks_csv)
        writer.writerow(_task_headers(show_owner))
        for t in report_data["tasks"]:
            writer.writerow(_task_row(t, show_owner))
        zf.writestr("tasks.csv", tasks_csv.getvalue())

        meetings_csv = io.StringIO()
        writer = csv.writer(meetings_csv)
        writer.writerow(_meeting_headers(show_owner))
        for m in report_data["meetings"]:
            writer.writerow(_meeting_row(m, show_owner))
        zf.writestr("meetings.csv", meetings_csv.getvalue())

    buffer.seek(0)
    return buffer


# ------------------------------------------------------------------ PDF ----

def _add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(
        landscape(letter)[0] - 0.5 * inch, 0.4 * inch, f"Page {doc.page}"
    )
    canvas.restoreState()


def generate_pdf(report_data):
    show_owner = report_data.get("show_owner", False)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    title_style = styles["Title"]
    heading_style = styles["Heading2"]

    story = []
    story.append(Paragraph(current_app.config["APP_NAME"].replace("&", "&amp;"), title_style))
    story.append(Paragraph(f"Report Period: {report_data['range_label']}", styles["Normal"]))
    story.append(
        Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", styles["Normal"])
    )
    story.append(Spacer(1, 12))

    summary = report_data["summary"]
    summary_table_data = [
        ["Total Tasks", "Completed", "In Progress", "TODO", "On Hold", "Cancelled", "Overdue", "Meetings", "Est. Hrs", "Hrs Logged"],
        [
            summary["total_tasks"],
            summary["completed"],
            summary["in_progress"],
            summary["todo"],
            summary["on_hold"],
            summary["cancelled"],
            summary["overdue"],
            summary["total_meetings"],
            summary["total_estimated"],
            summary["total_time_spent"],
        ],
    ]
    summary_table = Table(summary_table_data, hAlign="LEFT")
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 16))

    def escape(text):
        return Paragraph((text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), cell_style)

    story.append(Paragraph("Task Report", heading_style))
    if report_data["tasks"]:
        data = [_task_headers(show_owner)] + [
            [escape(str(v)) for v in _task_row(t, show_owner)] for t in report_data["tasks"]
        ]
        task_col_widths = [0.7 * inch, 0.5 * inch, 1.3 * inch, 0.9 * inch, 0.7 * inch, 0.9 * inch, 0.7 * inch, 0.5 * inch, 0.5 * inch, 1.9 * inch]
        if show_owner:
            task_col_widths.insert(4, 1.0 * inch)
        table = Table(data, repeatRows=1, colWidths=task_col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No tasks found for this date range.", styles["Normal"]))

    story.append(Spacer(1, 16))
    story.append(Paragraph("Meeting Report", heading_style))
    if report_data["meetings"]:
        data = [_meeting_headers(show_owner)] + [
            [escape(str(v)) for v in _meeting_row(m, show_owner)] for m in report_data["meetings"]
        ]
        meeting_col_widths = [0.7 * inch, 0.5 * inch, 1.2 * inch, 0.9 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch]
        if show_owner:
            meeting_col_widths.insert(4, 0.9 * inch)
        table = Table(data, repeatRows=1, colWidths=meeting_col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No meetings found for this date range.", styles["Normal"]))

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buffer.seek(0)
    return buffer
