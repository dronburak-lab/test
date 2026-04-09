# Gerrit Workflow (Agent-Native)

The runner uses agent-native git operations:

1. `git fetch --all --prune`
2. `git switch -C agent/<title-slug>`
3. `git rebase <target_branch>`
4. `git commit -am "task: <title>"`
5. `git push origin HEAD`

After push, the orchestrator stores:

- `commit_hash` (full SHA),
- `gerrit_change_id` (if present in push output).
