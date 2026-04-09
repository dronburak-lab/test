from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PolicyConfig:
    allowed_commands: list[str]
    allowed_command_prefixes: list[str]
    blocked_commands: list[str]
    allowed_paths: list[str]
    blocked_paths: list[str]
    allow_network: bool = False


class PolicyError(RuntimeError):
    pass


class PolicyGuard:
    def __init__(self, config: PolicyConfig, workspace: str) -> None:
        self.config = config
        self.workspace = Path(workspace).resolve()

    def validate_command(self, command: str) -> None:
        if any(token in command for token in self.config.blocked_commands):
            raise PolicyError(f"Blocked command: {command}")

        if command in self.config.allowed_commands:
            return

        if any(command.startswith(prefix) for prefix in self.config.allowed_command_prefixes):
            return

        raise PolicyError(f"Command is not whitelisted: {command}")

    def validate_path(self, path: str) -> None:
        candidate = Path(path).resolve()
        if any(str(candidate).startswith(blocked) for blocked in self.config.blocked_paths):
            raise PolicyError(f"Blocked path: {candidate}")
        if not any(str(candidate).startswith(str((self.workspace / allowed).resolve())) for allowed in self.config.allowed_paths):
            raise PolicyError(f"Path outside allowed roots: {candidate}")
