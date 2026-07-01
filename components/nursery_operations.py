"""
Nursery Operations – Phase 1 + Reports & Printouts (All Indian Languages)
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import io, os, glob
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# Indian languages mapping (same as in reports.py)
# ---------------------------------------------------------------------------
INDIAN_LANGUAGES = {
    "English": "en",
    "हिन्दी (Hindi)": "hi",
    "বাংলা (Bengali)": "bn",
    "తెలుగు (Telugu)": "te",
    "मराठी (Marathi)": "mr",
    "தமிழ் (Tamil)": "ta",
    "اردو (Urdu)": "ur",
    "ગુજરાતી (Gujarati)": "gu",
    "ಕನ್ನಡ (Kannada)": "kn",
    "ଓଡ଼ିଆ (Odia)": "or",
    "മലയാളം (Malayalam)": "ml",
    "ਪੰਜਾਬੀ (Punjabi)": "pa",
    "অসমীয়া (Assamese)": "as",
    "मैथिली (Maithili)": "mai"
}

# ---------------------------------------------------------------------------
# Font helper (same logic as reports.py)
# ---------------------------------------------------------------------------
def _find_noto_font():
    """Locate NotoSans-Regular.ttf on the system."""
    search_patterns = [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans*.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans*.ttf",
        "/usr/share/fonts/noto/*.ttf"
    ]
    for pattern in search_patterns:
        for match in glob.glob(pattern):
            if "Regular" in match or "regular" in match.lower():
                return match
    return None

# ---------------------------------------------------------------------------
# Translation dictionary for static report headings
# ---------------------------------------------------------------------------
def get_translations(lang_code):
    """Return dict of translated strings for report headings."""
    # Default English
    t = {
        "daily_handout": "Daily Task Handout",
        "date": "Date",
        "task_id": "Task ID",
        "batch": "Batch",
        "task": "Task",
        "employee": "Employee",
        "status": "Status",
        "monthly_attendance": "Monthly Attendance Report",
        "employee_name": "Employee Name",
        "month": "Month",
        "day": "Day",
        "check_in": "Check-In",
        "check_out": "Check-Out",
        "task_calendar": "Task Calendar",
        "scheduled_date": "Scheduled Date",
    }
    if lang_code == "hi":
        t.update({
            "daily_handout": "दैनिक कार्य सूची",
            "date": "दिनांक",
            "task_id": "कार्य ID",
            "batch": "बैच",
            "task": "कार्य",
            "employee": "कर्मचारी",
            "status": "स्थिति",
            "monthly_attendance": "मासिक उपस्थिति रिपोर्ट",
            "employee_name": "कर्मचारी का नाम",
            "month": "महीना",
            "day": "दिन",
            "check_in": "आगमन",
            "check_out": "प्रस्थान",
            "task_calendar": "कार्य कैलेंडर",
            "scheduled_date": "निर्धारित तिथि",
        })
    # TODO: add more languages as needed (bn, te, mr, ta, etc.)
    return t

# ---------------------------------------------------------------------------
# PDF generation functions
# ---------------------------------------------------------------------------
def _build_pdf(title: str, data_lines: list, lang_code: str) -> io.BytesIO:
    """Create a simple PDF with title and lines."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Choose font
    if lang_code != "en":
        font_path = _find_noto_font()
        if font_path:
            try:
                pdfmetrics.registerFont(TTFont("NotoSans", font_path))
                font_name = "NotoSans"
            except:
                font_name = "Helvetica"
        else:
            font_name = "Helvetica"
    else:
        font_name = "Helvetica"

    p.setFont(font_name, 12)
    p.drawCentredString(w/2, h - 30*mm, title)

    p.setFont(font_name, 9)
    y = h - 40*mm
    for line in data_lines:
        if isinstance(line, str):
            p.drawString(20*mm, y, line)
            y -= 5*mm
            if y < 20*mm:
                p.showPage()
                y = h - 30*mm
                p.setFont(font_name, 9)

    p.save()
    buffer.seek(0)
    return buffer

