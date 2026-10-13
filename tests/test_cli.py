import contextlib
import io
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from taskflow import __version__
from taskflow.cli import default_storage_path, format_task, main
from taskflow.models import Priority, Task


class CliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.file = str(Path(tmp.name) / "tasks.json")

    def run_cli(self, *args):
        """Run the CLI and return (exit_code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--file", self.file, *args])
        return code, out.getvalue(), err.getvalue()

    def test_add_and_list(self):
        code, out, _ = self.run_cli("add", "Buy", "milk", "-p", "high", "-t", "home")
        self.assertEqual(code, 0)
        self.assertIn("Added task 1: Buy milk", out)

        code, out, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("Buy milk", out)
        self.assertIn("(high)", out)
        self.assertIn("#home", out)
        self.assertIn("1 task(s)", out)

    def test_list_when_empty(self):
        code, out, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("No tasks found.", out)

    def test_done_and_filtering(self):
        self.run_cli("add", "Task A")
        self.run_cli("add", "Task B")
        code, out, _ = self.run_cli("done", "1")
        self.assertEqual(code, 0)
        self.assertIn("Completed task 1", out)

        _, out, _ = self.run_cli("list", "--status", "pending")
        self.assertIn("Task B", out)
        self.assertNotIn("Task A", out)

    def test_delete(self):
        self.run_cli("add", "Temporary")
        code, out, _ = self.run_cli("delete", "1")
        self.assertEqual(code, 0)
        self.assertIn("Deleted task 1", out)

    def test_unknown_task_returns_error_code(self):
        code, out, err = self.run_cli("done", "42")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("No task with id 42", err)

    def test_blank_title_returns_error_code(self):
        code, _, err = self.run_cli("add", "   ")
        self.assertEqual(code, 1)
        self.assertIn("cannot be empty", err)

    def test_invalid_priority_exits_with_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli("add", "Oops", "-p", "urgent")
        self.assertEqual(ctx.exception.code, 2)

    def test_invalid_date_exits_with_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli("add", "Oops", "-d", "31/12/2026")
        self.assertEqual(ctx.exception.code, 2)

    def test_impossible_date_exits_with_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli("add", "Oops", "-d", "2026-02-30")
        self.assertEqual(ctx.exception.code, 2)

    def test_missing_command_exits_with_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli()
        self.assertEqual(ctx.exception.code, 2)

    def test_due_today_and_tomorrow_keywords(self):
        self.run_cli("add", "Soon", "-d", "tomorrow")
        self.run_cli("add", "Now", "-d", "today")
        _, out, _ = self.run_cli("list")
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertIn(f"due {tomorrow}", out)
        self.assertIn(f"due {date.today().isoformat()}", out)
        self.assertNotIn("OVERDUE", out)

    def test_overdue_is_flagged(self):
        self.run_cli("add", "Late", "-d", "2000-01-01")
        _, out, _ = self.run_cli("list")
        self.assertIn("OVERDUE", out)

    def test_search(self):
        self.run_cli("add", "Write report", "-t", "work")
        code, out, _ = self.run_cli("search", "report")
        self.assertEqual(code, 0)
        self.assertIn("Write report", out)

    def test_stats_and_clear(self):
        self.run_cli("add", "A")
        self.run_cli("add", "B")
        self.run_cli("done", "1")
        _, out, _ = self.run_cli("stats")
        self.assertIn("Total:      2", out)
        self.assertIn("Completion: 50%", out)

        _, out, _ = self.run_cli("clear")
        self.assertIn("Removed 1 completed task(s).", out)

    def test_corrupt_file_returns_error_code(self):
        Path(self.file).write_text("not json at all", encoding="utf-8")
        code, _, err = self.run_cli("list")
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", err)

    def test_version_flag(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(__version__, out.getvalue())


class HelperTests(unittest.TestCase):
    def test_format_task_shows_all_details(self):
        task = Task(
            id=3,
            title="Ship it",
            priority=Priority.HIGH,
            due_date=date(2026, 1, 1),
            tags=["work"],
        )
        line = format_task(task, today=date(2026, 2, 1))
        self.assertIn("[ ]", line)
        self.assertIn("Ship it", line)
        self.assertIn("(high)", line)
        self.assertIn("due 2026-01-01 OVERDUE", line)
        self.assertIn("#work", line)

    def test_format_task_marks_done(self):
        task = Task(id=1, title="Done")
        task.mark_done()
        self.assertIn("[x]", format_task(task))

    def test_default_path_uses_environment_variable(self):
        with mock.patch.dict(os.environ, {"TASKFLOW_FILE": "/tmp/custom.json"}):
            self.assertEqual(default_storage_path(), Path("/tmp/custom.json"))

    def test_default_path_falls_back_to_home_directory(self):
        env = {k: v for k, v in os.environ.items() if k != "TASKFLOW_FILE"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                default_storage_path(), Path.home() / ".taskflow" / "tasks.json"
            )


if __name__ == "__main__":
    unittest.main()
