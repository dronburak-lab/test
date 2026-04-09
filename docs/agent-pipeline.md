# Autonomous Agent Pipeline

This pipeline processes tasks from Google Sheets (or Excel fallback), runs task execution through an agent in a dedicated branch/worktree flow, and writes status + git metadata back to the task source.

## Main Loop

1. Read runnable tasks (`ready_to_work`, or `on_review` with comment).
2. Claim a task and switch status to `in_progress`.
3. Run agent execution (`start_task` or `continue_task`).
4. Commit and push to Gerrit.
5. Write back `commit_hash`, `gerrit_change_id`, `agent_reply`, and target status.
6. On failure write diagnostics and keep task in `on_review`.

## Key Guarantees

- Single active orchestrator by lock file.
- Command/path safety via whitelist policy.
- Swappable `TaskStore` backend (`google_sheets` / `excel`).
- Swappable `ToolsProvider` backend (`local` / `mcp` placeholder).
