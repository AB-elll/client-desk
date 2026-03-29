"""DriveDesk の _DriveDesk_Files シートをポーリングしてClientDeskに取込"""
import json
import logging

from googleapiclient.discovery import build

from categories import CATEGORY_REGISTRY
from google_auth import get_credentials

logger = logging.getLogger(__name__)

_FILES_SHEET = "_DriveDesk_Files"
_FILES_HEADERS = [
    "file_id", "file_name", "shared_at", "primary_date", "dates",
    "category", "subcategory", "confidence", "low_confidence",
    "status", "processor_refs", "error_message", "updated_at",
]

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


def poll(client_id: str, spreadsheet_id: str, store) -> int:
    svc = build("sheets", "v4", credentials=get_credentials())

    resp = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{_FILES_SHEET}!A1:Z",
    ).execute()
    raw_rows = resp.get("values", [])
    if len(raw_rows) <= 1:
        return 0

    rows = [
        dict(zip(_FILES_HEADERS, r + [""] * (len(_FILES_HEADERS) - len(r))))
        for r in raw_rows[1:]
    ]

    last_checked = store.get_sync_state("drivedesk_last_checked") or "1970-01-01T00:00:00"

    imported = 0
    latest = last_checked

    for row in rows:
        if row.get("status") != "processed":
            continue
        if row.get("updated_at", "") <= last_checked:
            continue

        cd_category = DRIVEDESK_MAP.get(row.get("subcategory", ""))
        if not cd_category:
            continue

        schema = CATEGORY_REGISTRY.get(cd_category)
        if not schema:
            continue

        dates_raw = row.get("dates") or "{}"
        try:
            dates = json.loads(dates_raw)
        except Exception:
            dates = {}

        fields = {
            "source_file": row.get("file_name", ""),
            "primary_date": row.get("primary_date", ""),
            **dates,
        }

        primary_deadline = None
        for fd in schema.fields:
            val = fields.get(fd.name) or (row.get("primary_date") if fd.is_primary_deadline else None)
            if val and fd.is_primary_deadline and not primary_deadline:
                primary_deadline = val

        store.upsert(
            client_id=client_id,
            category=cd_category,
            record_key=row.get("file_name", ""),
            fields=fields,
            primary_deadline=primary_deadline,
            source="drivedesk",
            drive_file_id=row.get("file_id", ""),
        )
        imported += 1
        if row.get("updated_at", "") > latest:
            latest = row["updated_at"]

    store.set_sync_state("drivedesk_last_checked", latest)
    logger.info(f"DriveDesk import: {imported} records")
    return imported
