from __future__ import annotations

import argparse
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# Allow `python ./task_orchestrator.py` from inside `automation/` (repo root must be on sys.path).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from automation.agent_runner.cursor_runner import CursorRunner, CursorRunnerConfig
from automation.policy_guard import PolicyConfig, PolicyGuard
from automation.task_store.excel_store import ExcelTaskStore
from automation.task_store.google_sheets_store import GoogleSheetsTaskStore
from automation.task_store.sheets_locator import SheetLocation
from automation.task_store.base import TaskStatus
from automation.tools_provider.local_provider import LocalToolsProvider
from automation.tools_provider.mcp_provider import MCPConfig, MCPToolsProvider

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_config(path: str) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read config files")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@contextmanager
def file_lock(path: str):
    lock_file = Path(path)
    if lock_file.exists():
        raise RuntimeError(f"Lock file exists: {lock_file}")
    lock_file.write_text(str(os.getpid()), encoding="utf-8")
    try:
        yield
    finally:
        if lock_file.exists():
            lock_file.unlink()


def build_task_store(config: dict[str, Any], config_dir: Path | None = None):
    store_cfg = config["task_store"]
    if store_cfg["backend"] == "google_sheets":
        location = SheetLocation.from_config(store_cfg["google_sheets"])
        return GoogleSheetsTaskStore(location, store_cfg["google_sheets"]["credentials_json_env"])
    if store_cfg["backend"] == "excel":
        excel = store_cfg["excel"]
        file_path = excel["file_path"]
        p = Path(file_path)
        if config_dir is not None and not p.is_absolute():
            file_path = str((config_dir / p).resolve())
        return ExcelTaskStore(file_path, excel.get("sheet_name", "tasks"))
    raise ValueError(f"Unknown task_store backend: {store_cfg['backend']}")


def build_tools_provider(config: dict[str, Any]):
    tools = config["tools_provider"]
    if tools["backend"] == "local":
        return LocalToolsProvider()
    if tools["backend"] == "mcp":
        m = tools.get("mcp", {})
        return MCPToolsProvider(MCPConfig(server=m["server"], timeout_seconds=int(m.get("timeout_seconds", 30))))
    raise ValueError(f"Unknown tools backend: {tools['backend']}")


def build_policy(config: dict[str, Any], workspace: str) -> PolicyGuard:
    p = config["policy"]
    cfg = PolicyConfig(
        allowed_commands=p.get("allowed_commands", []),
        allowed_command_prefixes=p.get("allowed_command_prefixes", []),
        blocked_commands=p.get("blocked_commands", []),
        allowed_paths=p.get("allowed_paths", ["."]),
        blocked_paths=p.get("blocked_paths", []),
        allow_network=bool(p.get("allow_network", False)),
    )
    return PolicyGuard(cfg, workspace=workspace)


def run_loop(config: dict[str, Any], once: bool = False, config_dir: Path | None = None) -> None:
    orch = config["orchestrator"]
    workspace = str(Path.cwd())
    task_store = build_task_store(config, config_dir=config_dir)
    tools = build_tools_provider(config)
    policy = build_policy(config, workspace=workspace)
    ar = config.get("agent_runner", {})
    ca = ar.get("cursor_agent", {})
    gerrit = config.get("gerrit", {})
    runner = CursorRunner(
        CursorRunnerConfig(
            workspace=workspace,
            target_branch=gerrit.get("target_branch", "main"),
            gerrit_remote=gerrit.get("remote", "origin"),
            push_ref_template=str(
                gerrit.get("push_ref_template", "refs/heads/agent/{slug}-{task_id}")
            ),
            push_force_with_lease=bool(gerrit.get("push_force_with_lease", False)),
            cursor_agent_command_prefix=str(
                ca.get("command_prefix", "cursor agent -p --force")
            ),
            agent_output_max_chars=int(ca.get("agent_output_max_chars", 8000)),
        ),
        tools=tools,
        policy=policy,
    )

    lock_path = orch.get("lock_file", ".agent-orchestrator.lock")
    poll_s = int(orch.get("poll_interval_seconds", 15))

    with file_lock(lock_path):
        while True:
            tasks = task_store.list_runnable_tasks()
            if not tasks:
                if once:
                    return
                time.sleep(poll_s)
                continue

            task = tasks[0]
            if task.status == TaskStatus.ON_REVIEW and task.comment_from_user.strip():
                task = task_store.update_task(
                    task.task_id,
                    patch={"status": TaskStatus.IN_PROGRESS.value},
                    expected_version=0,
                )
            claimed = task_store.claim_task(task.task_id, expected_version=0)
            print(
                f"[orchestrator] Начало выполнения задачи: id={claimed.task_id!r}, "
                f"title={claimed.title!r}",
                flush=True,
            )
            try:
                if task.status == TaskStatus.ON_REVIEW:
                    result = runner.continue_task(claimed, claimed.comment_from_user)
                else:
                    result = runner.start_task(claimed)
                patch = {
                    "commit_hash": result.commit_hash,
                    "gerrit_change_id": result.gerrit_change_id,
                    "status": result.status,
                    "agent_reply": result.summary,
                    "comment_from_user": "",
                }
                task_store.update_task(claimed.task_id, patch=patch, expected_version=0)
            except Exception as exc:  # pylint: disable=broad-except
                task_store.update_task(
                    claimed.task_id,
                    patch={"status": TaskStatus.ON_REVIEW.value, "agent_reply": f"Execution failed: {exc}"},
                    expected_version=0,
                )

            if once:
                return


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous task orchestrator")
    parser.add_argument("--config", default="automation/config.yaml", help="Path to config file")
    parser.add_argument("--once", action="store_true", help="Run one iteration and exit")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(str(config_path))
    run_loop(config, once=args.once, config_dir=config_path.parent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
