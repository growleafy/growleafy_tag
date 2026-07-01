"""
Nursery Operations – Phase 1: Plant Lifecycle, Task Calendar, Workforce, Compliance
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# Helper: Safe date parsing
# ---------------------------------------------------------------------------
def _parse_date(val):
    if isinstance(val, (date, datetime)):
        return val
    if isinstance(val, str):
        try:
            return datetime.strptime(val[:10], "%Y-%m-%d").date()
        except:
            pass
    return None

# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render(db):
    st.title("🌿 Nursery Operations")
    st.caption("Plant lifecycle, task scheduling, workforce, and compliance")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🪴 Plant Lifecycle",
        "📅 Task Calendar",
        "👷 Workforce",
        "📊 Compliance"
    ])

    with tab1:
        _render_plant_lifecycle(db)
    with tab2:
        _render_task_calendar(db)
    with tab3:
        _render_workforce(db)
    with tab4:
        _render_compliance(db)

# ---------------------------------------------------------------------------
# 1. PLANT LIFECYCLE
# ---------------------------------------------------------------------------
def _render_plant_lifecycle(db):
    st.subheader("Plant Batches & Growth Stages")

    mode = st.radio("Action", ["View Batches", "Add New Batch", "Update Batch Stage"],
                    key="lifecycle_mode", horizontal=True)

    if mode == "View Batches":
        batches = db.fetch_all("plant_batches")
        if batches:
            df = pd.DataFrame(batches)
            # Sort by start_date descending
            if "start_date" in df.columns:
                df["start_date"] = pd.to_datetime(df["start_date"]).dt.date
                df = df.sort_values("start_date", ascending=False)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No batches recorded yet.")

    elif mode == "Add New Batch":
        with st.form("add_batch"):
            # Select plant from plants table
            plants = db.fetch_all("plants")
            plant_options = {p['id']: p.get('name','') for p in plants}
            plant_id = st.selectbox("Plant", options=list(plant_options.keys()),
                                    format_func=lambda x: plant_options[x])

            batch_code = st.text_input("Batch Code *")
            stage = st.selectbox("Initial Stage", [
                "seed","propagation","germination","seedling","transplanting",
                "vegetative","flowering","fruiting","ready_for_sale","sold","disposed"
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
                "seed","propagation","germination","seedling","transplanting",
                "vegetative","flowering","fruiting","ready_for_sale","sold","disposed"
            ])
            notes = st.text_area("Update Notes")
            if st.form_submit_button("Update Stage"):
                data = {"stage": new_stage, "notes": (notes if notes else current.get("notes",""))}
                if db.update_one("plant_batches", sel_id, data):
                    st.success("Stage updated!")
                    st.rerun()
                else:
                    st.error("Update failed.")

# ---------------------------------------------------------------------------
# 2. TASK CALENDAR
# ---------------------------------------------------------------------------
def _render_task_calendar(db):
    st.subheader("Task Calendar & Scheduling")

    sub = st.radio("View", ["Today's Tasks", "All Scheduled Tasks", "Create Task"],
                   key="task_view", horizontal=True)

    if sub == "Today's Tasks":
        today = date.today().isoformat()
        all_tasks = db.fetch_all("scheduled_tasks")
        today_tasks = [t for t in all_tasks if t.get("scheduled_date","") == today] if all_tasks else []
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

            # Quick status update
            st.subheader("Update Task Status")
            task_id = st.selectbox("Task ID", df["id"],
                                   format_func=lambda x: f"Task {x} – {df[df['id']==x].iloc[0].get('status','')}")
            new_status = st.selectbox("New Status", ["pending","in_progress","completed","verified","cancelled"])
            if st.button("Update Status"):
                if db.update_one("scheduled_tasks", task_id, {"status": new_status}):
                    st.success("Status updated!")
                    st.rerun()
                else:
                    st.error("Update failed.")
        else:
            st.info("No tasks in the system.")

    elif sub == "Create Task":
        batches = db.fetch_all("plant_batches")
        templates = db.fetch_all("task_templates")
        employees = db.fetch_all("employees")

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
# 3. WORKFORCE
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
            # Find today's attendance record for this employee and set check-out
            today_iso = date.today().isoformat()
            records = db.fetch_all("attendance")
            if records:
                today_record = None
                for r in records:
                    r_date = r.get("check_in","")[:10]
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
# 4. COMPLIANCE DASHBOARD
# ---------------------------------------------------------------------------
def _render_compliance(db):
    st.subheader("Task Compliance Overview")
    tasks = db.fetch_all("scheduled_tasks")
    if not tasks:
        st.info("No tasks yet.")
        return
    df = pd.DataFrame(tasks)
    if "status" not in df.columns:
        st.info("No status data.")
        return
    total = len(df)
    completed = len(df[df['status'].isin(['completed','verified'])])
    pending = len(df[df['status'] == 'pending'])
    overdue = len(df[(df['status'] == 'pending') & (pd.to_datetime(df['scheduled_date']).dt.date < date.today())])
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
        overdue_tasks = df[(df['status'] == 'pending') & (pd.to_datetime(df['scheduled_date']).dt.date < date.today())]
        st.dataframe(overdue_tasks[["id","batch_id","scheduled_date"]], use_container_width=True)
