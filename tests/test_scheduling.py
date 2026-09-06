import unittest
from datetime import datetime

from academic_scheduler import (
    allocate_study_time,
    build_assignment_deadline,
    build_course_session,
    build_exam_schedule,
    build_reminder,
    generate_semester_template,
    get_indian_academic_calendar,
    parse_free_time_query,
)
from calendar_api import (
    find_conflicts,
    parse_natural_language_request,
    suggest_next_free_slot,
)


class SchedulingFeaturesTests(unittest.TestCase):
    def test_parse_natural_language_request_with_duration(self):
        reference = datetime(2026, 7, 25, 9, 0)
        parsed = parse_natural_language_request(
            "Schedule a team sync tomorrow at 2pm for 1 hour",
            reference_date=reference,
        )

        self.assertEqual(parsed["title"], "team sync")
        self.assertEqual(parsed["start_dt"], datetime(2026, 7, 26, 14, 0))
        self.assertEqual(parsed["end_dt"], datetime(2026, 7, 26, 15, 0))

    def test_find_conflicts_detects_overlap(self):
        existing_events = [
            {
                "summary": "Focus block",
                "start": {"dateTime": "2026-07-10T09:30:00Z"},
                "end": {"dateTime": "2026-07-10T10:30:00Z"},
            }
        ]

        conflicts = find_conflicts(
            datetime(2026, 7, 10, 9, 0),
            datetime(2026, 7, 10, 10, 0),
            existing_events,
        )

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["summary"], "Focus block")

    def test_suggest_next_free_slot_returns_first_available_window(self):
        existing_events = [
            {
                "summary": "Meeting",
                "start": {"dateTime": "2026-07-10T08:30:00Z"},
                "end": {"dateTime": "2026-07-10T09:30:00Z"},
            }
        ]

        slot = suggest_next_free_slot(
            datetime(2026, 7, 10, 8, 0),
            60,
            existing_events,
        )

        self.assertEqual(slot["start_dt"], datetime(2026, 7, 10, 9, 30))
        self.assertEqual(slot["end_dt"], datetime(2026, 7, 10, 10, 30))

    def test_generate_semester_template_includes_breaks_and_festivals(self):
        template = generate_semester_template("Semester 1", 2026)

        self.assertEqual(template["term_name"], "Semester 1")
        self.assertGreaterEqual(template["week_count"], 16)
        self.assertTrue(template["breaks"])
        self.assertIn("festival_holidays", template)

    def test_build_course_session_tracks_session_type_and_term(self):
        session = build_course_session(
            course_name="Data Structures",
            session_type="Lab",
            day="Tuesday",
            start_time="11:00",
            end_time="12:30",
            semester="Semester 1",
        )

        self.assertEqual(session["course_name"], "Data Structures")
        self.assertEqual(session["session_type"], "lab")
        self.assertEqual(session["semester"], "Semester 1")

    def test_build_exam_schedule_and_study_allocation(self):
        exam = build_exam_schedule(
            course_name="Algorithms",
            exam_title="Midterm Exam",
            exam_date="2026-10-15",
            start_time="09:00",
            end_time="10:30",
            study_hours=8,
            priority="high",
            semester="Semester 1",
        )

        self.assertEqual(exam["course_name"], "Algorithms")
        self.assertEqual(exam["priority"], "high")
        self.assertGreaterEqual(exam["study_hours"], 6)

        allocation = allocate_study_time([exam], weekly_study_hours=12)
        self.assertEqual(len(allocation), 1)
        self.assertGreater(allocation[0]["allocated_hours"], 0)

    def test_build_assignment_deadline_tracks_priority_and_due_date(self):
        assignment = build_assignment_deadline(
            assignment_title="Operating Systems Quiz",
            course_name="Operating Systems",
            due_date="2026-09-03",
            priority="medium",
            estimated_hours=3,
        )

        self.assertEqual(assignment["course_name"], "Operating Systems")
        self.assertEqual(assignment["priority"], "medium")
        self.assertEqual(assignment["status"], "pending")

    def test_indian_academic_calendar_contains_semester_breaks(self):
        calendar = get_indian_academic_calendar(2026, "Semester 1")

        self.assertEqual(calendar["year"], 2026)
        self.assertIn("semester_breaks", calendar)
        self.assertTrue(calendar["semester_breaks"])
        self.assertIn("festival_holidays", calendar)

    def test_parse_free_time_query_detects_duration_and_date(self):
        query = parse_free_time_query("find free time tomorrow for 90 minutes", reference_date=datetime(2026, 7, 25, 9, 0))

        self.assertEqual(query["duration_minutes"], 90)
        self.assertEqual(query["date"], "2026-07-26")

    def test_build_reminder_supports_email_and_sms_channels(self):
        reminder = build_reminder(
            title="Review algorithms notes",
            reminder_time="2026-09-02 18:00",
            channel="email",
        )

        self.assertEqual(reminder["title"], "Review algorithms notes")
        self.assertEqual(reminder["channel"], "email")
        self.assertEqual(reminder["status"], "scheduled")


if __name__ == "__main__":
    unittest.main()
