import re
from datetime import date, datetime, timedelta

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CLASS_TYPES = ["Lecture", "Lab", "Tutorial", "Seminar"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
PRIORITY_WEIGHT = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}

# Common Indian academic breaks and festivals can be edited per institution.
INDIAN_ACADEMIC_CALENDAR = [
    {"name": "Republic Day", "date": "01-26", "kind": "National holiday"},
    {"name": "Holi", "date": "03-14", "kind": "Festival"},
    {"name": "Independence Day", "date": "08-15", "kind": "National holiday"},
    {"name": "Gandhi Jayanti", "date": "10-02", "kind": "National holiday"},
    {"name": "Diwali break", "date": "10-20", "kind": "Academic break"},
]


def time_to_minutes(value):
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def validate_time_range(start_time, end_time):
    start = time_to_minutes(start_time)
    end = time_to_minutes(end_time)
    if end <= start:
        raise ValueError("End time must be after start time.")


def find_schedule_conflicts(candidate, schedule):
    conflicts = []
    candidate_days = set(candidate.get("days", []))
    candidate_start = time_to_minutes(candidate["start_time"])
    candidate_end = time_to_minutes(candidate["end_time"])
    for item in schedule:
        shared_days = candidate_days.intersection(item.get("days", []))
        if not shared_days:
            continue
        item_start = time_to_minutes(item["start_time"])
        item_end = time_to_minutes(item["end_time"])
        if candidate_start < item_end and item_start < candidate_end:
            conflicts.append(
                {
                    "course_name": item.get("course_name", "Untitled"),
                    "days": sorted(shared_days, key=DAYS.index),
                    "start_time": item["start_time"],
                    "end_time": item["end_time"],
                }
            )
    return conflicts


def _days_until(value, today=None):
    today = today or date.today()
    due_date = date.fromisoformat(value)
    return (due_date - today).days


def recommend_study_sessions(assignments, exams, today=None):
    """Return prioritized study blocks using urgency and priority, without API calls."""
    recommendations = []
    for item in assignments:
        if item.get("completed"):
            continue
        days_left = _days_until(item["due_date"], today)
        urgency = max(1, 14 - max(days_left, 0))
        weight = PRIORITY_WEIGHT.get(item.get("priority", "Medium"), 2)
        minutes = max(30, min(120, int(item.get("estimated_hours", 1) * 60 / 2)))
        recommendations.append(
            {
                "title": f"Assignment: {item['title']}",
                "subject": item.get("subject", "General"),
                "minutes": minutes,
                "reason": f"{max(days_left, 0)} days until due date; {item.get('priority', 'Medium')} priority",
                "score": urgency * weight,
            }
        )
    for item in exams:
        days_left = _days_until(item["exam_date"], today)
        recommendations.append(
            {
                "title": f"Exam revision: {item['subject']}",
                "subject": item["subject"],
                "minutes": 90,
                "reason": f"{max(days_left, 0)} days until exam",
                "score": max(1, 21 - max(days_left, 0)) * 4,
            }
        )
    return sorted(recommendations, key=lambda item: item["score"], reverse=True)


def calculate_analytics(schedule, assignments, exams):
    class_minutes = sum(
        (time_to_minutes(item["end_time"]) - time_to_minutes(item["start_time"]))
        * len(item.get("days", []))
        for item in schedule
    )
    assignment_hours = sum(float(item.get("estimated_hours", 0)) for item in assignments if not item.get("completed"))
    completed = sum(1 for item in assignments if item.get("completed"))
    return {
        "weekly_class_hours": round(class_minutes / 60, 1),
        "outstanding_assignment_hours": round(assignment_hours, 1),
        "assignment_completion_rate": round(completed / len(assignments) * 100, 1) if assignments else 0,
        "upcoming_exams": len(exams),
    }


def parse_scheduling_request(request, reference_date=None):
    """Parse the small, predictable request language supported by the local assistant."""
    text = request.strip()
    if not text:
        raise ValueError("Enter a scheduling request.")
    lower_text = text.lower()
    if "free" in lower_text and "time" in lower_text:
        target_date = reference_date or date.today()
        if "tomorrow" in lower_text:
            target_date += timedelta(days=1)
        else:
            day_match = re.search(r"\b(" + "|".join(day.lower() for day in DAYS) + r")\b", lower_text)
            if day_match:
                target_index = DAYS.index(day_match.group(1).title())
                target_date += timedelta(days=(target_index - target_date.weekday()) % 7)
        return {"intent": "free_time", "date": target_date}

    day_pattern = "|".join(DAYS)
    match = re.search(
        rf"(?:schedule|add|book)\s+(?P<title>.+?)\s+(?:on\s+)?(?P<day>{day_pattern})\s+"
        rf"(?P<start>\d{{1,2}}:\d{{2}})\s*(?:to|-)\s*(?P<end>\d{{1,2}}:\d{{2}})",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError("Try 'schedule Physics on Monday 14:00 to 15:00' or 'find free time tomorrow'.")
    validate_time_range(match.group("start"), match.group("end"))
    return {
        "intent": "schedule",
        "course_name": match.group("title").strip(),
        "days": [match.group("day").title()],
        "start_time": match.group("start"),
        "end_time": match.group("end"),
    }


def find_free_slots(schedule, target_date, work_start="08:00", work_end="20:00", duration_minutes=60):
    """Find fixed-length gaps in a weekday between working-hours boundaries."""
    day = DAYS[target_date.weekday()]
    busy = sorted(
        (time_to_minutes(item["start_time"]), time_to_minutes(item["end_time"]))
        for item in schedule
        if day in item.get("days", [])
    )
    start = time_to_minutes(work_start)
    end = time_to_minutes(work_end)
    slots = []
    cursor = start
    for busy_start, busy_end in busy:
        if cursor + duration_minutes <= busy_start:
            slots.append((cursor, busy_start))
        cursor = max(cursor, busy_end)
    if cursor + duration_minutes <= end:
        slots.append((cursor, end))
    return [
        {"date": target_date.isoformat(), "start_time": _format_minutes(slot_start), "end_time": _format_minutes(slot_end)}
        for slot_start, slot_end in slots
    ]


def _format_minutes(value):
    return f"{value // 60:02d}:{value % 60:02d}"
