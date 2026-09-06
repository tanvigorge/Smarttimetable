import json
import os
from datetime import date, datetime

import streamlit as st

from calendar_api import create_calendar_event, fetch_upcoming_events, get_calendar_service
from google_calendar_component import request_google_access_token
from scheduling import (
    CLASS_TYPES,
    DAYS,
    INDIAN_ACADEMIC_CALENDAR,
    PRIORITIES,
    calculate_analytics,
    find_free_slots,
    find_schedule_conflicts,
    parse_scheduling_request,
    recommend_study_sessions,
    validate_time_range,
)
from reminder_api import build_reminders, send_email_reminder, smtp_defaults
from workflow_api import load_workflows, now_iso, save_workflows

SCHEDULE_FILE = "schedule.json"
WORKFLOW_FILE = "workflows.json"
ACADEMIC_FILE = "academic_data.json"


def load_schedule(file_path=SCHEDULE_FILE):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return []
    return []


def save_schedule(schedule, file_path=SCHEDULE_FILE):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(schedule, file, indent=2)


def load_academic_data(file_path=ACADEMIC_FILE):
    if not os.path.exists(file_path):
        return {"semester": {}, "assignments": [], "exams": []}
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return {
            "semester": data.get("semester", {}),
            "assignments": data.get("assignments", []),
            "exams": data.get("exams", []),
        }
    except (OSError, json.JSONDecodeError):
        return {"semester": {}, "assignments": [], "exams": []}


def save_academic_data(data, file_path=ACADEMIC_FILE):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def build_weekly_calendar(schedule):
    calendar = {day: [] for day in DAYS}
    for item in schedule:
        for day in item.get("days", []):
            calendar.setdefault(day, []).append(
                f"{item['start_time']} - {item['end_time']}: {item['course_name']}"
                + (f" @ {item['location']}" if item.get("location") else "")
            )
    return calendar


st.set_page_config(page_title="Smart Timetable Assistant", page_icon="📅")
st.title("📅 Smart Timetable Assistant")
st.write("A simple assistant to manage your classes, assignments, and events.")

if "service" not in st.session_state:
    st.session_state.service = None

if "calendar_access_token" not in st.session_state:
    st.session_state.calendar_access_token = None

if "calendar_auth_request" not in st.session_state:
    st.session_state.calendar_auth_request = None

if "schedule" not in st.session_state:
    st.session_state.schedule = load_schedule()

if "workflows" not in st.session_state:
    st.session_state.workflows = load_workflows(WORKFLOW_FILE)

if "academic_data" not in st.session_state:
    st.session_state.academic_data = load_academic_data()

if st.session_state.service is not None:
    st.success("✓ Google Calendar Connected")
elif st.button("Connect to Google Calendar"):
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        st.error("Google Calendar is not configured. Add GOOGLE_CLIENT_ID to .env and restart the app.")
    else:
        st.session_state.calendar_auth_request = datetime.now().isoformat()
        st.rerun()

if st.session_state.calendar_auth_request and st.session_state.service is None:
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    auth_result = request_google_access_token(client_id, st.session_state.calendar_auth_request)
    if auth_result:
        st.session_state.calendar_auth_request = None
        if auth_result.get("status") == "connected":
            try:
                st.session_state.calendar_access_token = auth_result["access_token"]
                st.session_state.service = get_calendar_service(st.session_state.calendar_access_token)
                st.rerun()
            except Exception:
                st.session_state.calendar_access_token = None
                st.error("Unable to connect to Google Calendar.")
        else:
            st.error(auth_result.get("message", "Unable to connect to Google Calendar."))

st.header("Class Schedule")
with st.form("schedule_form"):
    course_name = st.text_input("Course name")
    days = st.multiselect(
        "Days of the week",
        DAYS,
        default=["Monday"],
    )
    semester = st.text_input("Semester / term", placeholder="2026 Spring")
    class_type = st.selectbox("Class type", CLASS_TYPES)
    start_time_class = st.text_input("Start time (HH:MM)", value="09:00")
    end_time_class = st.text_input("End time (HH:MM)", value="10:00")
    location = st.text_input("Location")
    notes = st.text_area("Notes")
    add_class = st.form_submit_button("Save Class")

