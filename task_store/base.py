from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


class TaskStatus(str, Enum):
    PLANNING = "planning"
    READY_TO_WORK = "ready_to_work"
    IN_PROGRESS = "in_progress"
    ON_REVIEW = "on_review"
    DONE = "done"


class TaskPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


def parse_task_status(raw: str | None) -> TaskStatus:
    s = str(raw or "").strip()
    if s.startswith("TaskStatus."):
        s = s.removeprefix("TaskStatus.")
    if s in TaskStatus.__members__:
        return TaskStatus[s]
    try:
        return TaskStatus(s)
    except ValueError:
        return TaskStatus.PLANNING


def parse_task_priority(raw: str | float | int | None) -> TaskPriority:
    if raw is None or raw == "":
        return TaskPriority.P2
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        try:
            iv = int(raw)
            if 0 <= iv <= 3:
                return TaskPriority(f"P{iv}")
        except (ValueError, TypeError):
            pass
    # Google Sheets may send numbers as strings or text with extra noise
    s = str(raw).strip()
    if s.startswith("TaskPriority."):
        s = s.removeprefix("TaskPriority.").strip()
    try:
        return TaskPriority(s)
    except ValueError:
        pass
    m = re.search(r"[Pp]([0-3])\b", s)
    if m:
        try:
            return TaskPriority(f"P{m.group(1)}")
        except ValueError:
            pass
    u = s.upper()
    if u in TaskPriority.__members__:
        return TaskPriority[u]
    if re.fullmatch(r"[0-3]", s):
        return TaskPriority(f"P{s}")
    return TaskPriority.P2


REQUIRED_TASK_COLUMNS = [
    "title",
    "description",
    "status",
    "priority",
    "commit_hash",
    "gerrit_change_id",
    "comment_from_user",
    "agent_reply",
    "updated_at",
]


@dataclass(slots=True)
class TaskRecord:
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority = TaskPriority.P2
    task_id: str = ""
    commit_hash: str = ""
    gerrit_change_id: str = ""
    comment_from_user: str = ""
    agent_reply: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    meta: dict[str, Any] = field(default_factory=dict)


def sheet_cell_for_task_field(task: TaskRecord, field_name: str) -> str:
    """Stable string for writing enum columns back to Sheets/Excel."""
    if field_name == "priority":
        return task.priority.value
    if field_name == "status":
        return task.status.value
    v = getattr(task, field_name, "")
    return "" if v is None else str(v)


class TaskStore(Protocol):
    def list_runnable_tasks(self) -> list[TaskRecord]:
        """Return tasks in runnable state sorted by priority."""

    def claim_task(self, task_id: str, expected_version: int) -> TaskRecord:
        """Move task to in_progress state."""

    def update_task(self, task_id: str, patch: dict[str, Any], expected_version: int) -> TaskRecord:
        """Patch task by ID using optimistic locking."""

    def append_agent_reply(self, task_id: str, text: str, expected_version: int) -> TaskRecord:
        """Append reply text for a task."""
