from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List


INDIAN_FESTIVALS = {
    "Diwali": "October/November",
    "Dussehra": "September/October",
    "Holi": "March",
    "Navratri": "September/October",
    "Raksha Bandhan": "August",
    "Christmas": "December",
    "Eid": "Varies by moon sighting",
}


def get_indian_academic_calendar(year: int, term_name: str = "Semester 1") -> Dict[str, Any]:
    """Return a pragmatic Indian university calendar with semester breaks and festival holidays."""
    semester_breaks = [
        {
            "name": "Mid-semester break",
            "start_date": f"{year}-09-15",
            "end_date": f"{year}-09-20",
        },
        {
            "name": "Semester-end break",
            "start_date": f"{year}-12-15",
            "end_date": f"{year}-12-31",
        },
    ]

    festival_holidays = [
        {"name": holiday, "month": month, "notes": "Public or university holiday window"}
        for holiday, month in INDIAN_FESTIVALS.items()
    ]

    return {
        "year": year,
        "term_name": term_name,
        "semester_breaks": semester_breaks,
        "festival_holidays": festival_holidays,
        "exam_window": {
            "start_date": f"{year}-11-01",
            "end_date": f"{year}-11-30",
        },
    }


def generate_semester_template(term_name: str = "Semester 1", year: int = 2026) -> Dict[str, Any]:
    """Generate a term-based academic template, including breaks and festival holidays."""
    calendar = get_indian_academic_calendar(year, term_name)
    weekly_count = 18
    return {
        "term_name": term_name,
        "year": year,
        "week_count": weekly_count,
        "start_date": f"{year}-07-01",
        "end_date": f"{year}-11-30",
        "breaks": calendar["semester_breaks"],
        "festival_holidays": calendar["festival_holidays"],
        "weekly_pattern": {
            "Monday": ["Lecture", "Lecture", "Tutorial"],
            "Tuesday": ["Lecture", "Lab"],
            "Wednesday": ["Lecture", "Tutorial"],
            "Thursday": ["Lecture", "Practical"],
            "Friday": ["Lecture", "Seminar"],
        },
    }


