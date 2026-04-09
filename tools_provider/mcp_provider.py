from __future__ import annotations

from dataclasses import dataclass

from automation.tools_provider.base import ToolResult


@dataclass(slots=True)
class MCPConfig:
    server: str
    timeout_seconds: int = 30


class MCPToolsProvider:
    """
    Placeholder adapter for future MCP tool execution.
    """

    def __init__(self, config: MCPConfig) -> None:
        self.config = config

    def run(self, command: str, cwd: str) -> ToolResult:
        raise NotImplementedError(
            f"MCP provider is not wired yet. target={self.config.server}, command={command}, cwd={cwd}"
        )
