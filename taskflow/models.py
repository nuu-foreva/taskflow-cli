"""Data models for TaskFlow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class Priority(Enum):
    """Task priority. Definition order (low -> high) defines the rank."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        """Return 1 for low, 2 for medium and 3 for high."""
        return list(Priority).index(self) + 1

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        """Parse a priority name (case-insensitive)."""
        try:
            return cls(value.strip().lower())
        except ValueError:
            valid = ", ".join(p.value for p in cls)
            raise ValueError(
                f"Invalid priority '{value}'. Choose from: {valid}"
            ) from None


def _normalise_tags(tags: Optional[Iterable[str]]) -> List[str]:
    """Lower-case, strip, remove a leading '#', and de-duplicate tags."""
    cleaned_tags: List[str] = []
    for tag in tags or []:
        cleaned = tag.strip().lower().lstrip("#")
        if cleaned and cleaned not in cleaned_tags:
            cleaned_tags.append(cleaned)
    return cleaned_tags


def _now() -> datetime:
    """Current local time without microseconds (keeps saved data tidy)."""
    return datetime.now().replace(microsecond=0)


@dataclass
class Task:
    """A single to-do item."""

    id: int
    title: str
    priority: Priority = Priority.MEDIUM
    due_date: Optional[date] = None
    done: bool = False
    created_at: datetime = field(default_factory=_now)
    completed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Task title cannot be empty.")
        if self.id < 1:
            raise ValueError("Task id must be a positive integer.")
        self.tags = _normalise_tags(self.tags)

    def is_overdue(self, today: Optional[date] = None) -> bool:
        """A task is overdue if it is unfinished and its due date has passed."""
        if self.done or self.due_date is None:
            return False
        return self.due_date < (today or date.today())

    def mark_done(self) -> None:
        """Mark the task as completed (does nothing if already done)."""
        if self.done:
            return
        self.done = True
        self.completed_at = _now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serialisable dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "done": self.done,
            "created_at": self.created_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Rebuild a task from :meth:`to_dict` output.

        Raises KeyError, ValueError, TypeError or AttributeError on bad data.
        """
        due_raw = data.get("due_date")
        completed_raw = data.get("completed_at")
        return cls(
            id=int(data["id"]),
            title=str(data["title"]),
            priority=Priority.from_string(str(data.get("priority", "medium"))),
            due_date=date.fromisoformat(due_raw) if due_raw else None,
            done=bool(data.get("done", False)),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=(
                datetime.fromisoformat(completed_raw) if completed_raw else None
            ),
            tags=list(data.get("tags", [])),
        )