def _generate_daily_handout(db, selected_date, lang_code):
    """Fetch tasks for a given date and format as PDF."""
    trans = get_translations(lang_code)
    date_str = selected_date.isoformat()
    tasks = db.fetch_all("scheduled_tasks")
    day_tasks = [t for t in tasks if t.get("scheduled_date","") == date_str] if tasks else []

    title = f"{trans['daily_handout']} - {selected_date.strftime('%d/%m/%Y')}"
    lines = [f"{trans['date']}: {selected_date.strftime('%d/%m/%Y')}", "", ""]

    if not day_tasks:
        lines.append("No tasks scheduled for this day.")
    else:
        # Fetch batch names and employee names for readability
        batches = {b['id']: b['batch_code'] for b in db.fetch_all("plant_batches")}
        employees = {e['id']: e['name'] for e in db.fetch_all("employees")}
        templates = {t['id']: t['name'] for t in db.fetch_all("task_templates")}

        lines.append(f"{'ID':<5} {'Batch':<15} {'Task':<20} {'Assigned To':<15} {'Status':<10}")
        for t in day_tasks:
            batch_name = batches.get(t.get("batch_id"), "?")
            task_name = templates.get(t.get("template_id"), "?")
            emp_name = employees.get(t.get("assigned_to"), "?")
            status = t.get("status","?")
            lines.append(f"{t['id']:<5} {batch_name[:15]:<15} {task_name[:20]:<20} {emp_name[:15]:<15} {status:<10}")

    return _build_pdf(title, lines, lang_code)

def _generate_monthly_attendance(db, emp_id, month, lang_code):
    """Fetch attendance records for one employee in a month."""
    trans = get_translations(lang_code)
    emp = next((e for e in db.fetch_all("employees") if e['id']==emp_id), None)
    emp_name = emp['name'] if emp else str(emp_id)

    # Get all attendance records for the month
    start_date = month.replace(day=1)
    if month.month == 12:
        end_date = month.replace(year=month.year+1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = month.replace(month=month.month+1, day=1) - timedelta(days=1)

    records = db.fetch_all("attendance")
    month_records = []
    for r in records:
        if r.get("employee_id") == emp_id and r.get("check_in"):
            r_date = datetime.fromisoformat(r["check_in"]).date()
            if start_date <= r_date <= end_date:
                month_records.append(r)

    # Sort by date
    month_records.sort(key=lambda x: x["check_in"])

    title = f"{trans['monthly_attendance']} - {emp_name} ({month.strftime('%B %Y')})"
    lines = [
        f"{trans['employee_name']}: {emp_name}",
        f"{trans['month']}: {month.strftime('%B %Y')}",
        "", ""
    ]
    if not month_records:
        lines.append("No attendance records found for this month.")
    else:
        lines.append(f"{'Date':<12} {trans['day']:<10} {trans['check_in']:<20} {trans['check_out']:<20}")
        for r in month_records:
            dt = datetime.fromisoformat(r["check_in"])
            day_name = dt.strftime("%A")
            check_in = dt.strftime("%H:%M:%S")
            check_out = datetime.fromisoformat(r["check_out"]).strftime("%H:%M:%S") if r.get("check_out") else "N/A"
            lines.append(f"{dt.strftime('%d/%m/%Y'):<12} {day_name[:10]:<10} {check_in:<20} {check_out:<20}")

    return _build_pdf(title, lines, lang_code)

def _generate_task_calendar(db, month, lang_code):
    """Generate a list of all tasks for a given month."""
    trans = get_translations(lang_code)
    tasks = db.fetch_all("scheduled_tasks")
    if not tasks:
        return _build_pdf(trans['task_calendar'], ["No tasks."], lang_code)

    start_date = month.replace(day=1)
    if month.month == 12:
        end_date = month.replace(year=month.year+1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = month.replace(month=month.month+1, day=1) - timedelta(days=1)

    month_tasks = []
    for t in tasks:
        sched = t.get("scheduled_date","")
        if sched:
            d = datetime.strptime(sched, "%Y-%m-%d").date()
            if start_date <= d <= end_date:
                month_tasks.append(t)

    month_tasks.sort(key=lambda x: x["scheduled_date"])

    batches = {b['id']: b['batch_code'] for b in db.fetch_all("plant_batches")}
    employees = {e['id']: e['name'] for e in db.fetch_all("employees")}
    templates = {t['id']: t['name'] for t in db.fetch_all("task_templates")}

    title = f"{trans['task_calendar']} - {month.strftime('%B %Y')}"
    lines = [f"{trans['month']}: {month.strftime('%B %Y')}", "", ""]
    if not month_tasks:
        lines.append("No tasks scheduled for this month.")
    else:
        lines.append(f"{trans['scheduled_date']:<14} {trans['batch']:<15} {trans['task']:<20} {trans['employee']:<15} {trans['status']:<10}")
        for t in month_tasks:
            d = t["scheduled_date"]
            batch = batches.get(t.get("batch_id"), "?")[:15]
            task = templates.get(t.get("template_id"), "?")[:20]
            emp = employees.get(t.get("assigned_to"), "?")[:15]
            status = t.get("status","?")
            lines.append(f"{d:<14} {batch:<15} {task:<20} {emp:<15} {status:<10}")

    return _build_pdf(title, lines, lang_code)

# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render(db):
    st.title("🌿 Nursery Operations")
    st.caption("Plant lifecycle, task scheduling, workforce, compliance, and reports")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🪴 Plant Lifecycle",
        "📅 Task Calendar",
        "👷 Workforce",
        "📊 Compliance",
        "📄 Reports & Printouts"
    ])

    with tab1:
        _render_plant_lifecycle(db)
    with tab2:
        _render_task_calendar(db)
    with tab3:
        _render_workforce(db)
    with tab4:
        _render_compliance(db)
    with tab5:
        _render_reports(db)

