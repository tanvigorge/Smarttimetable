import unittest
from datetime import datetime

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


if __name__ == "__main__":
    unittest.main()
