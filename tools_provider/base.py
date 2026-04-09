from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ToolResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


class ToolsProvider(Protocol):
    def run(self, command: str, cwd: str) -> ToolResult:
        """Run a command using the selected tool backend."""
