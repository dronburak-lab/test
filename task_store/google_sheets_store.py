from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from automation.status_machine import require_transition
from automation.task_store.base import (
    REQUIRED_TASK_COLUMNS,
    TaskRecord,
    TaskStatus,
    parse_task_priority,
    parse_task_status,
    sheet_cell_for_task_field,
)
from automation.task_store.sheets_locator import SheetLocation

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:  # pragma: no cover
    Credentials = None
    build = None
    HttpError = None  # type: ignore[misc, assignment]


class GoogleSheetsTaskStore:
    def __init__(self, location: SheetLocation, credentials_json_env: str) -> None:
        if Credentials is None or build is None:
            raise RuntimeError("google-api-python-client and google-auth are required")
        self.location = location
        self.creds = self._build_credentials(credentials_json_env)
        self.api = build("sheets", "v4", credentials=self.creds)
        self.range_name = f"{self.location.worksheet_name}!A:Z"

    def _build_credentials(self, env_var: str) -> Credentials:
        raw = os.getenv(env_var, "")
        if not raw.strip():
            raise RuntimeError(f"Missing service account JSON in env: {env_var}")
        info = json.loads(raw)
        self._service_account_email = str(info.get("client_email", "") or "")
        return Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )

    def _reraise_sheets_http(self, exc: Exception) -> None:
        if HttpError is None or not isinstance(exc, HttpError):
            raise exc
        status = getattr(exc.resp, "status", None)
        sid = self.location.spreadsheet_id
        who = self._service_account_email or "(client_email missing in JSON)"
        if status == 403:
            raise RuntimeError(
                "Google Sheets returned 403 (no access). Share the spreadsheet with the service "
                f"account as Editor: {who}. "
                f"Confirm spreadsheet_id matches the file (id in URL): {sid!r}. "
                "In Google Cloud, enable the Google Sheets API for the project that owns this key."
            ) from exc
        if status == 404:
            raise RuntimeError(
                f"Spreadsheet not found (404). Check spreadsheet_id: {sid!r}."
            ) from exc
        raise exc

    def _read_rows(self) -> tuple[list[str], list[list[str]]]:
        try:
            values = (
                self.api.spreadsheets()
                .values()
                .get(spreadsheetId=self.location.spreadsheet_id, range=self.range_name)
                .execute()
                .get("values", [])
            )
        except Exception as exc:
            self._reraise_sheets_http(exc)
        raw = values[0] if values else []
        headers = [str(h).strip() for h in raw]
        missing = [c for c in REQUIRED_TASK_COLUMNS if c not in headers]
        if missing:
            raise ValueError(
                "Missing required column(s): "
                + ", ".join(missing)
                + ". Row 1 of the worksheet must list every header from docs/google-sheets-template.md "
                "(exact names, one column per cell)."
            )
        return headers, values[1:]

    def _parse(self, headers: list[str], row: list[str], row_no: int) -> TaskRecord:
        data = {h: row[i] if i < len(row) else "" for i, h in enumerate(headers)}
        return TaskRecord(
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=parse_task_status(data.get("status")),
            priority=parse_task_priority(data.get("priority")),
            task_id=data.get("task_id", f"row-{row_no}"),
            commit_hash=data.get("commit_hash", ""),
            gerrit_change_id=data.get("gerrit_change_id", ""),
            comment_from_user=data.get("comment_from_user", ""),
            agent_reply=data.get("agent_reply", ""),
            updated_at=data.get("updated_at", ""),
            meta={"row_no": row_no},
        )

    def _write_patch(self, task: TaskRecord, headers: list[str], patch: dict[str, Any]) -> TaskRecord:
        row_no = task.meta["row_no"]
        row_values = [""] * len(headers)
        for i, h in enumerate(headers):
            row_values[i] = sheet_cell_for_task_field(task, h) if hasattr(task, h) else ""
        for key, value in patch.items():
            if key in headers:
                row_values[headers.index(key)] = str(value)
        row_values[headers.index("updated_at")] = datetime.now(timezone.utc).isoformat()

        write_range = f"{self.location.worksheet_name}!A{row_no}:{chr(64 + len(headers))}{row_no}"
        try:
            self.api.spreadsheets().values().update(
                spreadsheetId=self.location.spreadsheet_id,
                range=write_range,
                valueInputOption="RAW",
                body={"values": [row_values]},
            ).execute()
        except Exception as exc:
            self._reraise_sheets_http(exc)

        updated = self._parse(headers, row_values, row_no)
        return updated

    def list_runnable_tasks(self) -> list[TaskRecord]:
        headers, rows = self._read_rows()
        status_idx = headers.index("status")
        comment_idx = headers.index("comment_from_user")
        tasks = []
        for i, row in enumerate(rows):
            if not row:
                continue
            status = row[status_idx]
            comment = row[comment_idx] if comment_idx < len(row) else ""
            if status == TaskStatus.READY_TO_WORK.value:
                tasks.append(self._parse(headers, row, i + 2))
            elif status == TaskStatus.ON_REVIEW.value and str(comment).strip():
                tasks.append(self._parse(headers, row, i + 2))
        return sorted(tasks, key=lambda x: (x.priority.value, x.task_id))

    def _get_task(self, task_id: str) -> tuple[TaskRecord, list[str]]:
        headers, rows = self._read_rows()
        for i, row in enumerate(rows):
            if not row:
                continue
            candidate = row[headers.index("task_id")] if "task_id" in headers and headers.index("task_id") < len(row) else f"row-{i+2}"
            if candidate == task_id:
                return self._parse(headers, row, i + 2), headers
        raise KeyError(f"Task not found: {task_id}")

    def claim_task(self, task_id: str, expected_version: int) -> TaskRecord:
        task, headers = self._get_task(task_id)
        require_transition(task.status, TaskStatus.IN_PROGRESS)
        return self._write_patch(task, headers, {"status": TaskStatus.IN_PROGRESS.value})

    def update_task(self, task_id: str, patch: dict[str, Any], expected_version: int) -> TaskRecord:
        task, headers = self._get_task(task_id)
        return self._write_patch(task, headers, patch)

    def append_agent_reply(self, task_id: str, text: str, expected_version: int) -> TaskRecord:
        task, headers = self._get_task(task_id)
        combined = f"{task.agent_reply}\n{text}".strip()
        return self._write_patch(task, headers, {"agent_reply": combined})