if add_class:
    if not course_name:
        st.warning("Please enter a course name.")
    elif not days:
        st.warning("Please select at least one day.")
    else:
        try:
            validate_time_range(start_time_class, end_time_class)
            new_schedule_item = {
                "course_name": course_name,
                "days": days,
                "semester": semester.strip(),
                "class_type": class_type,
                "start_time": start_time_class,
                "end_time": end_time_class,
                "location": location,
                "notes": notes,
            }
            conflicts = find_schedule_conflicts(new_schedule_item, st.session_state.schedule)
            if conflicts:
                conflict = conflicts[0]
                st.error(
                    f"Schedule conflict with {conflict['course_name']} on {', '.join(conflict['days'])} "
                    f"({conflict['start_time']} - {conflict['end_time']})."
                )
            else:
                st.session_state.schedule.append(new_schedule_item)
                save_schedule(st.session_state.schedule)
                st.success("Class schedule saved successfully.")
        except ValueError:
            st.error("Use HH:MM and make sure the end time is after the start time.")

if st.session_state.schedule:
    st.subheader("Saved Class Schedule")
    st.table(st.session_state.schedule)

    st.subheader("Weekly Calendar")
    weekly_calendar = build_weekly_calendar(st.session_state.schedule)
    columns = st.columns(7)
    for idx, day in enumerate(weekly_calendar):
        with columns[idx]:
            st.write(f"**{day}**")
            events = weekly_calendar[day]
            if events:
                for event in events:
                    st.write(f"- {event}")
            else:
                st.write("No classes")
else:
    st.info("Add a class schedule item to save it here.")

st.header("Scheduling Assistant")
st.caption("Use a simple request to add a recurring class or find an open study slot.")
with st.form("assistant_form"):
    assistant_request = st.text_input("Scheduling request", placeholder="find free time tomorrow")
    assistant_submit = st.form_submit_button("Process request")

if assistant_submit:
    try:
        request_result = parse_scheduling_request(assistant_request)
        if request_result["intent"] == "free_time":
            free_slots = find_free_slots(st.session_state.schedule, request_result["date"])
            if free_slots:
                st.success(f"Open slots on {request_result['date'].strftime('%A, %d %B')}")
                st.table(free_slots)
            else:
                st.warning("No one-hour slot is available between 08:00 and 20:00.")
        else:
            assistant_class = {
                "course_name": request_result["course_name"],
                "days": request_result["days"],
                "semester": st.session_state.academic_data["semester"].get("name", ""),
                "class_type": "Lecture",
                "start_time": request_result["start_time"],
                "end_time": request_result["end_time"],
                "location": "",
                "notes": "Added through scheduling assistant",
            }
            conflicts = find_schedule_conflicts(assistant_class, st.session_state.schedule)
            if conflicts:
                conflict = conflicts[0]
                st.error(f"Conflict with {conflict['course_name']} on {', '.join(conflict['days'])}.")
            else:
                st.session_state.schedule.append(assistant_class)
                save_schedule(st.session_state.schedule)
                st.success(f"Added {assistant_class['course_name']} to the recurring schedule.")
    except ValueError as error:
        st.error(str(error))

st.header("Academic Planner")
academic_data = st.session_state.academic_data
with st.expander("Semester template", expanded=not academic_data["semester"]):
    with st.form("semester_form"):
        term_name = st.text_input("Term name", value=academic_data["semester"].get("name", ""))
        term_start = st.date_input("Term start", value=datetime.strptime(academic_data["semester"].get("start", "2026-01-01"), "%Y-%m-%d").date())
        term_end = st.date_input("Term end", value=datetime.strptime(academic_data["semester"].get("end", "2026-05-31"), "%Y-%m-%d").date())
        save_term = st.form_submit_button("Save semester template")
    if save_term:
        if term_end <= term_start:
            st.error("Term end must be after term start.")
        elif not term_name.strip():
            st.error("Enter a term name.")
        else:
            academic_data["semester"] = {"name": term_name.strip(), "start": term_start.isoformat(), "end": term_end.isoformat()}
            save_academic_data(academic_data)
            st.success("Semester template saved.")

