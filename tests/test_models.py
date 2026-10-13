import unittest
from datetime import date, datetime

from taskflow.models import Priority, Task


class PriorityTests(unittest.TestCase):
    def test_from_string_is_case_insensitive(self):
        self.assertEqual(Priority.from_string(" HIGH "), Priority.HIGH)
        self.assertEqual(Priority.from_string("low"), Priority.LOW)

    def test_from_string_rejects_unknown_value(self):
        with self.assertRaises(ValueError) as ctx:
            Priority.from_string("urgent")
        self.assertIn("low, medium, high", str(ctx.exception))

    def test_rank_orders_priorities(self):
        self.assertLess(Priority.LOW.rank, Priority.MEDIUM.rank)
        self.assertLess(Priority.MEDIUM.rank, Priority.HIGH.rank)


class TaskTests(unittest.TestCase):
    def test_empty_title_is_rejected(self):
        with self.assertRaises(ValueError):
            Task(id=1, title="   ")

    def test_invalid_id_is_rejected(self):
        with self.assertRaises(ValueError):
            Task(id=0, title="Bad id")

    def test_title_is_stripped(self):
        self.assertEqual(Task(id=1, title="  Hello  ").title, "Hello")

    def test_tags_are_normalised_and_deduplicated(self):
        task = Task(id=1, title="Tags", tags=["#Work", "work", " Home ", ""])
        self.assertEqual(task.tags, ["work", "home"])

    def test_is_overdue(self):
        today = date(2026, 1, 10)
        past = Task(id=1, title="Past", due_date=date(2026, 1, 9))
        same_day = Task(id=2, title="Today", due_date=today)
        no_due = Task(id=3, title="No due date")
        self.assertTrue(past.is_overdue(today))
        self.assertFalse(same_day.is_overdue(today))
        self.assertFalse(no_due.is_overdue(today))

    def test_done_task_is_never_overdue(self):
        task = Task(id=1, title="Done", due_date=date(2000, 1, 1))
        task.mark_done()
        self.assertFalse(task.is_overdue(date(2026, 1, 10)))

    def test_mark_done_is_idempotent(self):
        task = Task(id=1, title="Finish")
        task.mark_done()
        first_completed_at = task.completed_at
        task.mark_done()
        self.assertTrue(task.done)
        self.assertIsNotNone(first_completed_at)
        self.assertEqual(task.completed_at, first_completed_at)

    def test_dict_round_trip(self):
        task = Task(
            id=7,
            title="Round trip",
            priority=Priority.HIGH,
            due_date=date(2026, 5, 1),
            created_at=datetime(2026, 4, 1, 9, 30, 0),
            tags=["a", "b"],
        )
        task.mark_done()
        restored = Task.from_dict(task.to_dict())
        self.assertEqual(restored, task)

    def test_from_dict_requires_mandatory_fields(self):
        with self.assertRaises(KeyError):
            Task.from_dict({"title": "No id"})


if __name__ == "__main__":
    unittest.main()
