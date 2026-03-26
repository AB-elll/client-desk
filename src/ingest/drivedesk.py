"""DriveDesk の drivedesk.db をポーリングしてClientDeskに取込"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from categories import CATEGORY_REGISTRY
from db import get_sync_state, set_sync_state, upsert_record

logger = logging.getLogger(__name__)

# DriveDesk subcategory → ClientDesk category マッピング
DRIVEDESK_MAP = {
    "employment_contract": "employment",
    "contract":            "contracts",
    "lease_agreement":     "contracts",
    "service_contract":    "contracts",
    "license":             "licenses",
    "permit":              "licenses",
    "insurance_policy":    "insurance",
    "tax_return":          "tax_docs",
    "tax_notice":          "tax_docs",
    "qualification":       "qualifications",
    "inspection_record":   "inspections",
}


def poll(client_id: str, drivedesk_db_path: str):
    """DriveDesk DBの差分をClientDeskに取込む。処理件数を返す。"""
    db_path = Path(drivedesk_db_path)
    if not db_path.exists():
        logger.warning(f"DriveDesk DB not found: {db_path}")
        return 0

    last_checked = get_sync_state("drivedesk_last_checked") or "1970-01-01T00:00:00"

    dd_conn = sqlite3.connect(db_path)
    dd_conn.row_factory = sqlite3.Row
    rows = dd_conn.execute(
        """SELECT file_id, file_name, primary_date, dates, category,
                  subcategory, confidence, status, updated_at
           FROM files
           WHERE status = 'processed'
             AND updated_at > ?
           ORDER BY updated_at ASC""",
        (last_checked,),
    ).fetchall()
    dd_conn.close()

    if not rows:
        return 0

    imported = 0
    latest_updated_at = last_checked

    for row in rows:
        cd_category = DRIVEDESK_MAP.get(row["subcategory"])
        if not cd_category:
            logger.debug(f"Skipping subcategory: {row['subcategory']}")
            continue

        schema = CATEGORY_REGISTRY.get(cd_category)
        if not schema:
            continue

        dates = json.loads(row["dates"] or "{}") if row["dates"] else {}
        fields = {
            "source_file": row["file_name"],
            "primary_date": row["primary_date"] or "",
            **{k: v for k, v in dates.items()},
        }

        # primary_deadline の決定
        primary_deadline = None
        secondary_deadline = None
        for fd in schema.fields:
            val = fields.get(fd.name) or (row["primary_date"] if fd.is_primary_deadline else None)
            if val and fd.is_primary_deadline and not primary_deadline:
                primary_deadline = val
            if val and fd.is_secondary_deadline and not secondary_deadline:
                secondary_deadline = val

        record_key = row["file_name"]

        upsert_record(
            client_id=client_id,
            category=cd_category,
            record_key=record_key,
            fields=fields,
            primary_deadline=primary_deadline,
            secondary_deadline=secondary_deadline,
            source="drivedesk",
            drive_file_id=row["file_id"],
            created_by=f"drivedesk:{row['file_id']}",
        )
        imported += 1
        if row["updated_at"] > latest_updated_at:
            latest_updated_at = row["updated_at"]

    set_sync_state("drivedesk_last_checked", latest_updated_at)
    logger.info(f"DriveDesk import: {imported} records imported")
    return imported
