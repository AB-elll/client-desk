"""DriveDesk の drivedesk.db をポーリングしてClientDeskに取込"""
import json
import logging
import sqlite3
from pathlib import Path

from categories import CATEGORY_REGISTRY

logger = logging.getLogger(__name__)

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
    "registration":        "licenses",
}


def poll(client_id: str, drivedesk_db_path: str, store) -> int:
    db_path = Path(drivedesk_db_path)
    if not db_path.exists():
        logger.warning(f"DriveDesk DB not found: {db_path}")
        return 0

    last_checked = store.get_sync_state("drivedesk_last_checked") or "1970-01-01T00:00:00"

    dd_conn = sqlite3.connect(db_path)
    dd_conn.row_factory = sqlite3.Row
    rows = dd_conn.execute(
        """SELECT file_id, file_name, primary_date, dates, category,
                  subcategory, confidence, status, updated_at
           FROM files
           WHERE status = 'processed' AND updated_at > ?
           ORDER BY updated_at ASC""",
        (last_checked,),
    ).fetchall()
    dd_conn.close()

    if not rows:
        return 0

    imported = 0
    latest = last_checked

    for row in rows:
        cd_category = DRIVEDESK_MAP.get(row["subcategory"])
        if not cd_category:
            continue

        schema = CATEGORY_REGISTRY.get(cd_category)
        if not schema:
            continue

        dates = json.loads(row["dates"] or "{}") if row["dates"] else {}
        fields = {"source_file": row["file_name"],
                  "primary_date": row["primary_date"] or "", **dates}

        primary_deadline = None
        for fd in schema.fields:
            val = fields.get(fd.name) or (row["primary_date"] if fd.is_primary_deadline else None)
            if val and fd.is_primary_deadline and not primary_deadline:
                primary_deadline = val

        store.upsert(
            client_id=client_id,
            category=cd_category,
            record_key=row["file_name"],
            fields=fields,
            primary_deadline=primary_deadline,
            source="drivedesk",
            drive_file_id=row["file_id"],
        )
        imported += 1
        if row["updated_at"] > latest:
            latest = row["updated_at"]

    store.set_sync_state("drivedesk_last_checked", latest)
    logger.info(f"DriveDesk import: {imported} records")
    return imported
