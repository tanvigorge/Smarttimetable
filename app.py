import json
import os
from datetime import datetime

import streamlit as st

from academic_scheduler import (
    allocate_study_time,
    build_assignment_deadline,
    build_course_session,
    build_exam_schedule,
    build_reminder,
    generate_semester_template,
    generate_study_session_plan,
    get_indian_academic_calendar,
    parse_free_time_query,
)
from calendar_api import (
    create_calendar_event,
    fetch_upcoming_events,
    find_conflicts,
    get_calendar_service,
    parse_natural_language_request,
    suggest_next_free_slot,
)
from knowledge_system import TopicKnowledgeSystem

SCHEDULE_FILE = "schedule.json"
TOPIC_DOCUMENTS = [
    {
        "subject": "Biology",
        "chapter": "Cell Structure",
        "title": "Cells and Organelles",
        "content": "Cells contain organelles like mitochondria and ribosomes that help the cell function.",
    },
    {
        "subject": "Biology",
        "chapter": "Cell Structure",
        "title": "Mitochondria Basics",
        "content": "Mitochondria produce energy for the cell through respiration.",
    },
    {
        "subject": "Chemistry",
        "chapter": "Atoms",
        "title": "Atomic Structure",
        "content": "Atoms are made of protons, neutrons, and electrons.",
    },
]
TOPIC_KNOWLEDGE_SYSTEM = TopicKnowledgeSystem(TOPIC_DOCUMENTS)


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


def build_weekly_calendar(schedule):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    calendar = {day: [] for day in days}
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

if "schedule" not in st.session_state:
    st.session_state.schedule = load_schedule()

if "academic_schedule" not in st.session_state:
    st.session_state.academic_schedule = []

if "exam_schedule" not in st.session_state:
    st.session_state.exam_schedule = []

if "assignment_deadlines" not in st.session_state:
    st.session_state.assignment_deadlines = []

if "study_reminders" not in st.session_state:
    st.session_state.study_reminders = []

if st.button("Connect to Google Calendar"):
    try:
        service = get_calendar_service()
        st.session_state.service = service
        st.success("Connected to Google Calendar successfully!")
    except FileNotFoundError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Authentication failed: {e}")

st.header("Class Schedule")
with st.form("schedule_form"):
    course_name = st.text_input("Course name")
    days = st.multiselect(
        "Days of the week",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        default=["Monday"],
    )
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
            datetime.strptime(start_time_class, "%H:%M")
            datetime.strptime(end_time_class, "%H:%M")
            new_schedule_item = {
                "course_name": course_name,
                "days": days,
                "start_time": start_time_class,
                "end_time": end_time_class,
                "location": location,
                "notes": notes,
            }
            st.session_state.schedule.append(new_schedule_item)
            save_schedule(st.session_state.schedule)
            st.success("Class schedule saved successfully.")
        except ValueError:
            st.error("Please use the format HH:MM for start and end times.")

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

st.header("Academic Planner")
current_year = datetime.now().year
semester_template = generate_semester_template("Semester 1", current_year)
calendar_overview = get_indian_academic_calendar(current_year, "Semester 1")

st.subheader("Semester / Term Templates")
st.write(f"Template for {semester_template['term_name']} ({semester_template['year']}): {semester_template['week_count']} teaching weeks")
for break_entry in semester_template["breaks"]:
    st.write(f"- {break_entry['name']}: {break_entry['start_date']} to {break_entry['end_date']}")
for festival in semester_template["festival_holidays"][:5]:
    st.write(f"- {festival['name']} ({festival['month']})")

with st.form("academic_session_form"):
    academic_course = st.text_input("Course name")
    session_type = st.selectbox("Session type", ["Lecture", "Lab", "Tutorial", "Seminar"])
    session_day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    session_start = st.text_input("Start time (HH:MM)", value="09:00")
    session_end = st.text_input("End time (HH:MM)", value="10:00")
    academic_semester = st.selectbox("Semester", ["Semester 1", "Semester 2", "Summer Term"])
    academic_location = st.text_input("Location")
    academic_notes = st.text_area("Notes")
    add_academic_session = st.form_submit_button("Save Course Session")

if add_academic_session:
    if not academic_course:
        st.warning("Please enter a course name.")
    else:
        try:
            session = build_course_session(
                course_name=academic_course,
                session_type=session_type,
                day=session_day,
                start_time=session_start,
                end_time=session_end,
                semester=academic_semester,
                location=academic_location,
                notes=academic_notes,
            )
            st.session_state.academic_schedule.append(session)
            st.success("Course-specific session saved successfully.")
        except ValueError as exc:
            st.error(str(exc))

