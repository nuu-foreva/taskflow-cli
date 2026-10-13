"""JSON file persistence for tasks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Union

from .models import Task


class StorageError(Exception):
    """Raised when tasks cannot be read from or written to disk."""


class JsonStorage:
    """Stores tasks in a human-readable JSON file."""

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)

    def load(self) -> List[Task]:
        """Load all tasks. A missing file means there are no tasks yet."""
        if not self.path.exists():
            return []

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except json.JSONDecodeError as exc:
            raise StorageError(f"'{self.path}' is not valid JSON: {exc}") from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise StorageError(f"Could not read '{self.path}': {exc}") from exc

        if not isinstance(raw, list):
            raise StorageError(f"'{self.path}' must contain a JSON list of tasks.")

        try:
            return [Task.from_dict(item) for item in raw]
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise StorageError(
                f"'{self.path}' contains an invalid task entry: {exc!r}"
            ) from exc

    def save(self, tasks: List[Task]) -> None:
        """Save tasks atomically (write to a temp file, then replace)."""
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tmp_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    [task.to_dict() for task in tasks],
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
                handle.write("\n")
            os.replace(tmp_path, self.path)
        except OSError as exc:
            try:
                tmp_path.unlink()
            except OSError:
                pass
            raise StorageError(f"Could not write '{self.path}': {exc}") from exc
