import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "clientdesk.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS records (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id           TEXT NOT NULL,
                category            TEXT NOT NULL,
                record_key          TEXT,
                source              TEXT DEFAULT 'manual',
                drive_file_id       TEXT,
                primary_deadline    DATE,
                secondary_deadline  DATE,
                status              TEXT DEFAULT 'active',
                alert_sent_at       DATETIME,
                fields              TEXT NOT NULL DEFAULT '{}',
                created_at          DATETIME NOT NULL,
                updated_at          DATETIME NOT NULL,
                created_by          TEXT DEFAULT 'manual',
                notes               TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_records_client_category
                ON records (client_id, category);
            CREATE INDEX IF NOT EXISTS idx_records_deadline
                ON records (primary_deadline)
                WHERE primary_deadline IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_records_drive_file_id
                ON records (drive_file_id)
                WHERE drive_file_id IS NOT NULL;

            CREATE TABLE IF NOT EXISTS alert_rules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id   TEXT NOT NULL,
                category    TEXT NOT NULL,
                days_before INTEGER NOT NULL,
                alert_type  TEXT DEFAULT 'deadline'
            );

            CREATE TABLE IF NOT EXISTS sync_state (
                key     TEXT PRIMARY KEY,
                value   TEXT
            );
        """)


def upsert_record(client_id: str, category: str, record_key: str,
                  fields: dict, **kwargs) -> int:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM records WHERE client_id=? AND category=? AND record_key=?",
            (client_id, category, record_key),
        ).fetchone()

        fields_json = json.dumps(fields, ensure_ascii=False)

        if existing:
            sets = {"fields": fields_json, "updated_at": now}
            sets.update({k: v for k, v in kwargs.items() if v is not None})
            sql_sets = ", ".join(f"{k}=?" for k in sets)
            conn.execute(
                f"UPDATE records SET {sql_sets} WHERE id=?",
                [*sets.values(), existing["id"]],
            )
            return existing["id"]
        else:
            data = {
                "client_id": client_id,
                "category": category,
                "record_key": record_key,
                "fields": fields_json,
                "created_at": now,
                "updated_at": now,
            }
            data.update({k: v for k, v in kwargs.items() if v is not None})
            cols = ", ".join(data.keys())
            phs = ", ".join("?" * len(data))
            cur = conn.execute(
                f"INSERT INTO records ({cols}) VALUES ({phs})",
                list(data.values()),
            )
            return cur.lastrowid


def get_records(client_id: str, category: str = None,
                status: str = "active") -> list[dict]:
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM records WHERE client_id=? AND category=? AND status=?"
                " ORDER BY primary_deadline ASC NULLS LAST",
                (client_id, category, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM records WHERE client_id=? AND status=?"
                " ORDER BY category, primary_deadline ASC NULLS LAST",
                (client_id, status),
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("fields"):
            d["fields"] = json.loads(d["fields"])
        result.append(d)
    return result


def get_expiring_records(client_id: str, within_days: int) -> list[dict]:
    """primary_deadline が within_days 日以内のアクティブなレコードを返す"""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM records
            WHERE client_id=?
              AND status='active'
              AND primary_deadline IS NOT NULL
              AND date(primary_deadline) <= date('now', ? || ' days')
              AND date(primary_deadline) >= date('now')
            ORDER BY primary_deadline ASC
            """,
            (client_id, f"+{within_days}"),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("fields"):
            d["fields"] = json.loads(d["fields"])
        result.append(d)
    return result


def get_sync_state(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key=?", (key,)
        ).fetchone()
    return row["value"] if row else None


def set_sync_state(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
            (key, value),
        )