def build_course_session(
    course_name: str,
    session_type: str,
    day: str,
    start_time: str,
    end_time: str,
    semester: str = "Semester 1",
    location: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    """Build a course-specific session item using an academic session type mapping."""
    normalized_type = (session_type or "lecture").strip().lower()
    allowed_types = {
        "lecture": "lecture",
        "lectures": "lecture",
        "lab": "lab",
        "labs": "lab",
        "tutorial": "tutorial",
        "tutorials": "tutorial",
        "practical": "lab",
        "seminar": "seminar",
    }
    normalized_type = allowed_types.get(normalized_type, normalized_type)

    if not course_name:
        raise ValueError("Course name is required.")

    try:
        datetime.strptime(start_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")
    except ValueError as exc:
        raise ValueError("Please use the format HH:MM for start and end times.") from exc

    return {
        "course_name": course_name,
        "session_type": normalized_type,
        "day": day,
        "start_time": start_time,
        "end_time": end_time,
        "semester": semester,
        "location": location,
        "notes": notes,
    }


def build_exam_schedule(
    course_name: str,
    exam_title: str,
    exam_date: str,
    start_time: str,
    end_time: str,
    study_hours: int = 6,
    priority: str = "medium",
    semester: str = "Semester 1",
    venue: str = "",
) -> Dict[str, Any]:
    """Create an exam schedule record with study-time allocation recommendations."""
    if not course_name:
        raise ValueError("Course name is required.")

    try:
        datetime.strptime(exam_date, "%Y-%m-%d")
        datetime.strptime(start_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")
    except ValueError as exc:
        raise ValueError("Please provide valid exam date and time in the expected format.") from exc

    normalized_priority = (priority or "medium").strip().lower()
    if normalized_priority not in {"low", "medium", "high"}:
        normalized_priority = "medium"

    hours = max(0, int(study_hours or 0))
    if hours == 0:
        hours = 6 if normalized_priority in {"medium", "high"} else 3

    return {
        "course_name": course_name,
        "exam_title": exam_title or f"{course_name} Exam",
        "exam_date": exam_date,
        "start_time": start_time,
        "end_time": end_time,
        "venue": venue,
        "study_hours": hours,
        "priority": normalized_priority,
        "semester": semester,
        "study_plan": [
            {"block": "Revision", "hours": max(2, hours // 3)},
            {"block": "Practice", "hours": max(2, hours // 3)},
            {"block": "Self-test", "hours": max(1, hours - max(2, hours // 3) - max(2, hours // 3))},
        ],
    }


def allocate_study_time(exam_schedule: Iterable[Dict[str, Any]], weekly_study_hours: int = 12) -> List[Dict[str, Any]]:
    """Allocate a weekly study plan based on each exam's priority and required study duration."""
    if weekly_study_hours <= 0:
        raise ValueError("Weekly study hours must be positive.")

    allocations: List[Dict[str, Any]] = []
    for exam in exam_schedule:
        study_hours = max(1, int(exam.get("study_hours", 0) or 1))
        priority_weight = {"low": 0.6, "medium": 1.0, "high": 1.4}.get((exam.get("priority") or "medium").lower(), 1.0)
        allocated = max(1, min(weekly_study_hours, int(round(study_hours * priority_weight))))
        allocations.append(
            {
                "course_name": exam.get("course_name"),
                "exam_title": exam.get("exam_title"),
                "priority": exam.get("priority", "medium"),
                "allocated_hours": allocated,
                "weekly_study_hours": weekly_study_hours,
            }
        )
    return allocations


def build_assignment_deadline(
    assignment_title: str,
    course_name: str,
    due_date: str,
    priority: str = "medium",
    estimated_hours: int = 2,
    status: str = "pending",
) -> Dict[str, Any]:
    """Create an assignment deadline tracker with a set priority and status."""
    if not assignment_title or not course_name:
        raise ValueError("Assignment title and course name are required.")

    try:
        datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Please provide due_date in YYYY-MM-DD format.") from exc

    normalized_priority = (priority or "medium").strip().lower()
    if normalized_priority not in {"low", "medium", "high"}:
        normalized_priority = "medium"

    normalized_status = (status or "pending").strip().lower()
    if normalized_status not in {"pending", "in_progress", "submitted", "overdue"}:
        normalized_status = "pending"

    return {
        "assignment_title": assignment_title,
        "course_name": course_name,
        "due_date": due_date,
        "priority": normalized_priority,
        "estimated_hours": max(1, int(estimated_hours or 1)),
        "status": normalized_status,
    }


def parse_free_time_query(query: str, reference_date: datetime | None = None) -> Dict[str, Any]:
    """Interpret a simple free-time query such as 'find free time tomorrow for 90 minutes'."""
    if not query or not query.strip():
        raise ValueError("Please enter a scheduling query.")

    reference = reference_date or datetime.now()
    lowered = query.lower().strip()

    duration_minutes = 60
    duration_match = re.search(r"(\d+)\s*(minute|minutes|min|mins|hour|hours|hr|hrs)", lowered)
    if duration_match:
        value = int(duration_match.group(1))
        unit = duration_match.group(2).lower()
        if unit.startswith("hour") or unit in {"hr", "hrs"}:
            duration_minutes = value * 60
        else:
            duration_minutes = value

    if "tomorrow" in lowered:
        target_date = (reference + timedelta(days=1)).date().isoformat()
    elif "today" in lowered:
        target_date = reference.date().isoformat()
    else:
        target_date = reference.date().isoformat()

    return {
        "query": query,
        "date": target_date,
        "duration_minutes": duration_minutes,
        "reference_date": reference,
    }


def build_reminder(title: str, reminder_time: str, channel: str = "email", status: str = "scheduled") -> Dict[str, Any]:
    """Create a reminder entry for email or SMS channels."""
    if not title:
        raise ValueError("Reminder title is required.")

    try:
        datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("Please provide reminder_time in YYYY-MM-DD HH:MM format.") from exc

    normalized_channel = (channel or "email").strip().lower()
    if normalized_channel not in {"email", "sms"}:
        normalized_channel = "email"

    normalized_status = (status or "scheduled").strip().lower()
    if normalized_status not in {"scheduled", "sent", "cancelled"}:
        normalized_status = "scheduled"

    return {
        "title": title,
        "reminder_time": reminder_time,
        "channel": normalized_channel,
        "status": normalized_status,
    }


def generate_study_session_plan(assignments: Iterable[Dict[str, Any]] | None = None, exams: Iterable[Dict[str, Any]] | None = None, daily_minutes: int = 90) -> List[Dict[str, Any]]:
    """Create an intelligent, priority-aware study plan using assignment and exam urgency."""
    items: List[Dict[str, Any]] = []
    for assignment in assignments or []:
        items.append(
            {
                "type": "assignment",
                "title": assignment.get("assignment_title") or assignment.get("title") or "Assignment",
                "priority": assignment.get("priority", "medium"),
                "due_date": assignment.get("due_date"),
                "hours": assignment.get("estimated_hours", 2),
            }
        )
    for exam in exams or []:
        items.append(
            {
                "type": "exam",
                "title": exam.get("exam_title") or exam.get("course_name") or "Exam",
                "priority": exam.get("priority", "medium"),
                "due_date": exam.get("exam_date"),
                "hours": exam.get("study_hours", 4),
            }
        )

    priority_weight = {"low": 1, "medium": 2, "high": 3}
    plan: List[Dict[str, Any]] = []
    for item in sorted(items, key=lambda entry: (priority_weight.get((entry.get("priority") or "medium").lower(), 2), -int(entry.get("hours", 2))), reverse=True):
        plan.append(
            {
                "type": item["type"],
                "title": item["title"],
                "priority": item["priority"],
                "recommended_minutes": max(30, min(int(daily_minutes), int(item["hours"]) * 25)),
                "due_date": item.get("due_date"),
            }
        )
    return plan
