import json
import os
from datetime import datetime

import streamlit as st

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