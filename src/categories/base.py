from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class FieldDef:
    name: str                       # フィールドキー（英語）
    label: str                      # 表示ラベル（日本語）
    type: str = "str"               # str / date / int / float / bool
    required: bool = False
    is_primary_deadline: bool = False
    is_secondary_deadline: bool = False
    hint: str = ""                  # 入力例・説明


class CategorySchema:
    category_id: str
    label: str
    source_type: str  # "auto" / "semi_auto" / "manual"
    fields: list[FieldDef]

    def get_sheets_headers(self) -> list[str]:
        base = ["ID", "record_key", "status", "primary_deadline",
                "secondary_deadline", "created_at", "updated_at", "notes"]
        return base + [f.label for f in self.fields]

    def extract_deadlines(self, fields: dict) -> tuple[date | None, date | None]:
        primary = None
        secondary = None
        for f in self.fields:
            val = fields.get(f.name)
            if not val:
                continue
            try:
                d = date.fromisoformat(str(val))
            except ValueError:
                continue
            if f.is_primary_deadline and primary is None:
                primary = d
            if f.is_secondary_deadline and secondary is None:
                secondary = d
        return primary, secondary

    def to_record_row(self, record: dict) -> list[Any]:
        f = record.get("fields", {})
        row = [
            record.get("id", ""),
            record.get("record_key", ""),
            record.get("status", ""),
            record.get("primary_deadline", "") or "",
            record.get("secondary_deadline", "") or "",
            (record.get("created_at", "") or "")[:10],
            (record.get("updated_at", "") or "")[:10],
            record.get("notes", "") or "",
        ]
        for fd in self.fields:
            val = f.get(fd.name, "")
            row.append("" if val is None else val)
        return row