# ---------------------------------------------------------------------------
# 1. PLANT LIFECYCLE (unchanged)
# ---------------------------------------------------------------------------
def _render_plant_lifecycle(db):
    st.subheader("Plant Batches & Growth Stages")
    mode = st.radio("Action", ["View Batches", "Add New Batch", "Update Batch Stage"],
                    key="lifecycle_mode", horizontal=True)

    if mode == "View Batches":
        batches = db.fetch_all("plant_batches")
        if batches:
            df = pd.DataFrame(batches)
            if "start_date" in df.columns:
                df["start_date"] = pd.to_datetime(df["start_date"]).dt.date
                df = df.sort_values("start_date", ascending=False)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No batches recorded yet.")

    elif mode == "Add New Batch":
        with st.form("add_batch"):
            plants = db.fetch_all("plants")
            plant_options = {p['id']: p.get('name', '') for p in plants}
            if not plant_options:
                st.warning("No plants in database. Add plants first.")
                st.form_submit_button("Save Batch", disabled=True)
            else:
                plant_id = st.selectbox("Plant", options=list(plant_options.keys()),
                                        format_func=lambda x: plant_options[x])
                batch_code = st.text_input("Batch Code *")
                stage = st.selectbox("Initial Stage", [
                    "seed", "propagation", "germination", "seedling", "transplanting",
                    "vegetative", "flowering", "fruiting", "ready_for_sale", "sold", "disposed"
                ])
                start_date = st.date_input("Start Date", value=date.today())
                location = st.text_input("Location (e.g., Greenhouse A)")
                quantity = st.number_input("Quantity", min_value=1, value=1)
                notes = st.text_area("Notes")
                if st.form_submit_button("Save Batch"):
                    if not batch_code:
                        st.error("Batch code is required.")
                    else:
                        data = {
                            "plant_id": plant_id,
                            "batch_code": batch_code,
                            "stage": stage,
                            "start_date": start_date.isoformat(),
                            "location": location,
                            "quantity": quantity,
                            "notes": notes
                        }
                        if db.insert_one("plant_batches", data):
                            st.success("Batch created!")
                            st.rerun()
                        else:
                            st.error("Failed to save batch.")

    elif mode == "Update Batch Stage":
        batches = db.fetch_all("plant_batches")
        if not batches:
            st.info("No batches.")
            return
        df = pd.DataFrame(batches)
        sel_id = st.selectbox("Select Batch", df["id"],
                              format_func=lambda x: f"{df[df['id']==x].iloc[0]['batch_code']} (Stage: {df[df['id']==x].iloc[0]['stage']})")
        current = df[df['id'] == sel_id].iloc[0]
        with st.form("update_batch"):
            st.write(f"Current Stage: **{current['stage']}**")
            new_stage = st.selectbox("New Stage", [
                "seed", "propagation", "germination", "seedling", "transplanting",
                "vegetative", "flowering", "fruiting", "ready_for_sale", "sold", "disposed"
            ])
            notes = st.text_area("Update Notes", value=current.get("notes", ""))
            if st.form_submit_button("Update Stage"):
                data = {"stage": new_stage, "notes": notes}
                if db.update_one("plant_batches", sel_id, data):
                    st.success("Stage updated!")
                    st.rerun()
                else:
                    st.error("Update failed.")

