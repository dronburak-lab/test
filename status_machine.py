from __future__ import annotations

from automation.task_store.base import TaskStatus


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PLANNING: {TaskStatus.READY_TO_WORK},
    TaskStatus.READY_TO_WORK: {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.ON_REVIEW, TaskStatus.DONE},
    TaskStatus.ON_REVIEW: {TaskStatus.IN_PROGRESS, TaskStatus.DONE},
    TaskStatus.DONE: set(),
}


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def require_transition(current: TaskStatus, target: TaskStatus) -> None:
    if not can_transition(current, target):
        raise ValueError(f"Transition not allowed: {current.value} -> {target.value}")
