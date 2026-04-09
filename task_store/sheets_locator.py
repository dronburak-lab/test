from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SheetLocation:
    spreadsheet_id: str
    worksheet_name: str | None = None
    worksheet_gid: int | None = None

    def validate(self) -> None:
        if not self.spreadsheet_id.strip():
            raise ValueError("spreadsheet_id is required")
        if not self.worksheet_name and self.worksheet_gid is None:
            raise ValueError("worksheet_name or worksheet_gid is required")

    @classmethod
    def from_config(cls, data: dict) -> "SheetLocation":
        location = cls(
            spreadsheet_id=str(data.get("spreadsheet_id", "")),
            worksheet_name=data.get("worksheet_name"),
            worksheet_gid=data.get("worksheet_gid"),
        )
        location.validate()
        return location
