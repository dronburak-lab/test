# Google Sheets Task Template

Create a sheet named `tasks`. **Row 1** must be exactly these headers (copy the line below into the first row, one cell per column):

```text
title	description	status	priority	commit_hash	gerrit_change_id	comment_from_user	agent_reply	updated_at
```

Optional but recommended: add a `task_id` column (any position) so tasks are stable when you refer to them by ID.

Column reference:

- `title`
- `description`
- `status` (`planning`, `ready_to_work`, `in_progress`, `on_review`, `done`)
- `priority` (`P0`, `P1`, `P2`, `P3`)
- `commit_hash`
- `gerrit_change_id`
- `comment_from_user`
- `agent_reply`
- `updated_at`

Recommended optional technical columns:

- `row_etag`
- `sheet_id`
- `last_writer`
