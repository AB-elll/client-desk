"""Google Sheets ダッシュボード同期"""
import logging
import os
from datetime import datetime

from googleapiclient.discovery import build

from categories import CATEGORY_REGISTRY
from db import get_expiring_records, get_records, set_sync_state
from google_auth import get_credentials

logger = logging.getLogger(__name__)


class SheetsSync:
    def __init__(self, config: dict):
        self.spreadsheet_id = os.environ["CLIENTDESK_SHEET_ID"]
        self.alert_thresholds = config.get("alerts", {}).get(
            "default_thresholds_days", [90, 30, 7]
        )
        self._sheets = build("sheets", "v4", credentials=get_credentials())

    def sync_all(self, client_id: str):
        """全カテゴリをSheetsに同期"""
        requests = []
        sheet_titles = self._get_existing_sheets()

        for cat_id, schema in CATEGORY_REGISTRY.items():
            records = get_records(client_id, cat_id)
            headers = schema.get_sheets_headers()
            rows = [schema.to_record_row(r) for r in records]

            if schema.label not in sheet_titles:
                requests.append(self._add_sheet_request(schema.label))

        # シート追加をバッチ実行
        if requests:
            self._sheets.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": requests},
            ).execute()
            sheet_titles = self._get_existing_sheets()

        # データ書き込み
        data = []
        for cat_id, schema in CATEGORY_REGISTRY.items():
            records = get_records(client_id, cat_id)
            headers = schema.get_sheets_headers()
            rows = [headers] + [schema.to_record_row(r) for r in records]
            data.append({
                "range": f"'{schema.label}'!A1",
                "values": rows,
            })

        if data:
            self._sheets.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"valueInputOption": "RAW", "data": data},
            ).execute()
            logger.info(f"Sheets sync: {len(data)} sheets updated")

        # アラートシート
        self._sync_alert_sheet(client_id)

        set_sync_state("sheets_last_synced_at", datetime.utcnow().isoformat())

    def _sync_alert_sheet(self, client_id: str):
        """期限アラートシートを更新"""
        sheet_titles = self._get_existing_sheets()
        alert_label = "⚠️ 期限アラート"

        if alert_label not in sheet_titles:
            self._sheets.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [self._add_sheet_request(alert_label)]},
            ).execute()

        max_days = max(self.alert_thresholds)
        expiring = get_expiring_records(client_id, max_days)

        headers = ["期限まで", "カテゴリ", "名称", "期限日", "ステータス", "更新日"]
        rows = [headers]
        today = datetime.utcnow().date()

        for r in expiring:
            if not r.get("primary_deadline"):
                continue
            try:
                dl = datetime.strptime(r["primary_deadline"], "%Y-%m-%d").date()
                days_left = (dl - today).days
            except ValueError:
                continue

            schema = CATEGORY_REGISTRY.get(r["category"])
            cat_label = schema.label if schema else r["category"]
            rows.append([
                f"{days_left}日",
                cat_label,
                r.get("record_key", ""),
                r["primary_deadline"],
                r["status"],
                (r.get("updated_at") or "")[:10],
            ])

        self._sheets.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{alert_label}'!A1",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()
        logger.info(f"Alert sheet updated: {len(rows) - 1} items")

    def _get_existing_sheets(self) -> set[str]:
        meta = self._sheets.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id
        ).execute()
        return {s["properties"]["title"] for s in meta.get("sheets", [])}

    def _add_sheet_request(self, title: str) -> dict:
        return {"addSheet": {"properties": {"title": title}}}