with st.expander("Assignments and exams"):
    with st.form("academic_item_form", clear_on_submit=True):
        item_kind = st.selectbox("Item", ["Assignment", "Exam"])
        subject = st.text_input("Subject")
        item_title = st.text_input("Title", placeholder="Data structures lab")
        due_date = st.date_input("Due / exam date")
        priority = st.selectbox("Priority", PRIORITIES, index=1)
        estimated_hours = st.number_input("Estimated study hours", min_value=0.5, max_value=40.0, value=2.0, step=0.5)
        save_item = st.form_submit_button("Add academic item")
    if save_item:
        if not subject.strip() or not item_title.strip():
            st.error("Subject and title are required.")
        else:
            if item_kind == "Exam":
                academic_data["exams"].append({"subject": subject.strip(), "exam_date": due_date.isoformat()})
            else:
                academic_data["assignments"].append({"subject": subject.strip(), "title": item_title.strip(), "due_date": due_date.isoformat(), "priority": priority, "estimated_hours": estimated_hours, "completed": False})
            save_academic_data(academic_data)
            st.success(f"{item_kind} added.")

    recommendations = recommend_study_sessions(academic_data["assignments"], academic_data["exams"])
    if recommendations:
        st.subheader("Recommended study queue")
        for recommendation in recommendations[:5]:
            st.write(f"**{recommendation['title']}**: {recommendation['minutes']} min | {recommendation['reason']}")
    if academic_data["assignments"]:
        st.dataframe(academic_data["assignments"], use_container_width=True)
        for assignment_index, assignment in enumerate(academic_data["assignments"]):
            completed = st.checkbox(
                f"Completed: {assignment['subject']} - {assignment['title']}",
                value=assignment.get("completed", False),
                key=f"assignment_completed_{assignment_index}",
            )
            if completed != assignment.get("completed", False):
                assignment["completed"] = completed
                save_academic_data(academic_data)
    if academic_data["exams"]:
        st.dataframe(academic_data["exams"], use_container_width=True)

st.subheader("Indian academic calendar")
st.dataframe(INDIAN_ACADEMIC_CALENDAR, use_container_width=True, hide_index=True)

analytics = calculate_analytics(st.session_state.schedule, academic_data["assignments"], academic_data["exams"])
metric_columns = st.columns(4)
metric_columns[0].metric("Weekly class hours", analytics["weekly_class_hours"])
metric_columns[1].metric("Study hours remaining", analytics["outstanding_assignment_hours"])
metric_columns[2].metric("Assignment completion", f"{analytics['assignment_completion_rate']}%")
metric_columns[3].metric("Upcoming exams", analytics["upcoming_exams"])

st.header("Reminders")
reminder_items = build_reminders(
    [dict(item, due_date=date.fromisoformat(item["due_date"])) for item in academic_data["assignments"]],
    [dict(item, exam_date=date.fromisoformat(item["exam_date"])) for item in academic_data["exams"]],
    date.today(),
)
if reminder_items:
    st.warning(f"{len(reminder_items)} academic reminder(s) due within three days.")
    st.dataframe(reminder_items, use_container_width=True, hide_index=True)
else:
    st.info("No assignments or exams are due within the next three days.")

with st.expander("Send reminders by email"):
    defaults = smtp_defaults()
    with st.form("reminder_form"):
        recipient = st.text_input("Recipient email")
        smtp_host = st.text_input("SMTP host", value=defaults["host"])
        smtp_port = st.number_input("SMTP port", min_value=1, max_value=65535, value=defaults["port"])
        smtp_user = st.text_input("SMTP username", value=defaults["user"])
        smtp_password = st.text_input("SMTP password or app password", type="password")
        send_reminders = st.form_submit_button("Send email reminders")
    if send_reminders:
        try:
            send_email_reminder(reminder_items, recipient, smtp_host, smtp_port, smtp_user, smtp_password)
            st.success("Reminder email sent.")
        except (OSError, ValueError) as error:
            st.error(f"Could not send reminders: {error}")

