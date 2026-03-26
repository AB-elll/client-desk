"""SupabaseStore — Supabase (PostgreSQL) 実装

【移行手順】
1. https://supabase.com でプロジェクト作成（無料）
2. pip install supabase
3. Supabase管理画面 > SQL Editor で以下を実行:

    CREATE TABLE records (
        id               TEXT PRIMARY KEY,
        client_id        TEXT NOT NULL,
        category         TEXT NOT NULL,
        record_key       TEXT,
        status           TEXT DEFAULT 'active',
        primary_deadline DATE,
        secondary_deadline DATE,
        created_at       TIMESTAMPTZ DEFAULT NOW(),
        updated_at       TIMESTAMPTZ DEFAULT NOW(),
        source           TEXT DEFAULT 'manual',
        drive_file_id    TEXT,
        notes            TEXT,
        fields           JSONB NOT NULL DEFAULT '{}'
    );
    CREATE INDEX ON records (client_id, category);
    CREATE INDEX ON records (primary_deadline) WHERE primary_deadline IS NOT NULL;

    CREATE TABLE sync_state (
        key   TEXT PRIMARY KEY,
        value TEXT
    );

4. .env に追記:
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_KEY=your-anon-key

5. clientdesk.config.yml を変更:
    store:
      type: supabase   # ← sheets から変更するだけ
"""
import json
import logging
import os
import uuid
from datetime import date, datetime, timedelta

from .base import AbstractStore

logger = logging.getLogger(__name__)


class SupabaseStore(AbstractStore):

    def __init__(self):
        try:
            from supabase import create_client
        except ImportError:
            raise ImportError(
                "supabase パッケージが必要です: pip install supabase"
            )
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        self._client = create_client(url, key)

    def upsert(self, client_id: str, category: str, record_key: str,
               fields: dict, **kwargs) -> str:
        now = datetime.utcnow().isoformat()
        record_id = str(uuid.uuid4())[:8]

        data = {
            "id":                 record_id,
            "client_id":          client_id,
            "category":           category,
            "record_key":         record_key,
            "fields":             fields,
            "status":             kwargs.get("status", "active"),
            "primary_deadline":   kwargs.get("primary_deadline"),
            "secondary_deadline": kwargs.get("secondary_deadline"),
            "source":             kwargs.get("source", "manual"),
            "drive_file_id":      kwargs.get("drive_file_id"),
            "notes":              kwargs.get("notes"),
            "updated_at":         now,
        }

        # upsert（record_key が一致すれば更新、なければ挿入）
        res = (
            self._client.table("records")
            .upsert(data, on_conflict="client_id,category,record_key")
            .execute()
        )
        return res.data[0]["id"] if res.data else record_id

    def get_all(self, client_id: str, category: str = None,
                status: str = "active") -> list[dict]:
        query = self._client.table("records").select("*").eq("client_id", client_id)
        if category:
            query = query.eq("category", category)
        if status != "all":
            query = query.eq("status", status)
        res = query.order("primary_deadline", desc=False, nullsfirst=False).execute()
        return res.data or []

    def get_expiring(self, client_id: str, within_days: int) -> list[dict]:
        today = date.today().isoformat()
        limit = (date.today() + timedelta(days=within_days)).isoformat()
        res = (
            self._client.table("records")
            .select("*")
            .eq("client_id", client_id)
            .eq("status", "active")
            .gte("primary_deadline", today)
            .lte("primary_deadline", limit)
            .order("primary_deadline")
            .execute()
        )
        return res.data or []

    def get_sync_state(self, key: str) -> str | None:
        res = (
            self._client.table("sync_state")
            .select("value")
            .eq("key", key)
            .execute()
        )
        return res.data[0]["value"] if res.data else None

    def set_sync_state(self, key: str, value: str):
        self._client.table("sync_state").upsert(
            {"key": key, "value": value}, on_conflict="key"
        ).execute()
