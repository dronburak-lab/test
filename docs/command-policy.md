# Command Policy

`PolicyGuard` blocks commands/paths outside the configured allowlist.

## Policy Fields

- `allowed_commands`: exact command matches.
- `allowed_command_prefixes`: prefix-based allow rules.
- `blocked_commands`: denylist tokens (checked first).
- `allowed_paths`: allowed root paths (relative to workspace).
- `blocked_paths`: explicit blocked roots.
- `allow_network`: reserved for future provider-level checks.

## MVP Blocked Operations

- `rm -rf`
- `git reset --hard`
- `sudo`
- writes outside workspace roots
