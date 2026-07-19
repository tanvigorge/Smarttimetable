import json
import os
from datetime import datetime

import streamlit as st

from calendar_api import create_calendar_event, fetch_upcoming_events, get_calendar_service

SCHEDULE_FILE = "schedule.json"


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