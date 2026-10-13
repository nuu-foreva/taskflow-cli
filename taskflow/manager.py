"""Business logic for managing tasks."""

from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, List, Optional

from .models import Priority, Task
from .storage import JsonStorage

VALID_STATUSES = ("all", "pending", "done")
VALID_SORTS = ("id", "priority", "due")


class TaskNotFoundError(Exception):
    """Raised when a task id does not exist."""


class TaskManager:
    """Create, update, query and persist tasks."""

    def __init__(self, storage: JsonStorage) -> None:
        self._storage = storage
        self._tasks: List[Task] = storage.load()

    # ----------------------------------------------------------- helpers
    def _next_id(self) -> int:
        return max((task.id for task in self._tasks), default=0) + 1

    def _save(self) -> None:
        self._storage.save(self._tasks)

    # ---------------------------------------------------------- commands
    def add(
        self,
        title: str,
        priority: Priority = Priority.MEDIUM,
        due_date: Optional[date] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> Task:
        """Create and save a new task."""
        task = Task(
            id=self._next_id(),
            title=title,
            priority=priority,
            due_date=due_date,
            tags=list(tags or []),
        )
        self._tasks.append(task)
        self._save()
        return task

    def get(self, task_id: int) -> Task:
        """Return the task with the given id."""
        for task in self._tasks:
            if task.id == task_id:
                return task
        raise TaskNotFoundError(f"No task with id {task_id}.")

    def complete(self, task_id: int) -> Task:
        """Mark a task as done."""
        task = self.get(task_id)
        task.mark_done()
        self._save()
        return task

    def delete(self, task_id: int) -> Task:
        """Remove a task and return it."""
        task = self.get(task_id)
        self._tasks.remove(task)
        self._save()
        return task

    def clear_completed(self) -> int:
        """Remove all finished tasks and return how many were removed."""
        remaining = [task for task in self._tasks if not task.done]
        removed = len(self._tasks) - len(remaining)
        if removed:
            self._tasks = remaining
            self._save()
        return removed

    # ----------------------------------------------------------- queries
    def list_tasks(
        self,
        status: str = "all",
        priority: Optional[Priority] = None,
        tag: Optional[str] = None,
        sort_by: str = "id",
    ) -> List[Task]:
        """Return tasks filtered by status/priority/tag and sorted."""
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Choose from: {', '.join(VALID_STATUSES)}"
            )
        if sort_by not in VALID_SORTS:
            raise ValueError(
                f"Invalid sort '{sort_by}'. Choose from: {', '.join(VALID_SORTS)}"
            )

        tasks = list(self._tasks)
        if status == "pending":
            tasks = [t for t in tasks if not t.done]
        elif status == "done":
            tasks = [t for t in tasks if t.done]
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        if tag:
            wanted = tag.strip().lower().lstrip("#")
            tasks = [t for t in tasks if wanted in t.tags]

        if sort_by == "priority":
            tasks.sort(key=lambda t: (-t.priority.rank, t.id))
        elif sort_by == "due":
            tasks.sort(
                key=lambda t: (t.due_date is None, t.due_date or date.max, t.id)
            )
        else:
            tasks.sort(key=lambda t: t.id)
        return tasks

    def search(self, keyword: str) -> List[Task]:
        """Find tasks whose title or tags contain the keyword (case-insensitive)."""
        needle = keyword.strip().lower()
        if not needle:
            return []
        return [
            task
            for task in self._tasks
            if needle in task.title.lower() or any(needle in t for t in task.tags)
        ]

    def stats(self, today: Optional[date] = None) -> Dict[str, int]:
        """Return summary counts, including a completion percentage."""
        total = len(self._tasks)
        done = sum(1 for task in self._tasks if task.done)
        overdue = sum(1 for task in self._tasks if task.is_overdue(today))
        percent = round(done / total * 100) if total else 0
        return {
            "total": total,
            "done": done,
            "pending": total - done,
            "overdue": overdue,
            "completion_percent": percent,
        }
