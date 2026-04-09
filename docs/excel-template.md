# Excel Fallback Template

For offline mode, use an `.xlsx` file with a `tasks` worksheet and the same schema as Google Sheets:

- `title`, `description`
- `status` (`planning`, `ready_to_work`, `in_progress`, `on_review`, `done`)
- `priority` (`P0`, `P1`, `P2`, `P3`)
- `commit_hash`, `gerrit_change_id`
- `comment_from_user`, `agent_reply`, `updated_at`

## Generate template file

Dependency:

`python -m pip install openpyxl`

Run:

`python automation/scripts/create_excel_template.py --output automation/tasks.xlsx --sheet-name tasks`

Or from `automation/` directory:

`python ./scripts/create_excel_template.py --output ./tasks.xlsx --sheet-name tasks`

Optional example row:

`python automation/scripts/create_excel_template.py --with-example-row`

Generated template auto-adds dropdown lists:

- `status`: `planning`, `ready_to_work`, `in_progress`, `on_review`, `done`
- `priority`: `P0`, `P1`, `P2`, `P3`