# ---------------------------------------------------------------------------
# 2. TASK CALENDAR (unchanged)
# ---------------------------------------------------------------------------
def _render_task_calendar(db):
    st.subheader("Task Calendar & Scheduling")

    sub = st.radio("View", ["Today's Tasks", "All Scheduled Tasks", "Create Task", "Manage Templates"],
                   key="task_view", horizontal=True)

    if sub == "Today's Tasks":
        today = date.today().isoformat()
        all_tasks = db.fetch_all("scheduled_tasks")
        today_tasks = [t for t in all_tasks if t.get("scheduled_date", "") == today] if all_tasks else []
        if today_tasks:
            df = pd.DataFrame(today_tasks)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No tasks scheduled for today.")

    elif sub == "All Scheduled Tasks":
        tasks = db.fetch_all("scheduled_tasks")
        if tasks:
            df = pd.DataFrame(tasks)
            if "scheduled_date" in df.columns:
                df["scheduled_date"] = pd.to_datetime(df["scheduled_date"]).dt.date
            st.dataframe(df, use_container_width=True)

            st.subheader("Update Task Status")
            task_id = st.selectbox("Task ID", df["id"],
                                   format_func=lambda x: f"Task {x} – {df[df['id']==x].iloc[0].get('status','')}")
            new_status = st.selectbox("New Status", ["pending", "in_progress", "completed", "verified", "cancelled"])
            if st.button("Update Status"):
                if db.update_one("scheduled_tasks", task_id, {"status": new_status}):
                    st.success("Status updated!")
                    st.rerun()
                else:
                    st.error("Update failed.")
        else:
            st.info("No tasks in the system.")

    elif sub == "Manage Templates":
        templates = db.fetch_all("task_templates")
        if templates:
            df = pd.DataFrame(templates)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No templates yet.")
        st.markdown("---")
        with st.form("new_template"):
            st.subheader("Add New Template")
            tname = st.text_input("Template Name *")
            tcat = st.text_input("Category (e.g., Water, Fertilizer)")
            tinstr = st.text_area("Instructions")
            test_min = st.number_input("Estimated Minutes", min_value=0, value=10)
            if st.form_submit_button("Save Template"):
                if tname:
                    db.insert_one("task_templates", {
                        "name": tname,
                        "category": tcat,
                        "instructions": tinstr,
                        "estimated_minutes": test_min
                    })
                    st.success("Template created!")
                    st.rerun()
                else:
                    st.error("Template name required.")

    elif sub == "Create Task":
        batches = db.fetch_all("plant_batches")
        templates = db.fetch_all("task_templates")
        employees = db.fetch_all("employees")

        if not batches:
            st.warning("No batches exist. Create a batch first.")
            return
        if not templates:
            st.warning("No task templates. Create one under 'Manage Templates'.")
            return
        if not employees:
            st.warning("No employees. Add them in the Workforce tab.")
            return

        with st.form("create_task"):
            batch_id = st.selectbox("Batch", [b['id'] for b in batches],
                                    format_func=lambda x: next((b['batch_code'] for b in batches if b['id']==x), ""))
            template_id = st.selectbox("Task Template", [t['id'] for t in templates],
                                       format_func=lambda x: next((t['name'] for t in templates if t['id']==x), ""))
            scheduled_date = st.date_input("Scheduled Date", value=date.today())
            assignee = st.selectbox("Assign To", [e['id'] for e in employees],
                                    format_func=lambda x: next((e['name'] for e in employees if e['id']==x), ""))
            if st.form_submit_button("Schedule Task"):
                data = {
                    "batch_id": batch_id,
                    "template_id": template_id,
                    "scheduled_date": scheduled_date.isoformat(),
                    "assigned_to": assignee,
                    "status": "pending"
                }
                if db.insert_one("scheduled_tasks", data):
                    st.success("Task scheduled!")
                    st.rerun()
                else:
                    st.error("Failed.")

# ---------------------------------------------------------------------------
# 3. WORKFORCE (unchanged)
# ---------------------------------------------------------------------------
def _render_workforce(db):
    st.subheader("Employees & Attendance")
    mode = st.radio("Action", ["Employee List", "Add Employee", "Attendance Check-In"],
                    key="wf_mode", horizontal=True)

    if mode == "Employee List":
        employees = db.fetch_all("employees")
        if employees:
            df = pd.DataFrame(employees)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No employees registered.")

    elif mode == "Add Employee":
        with st.form("add_employee"):
            name = st.text_input("Full Name *")
            role = st.text_input("Role")
            mobile = st.text_input("Mobile")
            daily_wage = st.number_input("Daily Wage (₹)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Add Employee"):
                if not name:
                    st.error("Name required.")
                else:
                    data = {"name": name, "role": role, "mobile": mobile, "daily_wage": daily_wage}
                    if db.insert_one("employees", data):
                        st.success("Employee added!")
                        st.rerun()
                    else:
                        st.error("Failed.")

    elif mode == "Attendance Check-In":
        employees = db.fetch_all("employees")
        if not employees:
            st.info("No employees.")
            return
        emp_id = st.selectbox("Select Employee", [e['id'] for e in employees],
                              format_func=lambda x: next((e['name'] for e in employees if e['id']==x), ""))
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Check-In"):
                now = datetime.now().isoformat()
                if db.insert_one("attendance", {"employee_id": emp_id, "check_in": now}):
                    st.success(f"Check-in recorded at {now}")
                else:
                    st.error("Failed.")
        with col2:
            today_iso = date.today().isoformat()
            records = db.fetch_all("attendance")
            if records:
                today_record = None
                for r in records:
                    if r.get("check_in"):
                        r_date = r["check_in"][:10]
                        if r["employee_id"] == emp_id and r_date == today_iso and r.get("check_out") is None:
                            today_record = r
                            break
                if today_record:
                    if st.button("Check-Out"):
                        now = datetime.now().isoformat()
                        if db.update_one("attendance", today_record["id"], {"check_out": now}):
                            st.success(f"Check-out recorded at {now}")
                            st.rerun()
                        else:
                            st.error("Failed.")
                else:
                    st.info("No open check-in for today.")
            else:
                st.info("No attendance records.")

