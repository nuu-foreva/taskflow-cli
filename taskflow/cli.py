"""Command-line interface for TaskFlow."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .manager import VALID_SORTS, VALID_STATUSES, TaskManager, TaskNotFoundError
from .models import Priority, Task
from .storage import JsonStorage, StorageError


# ------------------------------------------------------------------ helpers
def default_storage_path() -> Path:
    """Use $TASKFLOW_FILE if set, otherwise ~/.taskflow/tasks.json."""
    env_path = os.environ.get("TASKFLOW_FILE")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".taskflow" / "tasks.json"


def priority_type(value: str) -> Priority:
    """argparse type for --priority."""
    try:
        return Priority.from_string(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def date_type(value: str) -> date:
    """argparse type for --due: YYYY-MM-DD, 'today' or 'tomorrow'."""
    text = value.strip().lower()
    if text == "today":
        return date.today()
    if text == "tomorrow":
        return date.today() + timedelta(days=1)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use YYYY-MM-DD, 'today' or 'tomorrow'."
        ) from None


def format_task(task: Task, today: Optional[date] = None) -> str:
    """Render a task as a single readable line."""
    check = "x" if task.done else " "
    parts = [f"[{check}] {task.id:>3}. {task.title}", f"({task.priority.value})"]
    if task.due_date:
        due = f"due {task.due_date.isoformat()}"
        if task.is_overdue(today):
            due += " OVERDUE"
        parts.append(due)
    if task.tags:
        parts.append(" ".join(f"#{tag}" for tag in task.tags))
    return "  ".join(parts)


def print_tasks(tasks: Sequence[Task]) -> None:
    """Print a list of tasks, or a friendly message if it is empty."""
    if not tasks:
        print("No tasks found.")
        return
    for task in tasks:
        print(format_task(task))
    print(f"\n{len(tasks)} task(s)")


# ----------------------------------------------------------------- commands
def cmd_add(manager: TaskManager, args: argparse.Namespace) -> int:
    task = manager.add(
        " ".join(args.title),
        priority=args.priority,
        due_date=args.due,
        tags=args.tag,
    )
    print(f"Added task {task.id}: {task.title}")
    return 0


def cmd_list(manager: TaskManager, args: argparse.Namespace) -> int:
    print_tasks(
        manager.list_tasks(
            status=args.status,
            priority=args.priority,
            tag=args.tag,
            sort_by=args.sort,
        )
    )
    return 0


def cmd_done(manager: TaskManager, args: argparse.Namespace) -> int:
    task = manager.complete(args.id)
    print(f"Completed task {task.id}: {task.title}")
    return 0


def cmd_delete(manager: TaskManager, args: argparse.Namespace) -> int:
    task = manager.delete(args.id)
    print(f"Deleted task {task.id}: {task.title}")
    return 0


def cmd_search(manager: TaskManager, args: argparse.Namespace) -> int:
    print_tasks(manager.search(args.keyword))
    return 0


def cmd_stats(manager: TaskManager, args: argparse.Namespace) -> int:
    stats = manager.stats()
    print(f"Total:      {stats['total']}")
    print(f"Done:       {stats['done']}")
    print(f"Pending:    {stats['pending']}")
    print(f"Overdue:    {stats['overdue']}")
    print(f"Completion: {stats['completion_percent']}%")
    return 0


def cmd_clear(manager: TaskManager, args: argparse.Namespace) -> int:
    removed = manager.clear_completed()
    print(f"Removed {removed} completed task(s).")
    return 0


COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "delete": cmd_delete,
    "search": cmd_search,
    "stats": cmd_stats,
    "clear": cmd_clear,
}


# ------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all sub-commands."""
    parser = argparse.ArgumentParser(
        prog="taskflow",
        description="A small command-line task manager.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="tasks file (default: $TASKFLOW_FILE or ~/.taskflow/tasks.json)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="add a new task")
    add.add_argument("title", nargs="+", help="task title")
    add.add_argument(
        "-p", "--priority", type=priority_type, default=Priority.MEDIUM,
        help="low, medium (default) or high",
    )
    add.add_argument(
        "-d", "--due", type=date_type,
        help="due date: YYYY-MM-DD, 'today' or 'tomorrow'",
    )
    add.add_argument(
        "-t", "--tag", action="append", default=[],
        help="add a tag (repeat for several tags)",
    )

    list_cmd = subparsers.add_parser("list", help="list tasks")
    list_cmd.add_argument("--status", choices=VALID_STATUSES, default="all")
    list_cmd.add_argument("-p", "--priority", type=priority_type)
    list_cmd.add_argument("-t", "--tag", help="only show tasks with this tag")
    list_cmd.add_argument("--sort", choices=VALID_SORTS, default="id")

    done = subparsers.add_parser("done", help="mark a task as completed")
    done.add_argument("id", type=int)

    delete = subparsers.add_parser("delete", help="delete a task")
    delete.add_argument("id", type=int)

    search = subparsers.add_parser("search", help="search titles and tags")
    search.add_argument("keyword")

    subparsers.add_parser("stats", help="show summary statistics")
    subparsers.add_parser("clear", help="remove all completed tasks")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    storage_path = args.file if args.file is not None else default_storage_path()

    try:
        manager = TaskManager(JsonStorage(storage_path))
        return COMMANDS[args.command](manager, args)
    except (TaskNotFoundError, StorageError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