if st.session_state.academic_schedule:
    st.subheader("Course-Specific Schedule")
    st.table(st.session_state.academic_schedule)
else:
    st.info("Add lecture, lab, or tutorial sessions for your semester.")

with st.form("exam_form"):
    exam_course = st.text_input("Exam course")
    exam_title = st.text_input("Exam title")
    exam_date = st.text_input("Exam date (YYYY-MM-DD)", value="2026-10-15")
    exam_start = st.text_input("Exam start (HH:MM)", value="09:00")
    exam_end = st.text_input("Exam end (HH:MM)", value="10:30")
    exam_hours = st.number_input("Study hours", min_value=1, max_value=20, value=6)
    exam_priority = st.selectbox("Priority", ["low", "medium", "high"])
    exam_semester = st.selectbox("Semester", ["Semester 1", "Semester 2", "Summer Term"])
    add_exam = st.form_submit_button("Save Exam")

if add_exam:
    if not exam_course:
        st.warning("Please enter an exam course.")
    else:
        try:
            exam = build_exam_schedule(
                course_name=exam_course,
                exam_title=exam_title,
                exam_date=exam_date,
                start_time=exam_start,
                end_time=exam_end,
                study_hours=int(exam_hours),
                priority=exam_priority,
                semester=exam_semester,
            )
            st.session_state.exam_schedule.append(exam)
            st.success("Exam schedule saved successfully.")
        except ValueError as exc:
            st.error(str(exc))

if st.session_state.exam_schedule:
    st.subheader("Exam Schedule and Study Allocation")
    exam_table = st.session_state.exam_schedule
    st.table(exam_table)
    study_plan = allocate_study_time(exam_table, weekly_study_hours=12)
    st.write("Study time allocation:")
    st.table(study_plan)
else:
    st.info("Add exam dates to manage study time allocation.")

with st.form("assignment_form"):
    assignment_title = st.text_input("Assignment title")
    assignment_course = st.text_input("Course")
    assignment_due_date = st.text_input("Due date (YYYY-MM-DD)", value="2026-09-03")
    assignment_priority = st.selectbox("Priority", ["low", "medium", "high"])
    assignment_hours = st.number_input("Estimated hours", min_value=1, max_value=20, value=3)
    add_assignment = st.form_submit_button("Save Assignment")

if add_assignment:
    if not assignment_title or not assignment_course:
        st.warning("Please enter both assignment title and course.")
    else:
        try:
            assignment = build_assignment_deadline(
                assignment_title=assignment_title,
                course_name=assignment_course,
                due_date=assignment_due_date,
                priority=assignment_priority,
                estimated_hours=int(assignment_hours),
            )
            st.session_state.assignment_deadlines.append(assignment)
            st.success("Assignment deadline tracked successfully.")
        except ValueError as exc:
            st.error(str(exc))

if st.session_state.assignment_deadlines:
    st.subheader("Assignment Deadline Tracker")
    st.table(st.session_state.assignment_deadlines)
else:
    st.info("Add assignment deadlines with priority levels to track work.")

study_plan = generate_study_session_plan(st.session_state.assignment_deadlines, st.session_state.exam_schedule, daily_minutes=90)
if study_plan:
    st.subheader("Intelligent Study Session Scheduling")
    st.table(study_plan)
else:
    st.info("Add assignments or exams to generate an intelligent study session plan.")

with st.form("reminder_form"):
    reminder_title = st.text_input("Reminder title")
    reminder_time = st.text_input("Reminder time (YYYY-MM-DD HH:MM)", value="2026-09-02 18:00")
    reminder_channel = st.selectbox("Channel", ["email", "sms"])
    add_reminder = st.form_submit_button("Save Reminder")

if add_reminder:
    if not reminder_title:
        st.warning("Please enter a reminder title.")
    else:
        try:
            reminder = build_reminder(reminder_title, reminder_time, reminder_channel)
            st.session_state.study_reminders.append(reminder)
            st.success("Reminder created successfully.")
        except ValueError as exc:
            st.error(str(exc))

if st.session_state.study_reminders:
    st.subheader("Reminder System")
    st.table(st.session_state.study_reminders)
else:
    st.info("Create a reminder for email or SMS notifications.")

st.header("Free Time Query")
free_time_query = st.text_input("Ask for free time", value="find free time tomorrow for 90 minutes")
if st.button("Check free slot"):
    if not free_time_query.strip():
        st.warning("Please enter a free-time query.")
    else:
        parsed_query = parse_free_time_query(free_time_query, reference_date=datetime.now())
        st.info(f"Query parsed for {parsed_query['date']} with {parsed_query['duration_minutes']} minutes requested.")