# ---------------------------------------------------------------------------
# 4. COMPLIANCE (unchanged)
# ---------------------------------------------------------------------------
def _render_compliance(db):
    st.subheader("Task Compliance Overview")
    tasks = db.fetch_all("scheduled_tasks")
    if not tasks:
        st.info("No tasks yet.")
        return
    df = pd.DataFrame(tasks)
    if "status" not in df.columns or "scheduled_date" not in df.columns:
        st.info("Incomplete task data.")
        return

    total = len(df)
    completed = len(df[df['status'].isin(['completed', 'verified'])])
    pending = len(df[df['status'] == 'pending'])
    today = date.today()
    overdue = len(df[(df['status'] == 'pending') & (pd.to_datetime(df['scheduled_date']).dt.date < today)])
    compliance_pct = (completed / total) * 100 if total else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tasks", total)
    col2.metric("Completed", completed)
    col3.metric("Pending", pending)
    col4.metric("Overdue", overdue)

    st.progress(compliance_pct / 100)
    st.caption(f"Overall Compliance: {compliance_pct:.1f}%")

    if overdue > 0:
        st.warning(f"{overdue} task(s) are past due date and still pending.")
        overdue_tasks = df[(df['status'] == 'pending') & (pd.to_datetime(df['scheduled_date']).dt.date < today)]
        st.dataframe(overdue_tasks[["id", "batch_id", "scheduled_date", "assigned_to"]], use_container_width=True)

# ---------------------------------------------------------------------------
# 5. REPORTS & PRINTOUTS (NEW)
# ---------------------------------------------------------------------------
def _render_reports(db):
    st.subheader("📄 Reports & Printouts")
    st.markdown("Generate printable reports in your preferred language.")

    col_lang, col_report = st.columns(2)
    with col_lang:
        selected_lang_label = st.selectbox("Report Language", list(INDIAN_LANGUAGES.keys()))
        lang_code = INDIAN_LANGUAGES[selected_lang_label]
    with col_report:
        report_type = st.selectbox("Report Type", [
            "Daily Task Handout",
            "Monthly Attendance Report",
            "Monthly Task Calendar"
        ])

    # Parameters depending on report type
    if report_type == "Daily Task Handout":
        selected_date = st.date_input("Select Date", value=date.today())
        if st.button("Generate Handout PDF"):
            pdf = _generate_daily_handout(db, selected_date, lang_code)
            st.success("Handout ready!")
            st.download_button("📥 Download PDF", pdf, f"daily_tasks_{selected_date}.pdf", "application/pdf")

    elif report_type == "Monthly Attendance Report":
        col_emp, col_month = st.columns(2)
        with col_emp:
            employees = db.fetch_all("employees")
            if not employees:
                st.warning("No employees found.")
                return
            emp_id = st.selectbox("Employee", [e['id'] for e in employees],
                                  format_func=lambda x: next((e['name'] for e in employees if e['id']==x), ""))
        with col_month:
            month = st.date_input("Month", value=date.today().replace(day=1))
        if st.button("Generate Attendance Report"):
            pdf = _generate_monthly_attendance(db, emp_id, month, lang_code)
            st.success("Attendance report ready!")
            st.download_button("📥 Download PDF", pdf, f"attendance_{emp_id}_{month.strftime('%Y%m')}.pdf", "application/pdf")

    elif report_type == "Monthly Task Calendar":
        month = st.date_input("Select Month", value=date.today().replace(day=1))
        if st.button("Generate Task Calendar PDF"):
            pdf = _generate_task_calendar(db, month, lang_code)
            st.success("Task calendar ready!")
            st.download_button("📥 Download PDF", pdf, f"task_calendar_{month.strftime('%Y%m')}.pdf", "application/pdf")
