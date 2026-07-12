import streamlit as st
from datetime import datetime

from calendar_api import create_calendar_event, fetch_upcoming_events, get_calendar_service

st.set_page_config(page_title="Smart Timetable Assistant", page_icon="📅")
st.title("📅 Smart Timetable Assistant")
st.write("A simple assistant to manage your classes, assignments, and events.")

if "service" not in st.session_state:
    st.session_state.service = None

if st.button("Connect to Google Calendar"):
    try:
        service = get_calendar_service()
        st.session_state.service = service
        st.success("Connected to Google Calendar successfully!")
    except FileNotFoundError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Authentication failed: {e}")

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