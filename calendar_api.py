import os
import re
from datetime import datetime, timedelta, timezone

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - exercised in lightweight test environments
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _coerce_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            try:
                return datetime.strptime(text, "%Y-%m-%d")
            except ValueError:
                return None
    return None


def parse_natural_language_request(request_text, reference_date=None):
    """Parse a simple natural-language scheduling request into a start/end window."""
    if not request_text or not request_text.strip():
        raise ValueError("Please enter a scheduling request.")

    reference_date = reference_date or datetime.now()
    text = request_text.strip()
    lowered = text.lower()

    title_match = re.search(
        r"^(?:schedule|book|create|add|plan)\s+(?:a|an|the)?\s*(.+?)(?:\s+(?:tomorrow|today|next|on|at|for|from|until|to)\b|$)",
        lowered,
    )
    title = title_match.group(1).strip() if title_match else "Scheduled Event"
    title = title.strip().lower().replace("  ", " ")

    if "tomorrow" in lowered:
        start_date = reference_date.date() + timedelta(days=1)
    elif "today" in lowered:
        start_date = reference_date.date()
    else:
        weekday_match = re.search(r"\b(next|this)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lowered)
        if weekday_match:
            weekday_name = weekday_match.group(2)
            weekdays = [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
            target_weekday = weekdays.index(weekday_name)
            current_weekday = reference_date.weekday()
            delta_days = (target_weekday - current_weekday) % 7
            if weekday_match.group(1) == "next":
                delta_days = (delta_days + 7) % 7 or 7
            start_date = reference_date.date() + timedelta(days=delta_days)
        else:
            start_date = reference_date.date()

    time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lowered)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridiem = time_match.group(3)
        if meridiem and meridiem.lower() == "pm" and hour < 12:
            hour += 12
        if meridiem and meridiem.lower() == "am" and hour == 12:
            hour = 0
        if hour > 23 or minute > 59:
            raise ValueError("Please enter a valid time.")
        start_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
    else:
        start_time = datetime.strptime("09:00", "%H:%M").time()

    duration_match = re.search(r"\bfor\s+(\d+)\s*(hour|hours|hr|hrs|minute|minutes|min|mins)\b", lowered)
    if duration_match:
        duration_value = int(duration_match.group(1))
        unit = duration_match.group(2).lower()
        if unit.startswith("hour") or unit in {"hr", "hrs"}:
            duration_delta = timedelta(hours=duration_value)
        else:
            duration_delta = timedelta(minutes=duration_value)
    else:
        duration_delta = timedelta(hours=1)

    start_dt = datetime.combine(start_date, start_time)
    end_dt = start_dt + duration_delta
    return {
        "title": title,
        "start_dt": start_dt,
        "end_dt": end_dt,
        "description": text,
    }


def find_conflicts(start_dt, end_dt, existing_events=None):
    """Return any events that overlap with the requested time window."""
    conflicts = []
    for event in existing_events or []:
        event_start = _coerce_datetime(event.get("start", {}).get("dateTime") or event.get("start", {}).get("date"))
        event_end = _coerce_datetime(event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"))
        if event_start is None or event_end is None:
            continue
        if start_dt < event_end and end_dt > event_start:
            conflicts.append(
                {
                    "summary": event.get("summary", "Untitled Event"),
                    "start_dt": event_start,
                    "end_dt": event_end,
                }
            )
    return conflicts


def suggest_next_free_slot(start_dt, duration_minutes, existing_events=None):
    """Suggest the first available slot that fits the requested duration."""
    if duration_minutes <= 0:
        raise ValueError("Duration must be positive.")

    candidate_start = start_dt
    candidate_end = start_dt + timedelta(minutes=duration_minutes)
    while True:
        conflicts = find_conflicts(candidate_start, candidate_end, existing_events)
        if not conflicts:
            return {
                "start_dt": candidate_start,
                "end_dt": candidate_end,
            }
        next_conflict = min(conflicts, key=lambda item: item["end_dt"])
        candidate_start = next_conflict["end_dt"]
        candidate_end = candidate_start + timedelta(minutes=duration_minutes)


def get_calendar_service(credentials_file="credentials.json", token_file="token.json"):
    """Authenticate and return a Google Calendar service object."""
    if build is None or Credentials is None or InstalledAppFlow is None or Request is None:
        raise RuntimeError("Google Calendar dependencies are not installed. Install the packages from requirements.txt first.")

    if not os.path.exists(credentials_file):
        raise FileNotFoundError(
            "credentials.json was not found. Create it from Google Cloud Console and place it in the project folder."
        )

    creds = None
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_calendar_event(service, title, start_dt, end_dt, description=""):
    """Create a new event in the primary Google Calendar."""
    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
    }
    return service.events().insert(calendarId="primary", body=event).execute()


def fetch_upcoming_events(service, max_results=5):
    """Return the next upcoming events from the user's primary calendar."""
    now = datetime.utcnow().isoformat() + "Z"
    future = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            timeMax=future,
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        )
        .execute()
    )
    return result.get("items", [])
