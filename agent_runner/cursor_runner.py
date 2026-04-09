from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shlex

from automation.agent_runner.base import RunnerResult
from automation.policy_guard import PolicyGuard
from automation.task_store.base import TaskRecord, TaskStatus
from automation.tools_provider.base import ToolsProvider


@dataclass(slots=True)
class CursorRunnerConfig:
    workspace: str
    target_branch: str
    gerrit_remote: str = "origin"
    push_ref_template: str = "refs/for/{target_branch}"
    # Shell prefix before the shlex-quoted task prompt (headless agent with edits).
    cursor_agent_command_prefix: str = "cursor agent -p --force"
    # Max chars of agent stdout+stderr stored in agent_reply / RunnerResult.summary.
    agent_output_max_chars: int = 8000


class CursorRunner:
    def __init__(self, config: CursorRunnerConfig, tools: ToolsProvider, policy: PolicyGuard) -> None:
        self.config = config
        self.tools = tools
        self.policy = policy
        self.workspace = str(Path(config.workspace).resolve())

    def _run(self, command: str):
        self.policy.validate_command(command)
        return self.tools.run(command, cwd=self.workspace)

    def _slug(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
        return slug or "task"

    def _truncate(self, text: str) -> str:
        cap = max(256, int(self.config.agent_output_max_chars))
        if len(text) <= cap:
            return text
        return text[: cap - 3] + "..."

    def _build_prompt(self, task: TaskRecord, feedback: str | None) -> str:
        parts = [
            "You are working in this git repository checkout. Follow the instructions exactly.",
            "",
            f"Title: {task.title.strip()}",
            "",
            "Description:",
            task.description.strip() or "(empty)",
        ]
        if feedback and feedback.strip():
            parts.extend(["", "Additional feedback from the reviewer:", feedback.strip()])
        return "\n".join(parts)

    def _run_agent_for_description(self, task: TaskRecord, feedback: str | None) -> str:
        prefix = (self.config.cursor_agent_command_prefix or "").strip()
        if not prefix:
            raise RuntimeError(
                "agent_runner.cursor_agent.command_prefix is empty; set a non-empty value "
                "(e.g. cursor agent -p --force) to run the task description."
            )
        prompt = self._build_prompt(task, feedback)
        print(
            f"[cursor-runner] Запуск агента по description ({len(prompt)} символов в промпте).",
            flush=True,
        )
        cmd = f"{prefix} {shlex.quote(prompt)}"
        res = self._run(cmd)
        log = (res.stdout or "") + (res.stderr or "")
        if res.exit_code != 0:
            raise RuntimeError(
                f"Agent command failed (exit {res.exit_code}): {self._truncate(log)}"
            )
        return log

    def _list_remote_branch_refs(self, remote: str) -> list[str]:
        res = self._run(f"git for-each-ref --format=%(refname:short) refs/remotes/{remote}/")
        if res.exit_code != 0:
            return []
        refs: list[str] = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line or line.endswith("/HEAD"):
                continue
            refs.append(line)
        return sorted(refs)

    def _pick_remote_ref(self, refs: list[str]) -> str | None:
        if not refs:
            return None
        tails: dict[str, str] = {}
        for ref in refs:
            tail = ref.split("/", 1)[-1]
            tails[tail] = ref
        for name in (self.config.target_branch, "main", "master", "develop", "trunk"):
            if name in tails:
                return tails[name]
        return refs[0]

    def _resolve_rebase_upstream(self) -> str:
        """Pick a ref that exists locally after fetch."""
        remote = self.config.gerrit_remote

        sym = self._run(f"git symbolic-ref -q refs/remotes/{remote}/HEAD")
        if sym.exit_code == 0:
            raw = sym.stdout.strip()
            if raw.startswith("refs/remotes/"):
                return raw[len("refs/remotes/") :]

        tried: list[str] = []
        for name in (self.config.target_branch, "main", "master", "develop", "trunk"):
            ref = f"{remote}/{name}"
            tried.append(ref)
            check = self._run(f"git rev-parse --verify {ref}")
            if check.exit_code == 0:
                return ref

        refs = self._list_remote_branch_refs(remote)
        picked = self._pick_remote_ref(refs)
        if picked:
            return picked

        remotes_res = self._run("git remote")
        if remotes_res.exit_code == 0:
            for other in remotes_res.stdout.split():
                if other == remote:
                    continue
                refs = self._list_remote_branch_refs(other)
                picked = self._pick_remote_ref(refs)
                if picked:
                    return picked

        br = self._run("git branch -r")
        branch_hint = (br.stdout.strip() or "(empty)")[:500]
        raise RuntimeError(
            "Cannot rebase: no remote-tracking branch found. "
            f"Configured remote is {remote!r}; tried {', '.join(tried[:6])}… "
            "`git branch -r`:\n"
            f"{branch_hint}\n"
            "Fix: run from a repo clone with `git fetch --all`, set `gerrit.remote` to your remote name "
            "(see `git remote -v`), and `gerrit.target_branch` to an existing branch name."
        )

    def _prepare_branch(self, task: TaskRecord) -> None:
        branch_name = f"agent/{self._slug(task.title)}"
        res = self._run("git fetch --all --prune")
        if res.exit_code != 0:
            raise RuntimeError(res.stderr or res.stdout)
        base_ref = self._resolve_rebase_upstream()
        for cmd in [
            f"git switch -C {branch_name}",
            f"git rebase {base_ref}",
        ]:
            res = self._run(cmd)
            if res.exit_code != 0:
                raise RuntimeError(res.stderr or res.stdout)

    def _commit_and_push(self, task: TaskRecord) -> tuple[str, str]:
        safe_title = task.title[:72].replace("\n", " ").strip()
        commit_msg = f"task: {safe_title}"
        for cmd in [
            "git add -A",
            f"git commit -m {shlex.quote(commit_msg)}",
        ]:
            res = self._run(cmd)
            if res.exit_code != 0:
                raise RuntimeError(
                    f"git failed after agent ({cmd!r}): {res.stderr or res.stdout}"
                )

        hash_res = self._run("git rev-parse HEAD")
        if hash_res.exit_code != 0:
            raise RuntimeError(hash_res.stderr or hash_res.stdout)
        commit_hash = hash_res.stdout.strip()

        push_ref = self.config.push_ref_template.format(target_branch=self.config.target_branch)
        push_res = self._run(f"git push {self.config.gerrit_remote} HEAD:{push_ref}")
        if push_res.exit_code != 0:
            raise RuntimeError(push_res.stderr or push_res.stdout)

        return commit_hash, self._extract_change_id(push_res.stdout + push_res.stderr)

    def _extract_change_id(self, text: str) -> str:
        for line in text.splitlines():
            if "Change-Id:" in line:
                return line.split("Change-Id:", 1)[1].strip()
        return ""

    def start_task(self, task: TaskRecord) -> RunnerResult:
        print(
            f"[cursor-runner] Начало выполнения задачи: id={task.task_id!r}, title={task.title!r}",
            flush=True,
        )
        self._prepare_branch(task)
        agent_log = self._run_agent_for_description(task, None)
        commit_hash, change_id = self._commit_and_push(task)
        summary = self._truncate(agent_log.strip() or "Task completed (no agent output).")
        return RunnerResult(
            success=True,
            summary=summary,
            commit_hash=commit_hash,
            gerrit_change_id=change_id,
            status=TaskStatus.ON_REVIEW.value,
        )

    def continue_task(self, task: TaskRecord, comment: str) -> RunnerResult:
        print(
            f"[cursor-runner] Начало выполнения задачи (продолжение): id={task.task_id!r}, "
            f"title={task.title!r}",
            flush=True,
        )
        self._prepare_branch(task)
        agent_log = self._run_agent_for_description(task, comment)
        commit_hash, change_id = self._commit_and_push(task)
        summary = self._truncate(agent_log.strip() or f"Feedback processed: {comment}")
        return RunnerResult(
            success=True,
            summary=summary,
            commit_hash=commit_hash,
            gerrit_change_id=change_id,
            status=TaskStatus.ON_REVIEW.value,
        )

    def collect_result(self, run_id: str) -> RunnerResult:
        return RunnerResult(success=False, summary=f"collect_result not implemented for run_id={run_id}")