st.header("Topic Knowledge Explorer")
knowledge_question = st.text_area(
    "Ask about a topic",
    value="How do cells produce energy?",
)
if st.button("Get Topic Insights"):
    if not knowledge_question.strip():
        st.warning("Please enter a topic question.")
    else:
        topic_result = TOPIC_KNOWLEDGE_SYSTEM.answer_question(knowledge_question)

        st.subheader("Study Mode")
        tab_explanation, tab_practice, tab_progression = st.tabs(["Explanation", "Practice", "Progression"])

        with tab_explanation:
            st.write(topic_result["explanation"])
            st.write(topic_result["answer"])
            if topic_result["references"]:
                st.write("**References**")
                for reference in topic_result["references"]:
                    st.write(f"- {reference['title']} ({reference['subject']} / {reference['chapter']})")

        with tab_practice:
            if topic_result["question_bank"]:
                for question in topic_result["question_bank"]:
                    st.write(f"- {question}")
            if topic_result["related_questions"]:
                st.write("**Related Questions**")
                for question in topic_result["related_questions"]:
                    st.write(f"- {question}")

        with tab_progression:
            for step in topic_result["learning_progression"]:
                st.write(f"- {step['stage'].title()}: {step['title']} — {step['description']}")

        st.subheader("Coverage")
        for subject, chapters in topic_result["coverage"].items():
            for chapter, count in chapters.items():
                st.write(f"- {subject} / {chapter}: {count} document(s)")

st.header("Natural Language Scheduling")
request_text = st.text_area(
    "Describe the event you want to schedule",
    value="Schedule a team sync tomorrow at 2pm for 1 hour",
)
if st.button("Process Scheduling Request"):
    if not request_text.strip():
        st.warning("Please enter a scheduling request.")
    elif st.session_state.service is None:
        st.warning("Please connect to Google Calendar first.")
    else:
        try:
            parsed_request = parse_natural_language_request(request_text, reference_date=datetime.now())
            st.info(
                f"Parsed request: {parsed_request['title']} from {parsed_request['start_dt'].strftime('%Y-%m-%d %H:%M')} to {parsed_request['end_dt'].strftime('%Y-%m-%d %H:%M')}"
            )
            existing_events = fetch_upcoming_events(st.session_state.service, max_results=20)
            conflicts = find_conflicts(parsed_request["start_dt"], parsed_request["end_dt"], existing_events)
            if conflicts:
                st.warning("This request overlaps with the following existing events:")
                for conflict in conflicts:
                    st.write(
                        f"- {conflict['summary']} ({conflict['start_dt'].strftime('%Y-%m-%d %H:%M')} to {conflict['end_dt'].strftime('%Y-%m-%d %H:%M')})"
                    )
            else:
                create_calendar_event(
                    st.session_state.service,
                    parsed_request["title"],
                    parsed_request["start_dt"],
                    parsed_request["end_dt"],
                    parsed_request["description"],
                )
                st.success("Event created successfully from your natural-language request!")
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Could not process request: {e}")

st.header("Suggest a Free Slot")
with st.form("free_slot_form"):
    slot_start = st.text_input("Suggested start time (YYYY-MM-DD HH:MM)", value="2026-07-10 08:00")
    slot_duration = st.number_input("Duration in minutes", min_value=15, max_value=480, value=60, step=15)
    slot_submitted = st.form_submit_button("Suggest Next Free Slot")

if slot_submitted:
    if st.session_state.service is None:
        st.warning("Please connect to Google Calendar first.")
    else:
        try:
            start_dt = datetime.strptime(slot_start, "%Y-%m-%d %H:%M")
            existing_events = fetch_upcoming_events(st.session_state.service, max_results=20)
            slot = suggest_next_free_slot(start_dt, int(slot_duration), existing_events)
            st.success(
                f"Suggested slot: {slot['start_dt'].strftime('%Y-%m-%d %H:%M')} to {slot['end_dt'].strftime('%Y-%m-%d %H:%M')}"
            )
        except ValueError:
            st.error("Please use the format YYYY-MM-DD HH:MM")
        except Exception as e:
            st.error(f"Could not suggest a free slot: {e}")

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
                existing_events = fetch_upcoming_events(st.session_state.service, max_results=20)
                conflicts = find_conflicts(start_dt, end_dt, existing_events)
                if conflicts:
                    st.warning("This time overlaps with an existing event:")
                    for conflict in conflicts:
                        st.write(
                            f"- {conflict['summary']} ({conflict['start_dt'].strftime('%Y-%m-%d %H:%M')} to {conflict['end_dt'].strftime('%Y-%m-%d %H:%M')})"
                        )
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