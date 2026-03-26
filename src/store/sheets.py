"""SheetsStore — Google Sheets をデータベースとして使う実装

シート構成:
  カテゴリ別シート（例: "契約", "許認可証" ...）: レコード本体
  "_state" シート: sync_state（page_tokenなど）

各シートの列構成（A〜K列）:
  A: id  B: record_key  C: status  D: primary_deadline
  E: secondary_deadline  F: created_at  G: updated_at
  H: source  I: drive_file_id  J: notes  K: fields（JSON）
"""
import json
import logging
import os
import uuid
from datetime import date, datetime, timedelta

from googleapiclient.discovery import build

from google_auth import get_credentials
from categories import CATEGORY_REGISTRY
from .base import AbstractStore

logger = logging.getLogger(__name__)

COLUMNS = ["id", "record_key", "status", "primary_deadline",
           "secondary_deadline", "created_at", "updated_at",
           "source", "drive_file_id", "notes", "fields"]
STATE_SHEET = "_state"


class SheetsSync:
    """Sheets API ラッパー（キャッシュ付き）"""
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self._svc = build("sheets", "v4", credentials=get_credentials())
        self._sheet_titles: set[str] | None = None

    def ensure_sheet(self, title: str):
        titles = self._get_titles()
        if title not in titles:
            self._svc.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
            ).execute()
            self._sheet_titles = None  # キャッシュ無効化

    def read(self, sheet: str) -> list[list]:
        try:
            resp = self._svc.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{sheet}'!A:Z",
            ).execute()
            return resp.get("values", [])
        except Exception:
            return []

    def append(self, sheet: str, row: list):
        self._svc.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{sheet}'!A1",
            valueInputOption="RAW",
            body={"values": [row]},
        ).execute()

    def update_row(self, sheet: str, row_index: int, row: list):
        """1-indexed の行番号を指定して更新"""
        self._svc.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{sheet}'!A{row_index}",
            valueInputOption="RAW",
            body={"values": [row]},
        ).execute()

    def _get_titles(self) -> set[str]:
        if self._sheet_titles is None:
            meta = self._svc.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            self._sheet_titles = {
                s["properties"]["title"] for s in meta.get("sheets", [])
            }
        return self._sheet_titles


class SheetsStore(AbstractStore):

    def __init__(self, spreadsheet_id: str):
        self._sheets = SheetsSync(spreadsheet_id)
        self._sheets.ensure_sheet(STATE_SHEET)

    # ── カテゴリシート名 ──────────────────────────────────────────

    def _sheet_name(self, category: str) -> str:
        schema = CATEGORY_REGISTRY.get(category)
        return schema.label if schema else category

    # ── upsert ───────────────────────────────────────────────────

    def upsert(self, client_id: str, category: str, record_key: str,
               fields: dict, **kwargs) -> str:
        sheet = self._sheet_name(category)
        self._sheets.ensure_sheet(sheet)

        rows = self._sheets.read(sheet)
        now = datetime.utcnow().isoformat()

        # ヘッダー行がなければ作成
        if not rows:
            self._sheets.append(sheet, COLUMNS)
            rows = [COLUMNS]

        # record_key で既存レコードを検索
        header = rows[0]
        try:
            key_col = header.index("record_key")
            id_col  = header.index("id")
        except ValueError:
            self._sheets.update_row(sheet, 1, COLUMNS)
            header = COLUMNS
            key_col = COLUMNS.index("record_key")
            id_col  = COLUMNS.index("id")

        existing_row_index = None
        existing_id = None
        for i, row in enumerate(rows[1:], start=2):
            val = row[key_col] if len(row) > key_col else ""
            if val == record_key:
                existing_row_index = i
                existing_id = row[id_col] if len(row) > id_col else ""
                break

        fields_json = json.dumps(fields, ensure_ascii=False)
        record_id = existing_id or str(uuid.uuid4())[:8]

        new_row = [
            record_id,
            record_key,
            kwargs.get("status", "active"),
            kwargs.get("primary_deadline", "") or "",
            kwargs.get("secondary_deadline", "") or "",
            now if not existing_row_index else (rows[existing_row_index - 1][5] if len(rows[existing_row_index - 1]) > 5 else now),
            now,
            kwargs.get("source", "manual"),
            kwargs.get("drive_file_id", "") or "",
            kwargs.get("notes", "") or "",
            fields_json,
        ]

        if existing_row_index:
            self._sheets.update_row(sheet, existing_row_index, new_row)
        else:
            self._sheets.append(sheet, new_row)

        return record_id

    # ── get_all ──────────────────────────────────────────────────

    def get_all(self, client_id: str, category: str = None,
                status: str = "active") -> list[dict]:
        categories = [category] if category else list(CATEGORY_REGISTRY.keys())
        result = []
        for cat in categories:
            sheet = self._sheet_name(cat)
            rows = self._sheets.read(sheet)
            if len(rows) < 2:
                continue
            header = rows[0]
            for row in rows[1:]:
                record = self._row_to_dict(header, row, cat)
                if status == "all" or record.get("status") == status:
                    result.append(record)
        return result

    # ── get_expiring ─────────────────────────────────────────────

    def get_expiring(self, client_id: str, within_days: int) -> list[dict]:
        today = date.today()
        limit = today + timedelta(days=within_days)
        result = []
        for cat in CATEGORY_REGISTRY:
            sheet = self._sheet_name(cat)
            rows = self._sheets.read(sheet)
            if len(rows) < 2:
                continue
            header = rows[0]
            for row in rows[1:]:
                record = self._row_to_dict(header, row, cat)
                if record.get("status") != "active":
                    continue
                dl = record.get("primary_deadline", "")
                if not dl:
                    continue
                try:
                    d = date.fromisoformat(str(dl))
                    if today <= d <= limit:
                        result.append(record)
                except ValueError:
                    continue
        result.sort(key=lambda r: r.get("primary_deadline", ""))
        return result

    # ── sync_state ───────────────────────────────────────────────

    def get_sync_state(self, key: str) -> str | None:
        rows = self._sheets.read(STATE_SHEET)
        for row in rows:
            if row and row[0] == key:
                return row[1] if len(row) > 1 else None
        return None

    def set_sync_state(self, key: str, value: str):
        self._sheets.ensure_sheet(STATE_SHEET)
        rows = self._sheets.read(STATE_SHEET)
        for i, row in enumerate(rows, start=1):
            if row and row[0] == key:
                self._sheets.update_row(STATE_SHEET, i, [key, value])
                return
        self._sheets.append(STATE_SHEET, [key, value])

    # ── ヘルパー ─────────────────────────────────────────────────

    def _row_to_dict(self, header: list, row: list, category: str) -> dict:
        d = {}
        for i, col in enumerate(header):
            d[col] = row[i] if i < len(row) else ""
        d["category"] = category
        if d.get("fields"):
            try:
                d["fields"] = json.loads(d["fields"])
            except (ValueError, TypeError):
                d["fields"] = {}
        return d
