import tempfile
import unittest
from datetime import date
from pathlib import Path

from taskflow.manager import TaskManager, TaskNotFoundError
from taskflow.models import Priority
from taskflow.storage import JsonStorage


class ManagerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "tasks.json"
        self.manager = TaskManager(JsonStorage(self.path))

    def reload(self):
        return TaskManager(JsonStorage(self.path))

    def test_add_assigns_incrementing_ids(self):
        first = self.manager.add("First")
        second = self.manager.add("Second")
        self.assertEqual((first.id, second.id), (1, 2))

    def test_ids_are_not_reused_for_existing_tasks(self):
        self.manager.add("One")
        self.manager.add("Two")
        self.manager.add("Three")
        self.manager.delete(2)
        self.assertEqual(self.manager.add("Four").id, 4)

    def test_changes_are_persisted(self):
        self.manager.add("Persist me", priority=Priority.HIGH, tags=["x"])
        reloaded = self.reload().get(1)
        self.assertEqual(reloaded.title, "Persist me")
        self.assertEqual(reloaded.priority, Priority.HIGH)
        self.assertEqual(reloaded.tags, ["x"])

    def test_complete_marks_task_and_persists(self):
        self.manager.add("Finish")
        self.manager.complete(1)
        self.assertTrue(self.reload().get(1).done)

    def test_unknown_id_raises(self):
        with self.assertRaises(TaskNotFoundError):
            self.manager.get(99)
        with self.assertRaises(TaskNotFoundError):
            self.manager.complete(99)
        with self.assertRaises(TaskNotFoundError):
            self.manager.delete(99)

    def test_delete_removes_task(self):
        self.manager.add("Gone soon")
        self.manager.delete(1)
        self.assertEqual(self.reload().list_tasks(), [])

    def test_list_filters_by_status(self):
        self.manager.add("A")
        self.manager.add("B")
        self.manager.complete(1)
        self.assertEqual([t.id for t in self.manager.list_tasks(status="done")], [1])
        self.assertEqual([t.id for t in self.manager.list_tasks(status="pending")], [2])
        self.assertEqual(len(self.manager.list_tasks(status="all")), 2)

    def test_list_filters_by_priority_and_tag(self):
        self.manager.add("A", priority=Priority.HIGH, tags=["work"])
        self.manager.add("B", priority=Priority.LOW, tags=["home"])
        by_priority = self.manager.list_tasks(priority=Priority.HIGH)
        by_tag = self.manager.list_tasks(tag="#HOME")
        self.assertEqual([t.id for t in by_priority], [1])
        self.assertEqual([t.id for t in by_tag], [2])

    def test_sort_by_priority_puts_high_first(self):
        self.manager.add("Low", priority=Priority.LOW)
        self.manager.add("High", priority=Priority.HIGH)
        self.manager.add("Medium", priority=Priority.MEDIUM)
        ids = [t.id for t in self.manager.list_tasks(sort_by="priority")]
        self.assertEqual(ids, [2, 3, 1])

    def test_sort_by_due_puts_undated_tasks_last(self):
        self.manager.add("No date")
        self.manager.add("Later", due_date=date(2026, 12, 1))
        self.manager.add("Sooner", due_date=date(2026, 6, 1))
        ids = [t.id for t in self.manager.list_tasks(sort_by="due")]
        self.assertEqual(ids, [3, 2, 1])

    def test_invalid_status_or_sort_raises(self):
        with self.assertRaises(ValueError):
            self.manager.list_tasks(status="bogus")
        with self.assertRaises(ValueError):
            self.manager.list_tasks(sort_by="bogus")

    def test_search_matches_title_and_tags_case_insensitively(self):
        self.manager.add("Buy Milk", tags=["shopping"])
        self.manager.add("Write report", tags=["work"])
        self.assertEqual([t.id for t in self.manager.search("milk")], [1])
        self.assertEqual([t.id for t in self.manager.search("WORK")], [2])
        self.assertEqual(self.manager.search("   "), [])
        self.assertEqual(self.manager.search("zzz"), [])

    def test_stats(self):
        self.manager.add("Done one")
        self.manager.add("Overdue one", due_date=date(2000, 1, 1))
        self.manager.add("Pending one")
        self.manager.add("Another pending")
        self.manager.complete(1)
        self.assertEqual(
            self.manager.stats(),
            {
                "total": 4,
                "done": 1,
                "pending": 3,
                "overdue": 1,
                "completion_percent": 25,
            },
        )

    def test_stats_with_no_tasks(self):
        self.assertEqual(self.manager.stats()["completion_percent"], 0)

    def test_clear_completed(self):
        self.manager.add("A")
        self.manager.add("B")
        self.manager.complete(1)
        self.assertEqual(self.manager.clear_completed(), 1)
        self.assertEqual(self.manager.clear_completed(), 0)
        self.assertEqual([t.id for t in self.reload().list_tasks()], [2])


if __name__ == "__main__":
    unittest.main()
