"""ダッシュボード同期（SheetsStoreを使う場合はストアがそのままダッシュボード）"""
import logging
from datetime import datetime

from categories import CATEGORY_REGISTRY

logger = logging.getLogger(__name__)


def sync_dashboard(client_id: str, store):
    """
    SheetsStore の場合: ストアがダッシュボードを兼ねるため追加作業なし。
    将来 SupabaseStore に移行した場合: Sheetsへのエクスポートをここに実装する。
    """
    store_type = type(store).__name__

    if store_type == "SheetsStore":
        # Sheetsがそのままダッシュボード。アラートシートだけ更新。
        _update_alert_sheet(client_id, store)
        logger.info("Sheets is the store — dashboard is always up-to-date")
        return

    # SupabaseStore → Sheets へエクスポート（将来実装）
    raise NotImplementedError(
        "Supabase → Sheets export is not implemented yet. "
        "Use Supabase Studio or implement here."
    )


def _update_alert_sheet(client_id: str, store):
    """期限アラートシートを更新（SheetsStore専用）"""
    from datetime import date, timedelta
    from store.sheets import SheetsSync
    import os

    spreadsheet_id = os.environ["CLIENTDESK_SHEET_ID"]
    sheets = SheetsSync(spreadsheet_id)
    alert_label = "⚠️ 期限アラート"
    sheets.ensure_sheet(alert_label)

    expiring = store.get_expiring(client_id, 90)
    today = date.today()

    headers = ["期限まで", "カテゴリ", "名称", "期限日", "ステータス", "更新日"]
    rows = [headers]

    for r in expiring:
        dl_str = r.get("primary_deadline", "")
        if not dl_str:
            continue
        try:
            dl = date.fromisoformat(str(dl_str))
            days_left = (dl - today).days
        except ValueError:
            continue

        schema = CATEGORY_REGISTRY.get(r["category"])
        cat_label = schema.label if schema else r["category"]
        rows.append([
            f"{days_left}日",
            cat_label,
            r.get("record_key", ""),
            dl_str,
            r.get("status", ""),
            (r.get("updated_at") or "")[:10],
        ])

    from googleapiclient.discovery import build
    from google_auth import get_credentials
    svc = build("sheets", "v4", credentials=get_credentials())
    svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{alert_label}'!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()
    logger.info(f"Alert sheet: {len(rows) - 1} items")
