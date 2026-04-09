from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from automation.task_store.base import TaskRecord


@dataclass(slots=True)
class RunnerResult:
    success: bool
    summary: str
    commit_hash: str = ""
    gerrit_change_id: str = ""
    status: str = ""


class AgentRunner(Protocol):
    def start_task(self, task: TaskRecord) -> RunnerResult:
        """Start execution for a freshly claimed task."""

    def continue_task(self, task: TaskRecord, comment: str) -> RunnerResult:
        """Continue work from user feedback."""

    def collect_result(self, run_id: str) -> RunnerResult:
        """Optional async hook for external runners."""
