import json
import tempfile
import unittest
from pathlib import Path

from taskflow.models import Task
from taskflow.storage import JsonStorage, StorageError


class StorageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.path = self.dir / "nested" / "tasks.json"
        self.storage = JsonStorage(self.path)

    def test_missing_file_loads_as_empty_list(self):
        self.assertEqual(self.storage.load(), [])

    def test_save_then_load_round_trip(self):
        tasks = [Task(id=1, title="One"), Task(id=2, title="Two", tags=["x"])]
        self.storage.save(tasks)
        self.assertEqual(self.storage.load(), tasks)

    def test_save_leaves_no_temporary_file(self):
        self.storage.save([Task(id=1, title="One")])
        leftovers = [p.name for p in self.path.parent.iterdir()]
        self.assertEqual(leftovers, ["tasks.json"])

    def test_unicode_titles_survive(self):
        self.storage.save([Task(id=1, title="Café ☕ — Ẹ kú àárọ̀")])
        self.assertEqual(self.storage.load()[0].title, "Café ☕ — Ẹ kú àárọ̀")

    def test_corrupt_json_raises_storage_error(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(StorageError):
            self.storage.load()

    def test_non_list_json_raises_storage_error(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"id": 1}), encoding="utf-8")
        with self.assertRaises(StorageError):
            self.storage.load()

    def test_invalid_entry_raises_storage_error(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps([{"title": "no id"}]), encoding="utf-8")
        with self.assertRaises(StorageError):
            self.storage.load()

    def test_non_object_entry_raises_storage_error(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps(["just a string"]), encoding="utf-8")
        with self.assertRaises(StorageError):
            self.storage.load()

    def test_unwritable_location_raises_storage_error(self):
        blocker = self.dir / "blocker"
        blocker.write_text("I am a file, not a folder", encoding="utf-8")
        storage = JsonStorage(blocker / "tasks.json")
        with self.assertRaises(StorageError):
            storage.save([Task(id=1, title="One")])


if __name__ == "__main__":
    unittest.main()
