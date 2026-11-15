"""Build the Excel data template HR fills in (one sheet per table + instructions + data dictionary)."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import config as C
from .data_io import REQUIRED_TABLES, SCHEMA

# (table, column, type, description, example)
DICTIONARY = [
    ("employees", "employee_id", "Text", "Unique employee code, the same in every sheet", "EMP-1043"),
    ("employees", "full_name", "Text", "Shown on the watchlist only. Never used for scoring", "Ali Raza"),
    ("employees", "gender", "Male / Female", "Fairness audit only. Never used for scoring", "Male"),
    ("employees", "date_of_birth", "Date", "Fairness audit only (age bands). Never used for scoring", "1998-04-12"),
    ("employees", "marital_status", "Single / Married", "Fairness audit only. Never used for scoring", "Single"),
    ("employees", "join_date", "Date", "First working day", "2023-08-01"),
    ("employees", "designation_at_join", "Text", "Title when hired; must match a title in config.py", "Design Engineer"),
    ("employees", "discipline", "Text", "Structural, Civil / Site Development, BIM / Revit, Transportation, ...", "Structural"),
    ("employees", "total_experience_at_join_years", "Number", "Years of experience before joining us", "1.5"),
    ("employees", "highest_degree", "Text", "BSc / MSc / PhD", "BSc"),
    ("employees", "billing_rate_usd", "Number", "Hourly rate billed to the client (for impact in $). Optional", "24"),
    ("exits", "employee_id", "Text", "Everyone who left in the last 3+ years, plus anyone serving notice", "EMP-0871"),
    ("exits", "notice_date", "Date", "Day the resignation (or termination notice) was given. Most important date", "2025-07-14"),
    ("exits", "last_working_date", "Date", "Last day at work", "2025-08-13"),
    ("exits", "exit_type", "Resignation / Termination", "", "Resignation"),
    ("exits", "exit_reason", "Text", "Free text is fine: 'Higher studies - Australia', 'Better offer', 'Performance', ...", "MS admission, Australia"),
    ("compensation", "employee_id", "Text", "One row per salary change since joining", "EMP-1043"),
    ("compensation", "effective_date", "Date", "Date the new salary started", "2025-07-01"),
    ("compensation", "monthly_salary_pkr", "Number", "Gross monthly salary after the change", "185000"),
    ("compensation", "designation", "Text", "Title after the change", "Senior Engineer"),
    ("compensation", "change_type", "Joining / Annual Increment / Promotion / Market Adjustment", "", "Annual Increment"),
    ("performance_reviews", "employee_id", "Text", "Every review cycle", "EMP-1043"),
    ("performance_reviews", "review_date", "Date", "", "2025-06-15"),
    ("performance_reviews", "rating", "Number 1-5", "Convert other scales to 1-5", "4"),
    ("performance_reviews", "cycle", "Text", "Annual / Mid-Year", "Annual"),
    ("timesheets", "employee_id", "Text", "One row per person per month", "EMP-1043"),
    ("timesheets", "month", "Date", "Any date in the month (first of month is best)", "2025-09-01"),
    ("timesheets", "total_hours", "Number", "Hours logged", "176"),
    ("timesheets", "billable_hours", "Number", "Hours billed to clients", "142"),
    ("timesheets", "overtime_hours", "Number", "Optional", "12"),
    ("timesheets", "client_feedback_score", "Number 1-5", "Optional; blank if the client gave none that month", "4.2"),
    ("timesheets", "rework_items", "Number", "QA comments / rework requests that month. Optional", "1"),
    ("hr_requests", "employee_id", "Text", "Letters requested from HR", "EMP-1043"),
    ("hr_requests", "request_date", "Date", "", "2025-12-03"),
    ("hr_requests", "request_type", "List", "Experience Letter, Salary Certificate, Bank Letter, Degree Attestation Support, NOC, Employment Verification, Other", "Experience Letter"),
    ("leaves", "employee_id", "Text", "Every leave taken", "EMP-1043"),
    ("leaves", "start_date", "Date", "", "2025-11-08"),
    ("leaves", "days", "Number", "", "1"),
    ("leaves", "leave_type", "List", "Annual, Casual, Sick, Unpaid, Other", "Casual"),
    ("engagement_surveys", "employee_id", "Text", "Pulse or annual survey, if identifiable", "EMP-1043"),
    ("engagement_surveys", "survey_date", "Date", "", "2025-09-20"),
    ("engagement_surveys", "engagement_score", "Number 1-5", "Overall engagement", "3.8"),
    ("engagement_surveys", "growth_score", "Number 1-5", "'I can grow my career here'. Optional", "3.2"),
    ("project_assignments", "employee_id", "Text", "One row per project or manager change", "EMP-1043"),
    ("project_assignments", "start_date", "Date", "", "2025-03-01"),
    ("project_assignments", "end_date", "Date", "Blank if still on it", ""),
    ("project_assignments", "project_code", "Text", "Optional", "P-512"),
    ("project_assignments", "client_name", "Text", "Optional", "US-ATL"),
    ("project_assignments", "client_region", "US / Australia / Internal", "Drives the shift signal", "US"),
    ("project_assignments", "manager_id", "Text", "Line manager on this project", "MGR-07"),
]

LISTS = {
    ("exits", "exit_type"): ["Resignation", "Termination"],
    ("compensation", "change_type"): ["Joining", "Annual Increment", "Promotion", "Market Adjustment"],
    ("hr_requests", "request_type"): ["Experience Letter", "Salary Certificate", "Bank Letter", "Degree Attestation Support", "NOC", "Employment Verification", "Other"],
    ("leaves", "leave_type"): ["Annual", "Casual", "Sick", "Unpaid", "Other"],
    ("project_assignments", "client_region"): ["US", "Australia", "Internal"],
    ("employees", "gender"): ["Male", "Female"],
    ("employees", "marital_status"): ["Single", "Married"],
}

README = [
    ("Retention Radar - HR data template", True),
    ("", False),
    ("How to fill it", True),
    ("1. Fill one sheet per table. Keep the column names exactly as they are. One row per record.", False),
    ("2. Use the same employee_id everywhere. Dates as YYYY-MM-DD (Excel dates also work).", False),
    ("3. Include people who have LEFT (last 3+ years). The agent learns from their history; without leavers it cannot learn.", False),
    ("4. Required sheets: employees, exits, compensation. Every other sheet is optional but makes predictions sharper.", False),
    ("5. Leave a cell blank if you do not know it. Do not type 'N/A'.", False),
    ("6. Run:  python run_agent.py --data Retention_Radar_Data_Template.xlsx", False),
    ("", False),
    ("Urdu summary", True),
    ("Har sheet mein apna data paste karein, column names mat badlein. Jo log company chhor chuke hain un ka data bhi zaroor dalein,", False),
    ("kyunke agent unhi se seekhta hai. Sirf employees, exits aur compensation zaroori hain; baqi sheets se accuracy barhti hai.", False),
    ("", False),
    ("Privacy", True),
    ("gender, date_of_birth, marital_status and full_name are NEVER used to score anyone. They are used only for the fairness audit.", False),
    ("Keep this file on HR systems only. Do not email it outside HR.", False),
    ("", False),
    ("What helps most (in order)", True),
    ("exits with notice_date and a reason > compensation history > hr_requests > timesheets > performance_reviews > leaves > surveys > projects", False),
]

HEAD_FILL = PatternFill("solid", fgColor="1F2A27")
REQ_FILL = PatternFill("solid", fgColor="3B4A45")
HEAD_FONT = Font(bold=True, color="FFFFFF")


def build(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    for i, (text, bold) in enumerate(README, start=1):
        c = ws.cell(row=i, column=1, value=text)
        c.font = Font(bold=bold, size=14 if i == 1 else 11)
    ws.column_dimensions["A"].width = 130

    dd = wb.create_sheet("Data Dictionary")
    dd.append(["table", "column", "required", "type / allowed values", "description", "example"])
    for c in dd[1]:
        c.fill, c.font = HEAD_FILL, HEAD_FONT
    for table, col, typ, desc, ex in DICTIONARY:
        req = "yes" if col in SCHEMA[table][0] and table in REQUIRED_TABLES else ("yes, if sheet used" if col in SCHEMA[table][0] else "optional")
        dd.append([table, col, req, typ, desc, ex])
    for col, w in zip("ABCDEF", (22, 30, 18, 34, 90, 26)):
        dd.column_dimensions[col].width = w
    dd.freeze_panes = "A2"

    for table, (req, opt, _dates) in SCHEMA.items():
        sh = wb.create_sheet(table)
        cols = req + opt
        sh.append(cols)
        for j, name in enumerate(cols, start=1):
            c = sh.cell(row=1, column=j)
            c.fill = REQ_FILL if name in req else HEAD_FILL
            c.font = HEAD_FONT
            c.alignment = Alignment(horizontal="left")
            sh.column_dimensions[get_column_letter(j)].width = max(16, len(name) + 4)
            if (table, name) in LISTS:
                dv = DataValidation(type="list", formula1='"' + ",".join(LISTS[(table, name)]) + '"', allow_blank=True)
                dv.error = "Pick a value from the list"
                sh.add_data_validation(dv)
                dv.add(f"{get_column_letter(j)}2:{get_column_letter(j)}20000")
        sh.freeze_panes = "A2"
        note = sh.cell(row=1, column=len(cols) + 2, value="Darker headers = required columns. Delete nothing; leave unknown cells blank.")
        note.font = Font(italic=True, color="666666")
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


if __name__ == "__main__":
    print(build(C.PROJECT_ROOT / "data_template" / "Retention_Radar_Data_Template.xlsx"))