st.header("Workflow Tracker")
if st.button("Refresh workflows"):
    st.session_state.workflows = load_workflows(WORKFLOW_FILE)
    st.rerun()

with st.form("workflow_form", clear_on_submit=True):
    workflow_title = st.text_input("Workflow title", placeholder="Prepare Friday lab report")
    workflow_description = st.text_area("Details", placeholder="Add the final checks and references")
    add_workflow = st.form_submit_button("Add Workflow")

if add_workflow:
    if not workflow_title.strip():
        st.warning("Please enter a workflow title.")
    else:
        st.session_state.workflows.append(
            {
                "id": str(len(st.session_state.workflows) + 1),
                "title": workflow_title.strip(),
                "description": workflow_description.strip(),
                "status": "pending",
                "created_at": now_iso(),
                "completed_at": None,
                "submitted_at": None,
            }
        )
        save_workflows(st.session_state.workflows, WORKFLOW_FILE)
        st.success("Workflow added.")

if st.session_state.workflows:
    status_counts = {
        status: sum(item["status"] == status for item in st.session_state.workflows)
        for status in ("pending", "completed", "submitted")
    }
    st.caption(
        f"Pending: {status_counts['pending']}  |  Completed: {status_counts['completed']}  |  Submitted: {status_counts['submitted']}"
    )
    for workflow in st.session_state.workflows:
        with st.container(border=True):
            st.write(f"**{workflow['title']}**")
            if workflow.get("description"):
                st.write(workflow["description"])
            st.caption(f"Status: {workflow['status'].replace('_', ' ').title()}")
            action_columns = st.columns(2)
            if workflow["status"] == "pending":
                if action_columns[0].button("Mark complete", key=f"complete_{workflow['id']}"):
                    workflow["status"] = "completed"
                    workflow["completed_at"] = now_iso()
                    save_workflows(st.session_state.workflows, WORKFLOW_FILE)
                    st.rerun()
            elif workflow["status"] == "completed":
                if action_columns[0].button("Submit completed workflow", key=f"submit_{workflow['id']}"):
                    workflow["status"] = "submitted"
                    workflow["submitted_at"] = now_iso()
                    save_workflows(st.session_state.workflows, WORKFLOW_FILE)
                    st.rerun()
            else:
                action_columns[0].success("Submitted")

st.header("Create a New Event")
with st.form("event_form"):
    title = st.text_input("Event title")
    start_time = st.text_input("Start time (YYYY-MM-DD HH:MM)", value="2026-07-10 09:00")
    end_time = st.text_input("End time (YYYY-MM-DD HH:MM)", value="2026-07-10 10:00")
    description = st.text_area("Description")
    submitted = st.form_submit_button("Add Event")

if submitted:
    if not title:
        st.warning("Please enter an event title.")
    elif st.session_state.service is None:
        st.warning("Please connect to Google Calendar first.")
    else:
        try:
            start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            if end_dt <= start_dt:
                st.error("End time must be after start time.")
            else:
                create_calendar_event(st.session_state.service, title, start_dt, end_dt, description)
                st.success("Event created successfully!")
        except ValueError:
            st.error("Please use the format YYYY-MM-DD HH:MM")
        except Exception as e:
            st.error(f"Could not create event: {e}")

st.header("Upcoming Events")
if st.session_state.service is None:
    st.info("Connect to Google Calendar to view your upcoming events.")
else:
    try:
        events = fetch_upcoming_events(st.session_state.service)
        if not events:
            st.write("No upcoming events found.")
        else:
            for event in events:
                start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
                st.write(f"- {event.get('summary', 'Untitled Event')} ({start})")
    except Exception as e:
        st.error(f"Could not fetch events: {e}")