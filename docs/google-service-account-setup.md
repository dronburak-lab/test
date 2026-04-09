# Google Service Account Setup

## 1. Create Service Account

- In Google Cloud Console create a service account for the orchestrator.
- Enable Google Sheets API in the same project.

## 2. Generate Credentials

- Create JSON key for the service account.
- Do not commit it to git.

## 3. Share Spreadsheet

- Share the target Google Sheet with the service account email.
- Grant editor access only to required documents.

## 4. Export Secret

Set JSON in environment variable expected by config:

```bash
export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat /secure/path/service-account.json)"
```

## 5. Configure Task Store

Set in `automation/config.yaml`:

- `task_store.backend: google_sheets`
- `task_store.google_sheets.spreadsheet_id`
- `task_store.google_sheets.worksheet_name` or `worksheet_gid`
- `task_store.google_sheets.credentials_json_env: GOOGLE_SERVICE_ACCOUNT_JSON`
