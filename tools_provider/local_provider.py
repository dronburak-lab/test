from __future__ import annotations

import subprocess

from automation.tools_provider.base import ToolResult


class LocalToolsProvider:
    def run(self, command: str, cwd: str) -> ToolResult:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
        return ToolResult(
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
