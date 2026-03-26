from .base import AbstractStore


def get_store(config: dict) -> AbstractStore:
    """config の store.type に応じたストアを返す"""
    import os
    store_type = config.get("store", {}).get("type", "sheets")

    if store_type == "sheets":
        from .sheets import SheetsStore
        spreadsheet_id = os.environ["CLIENTDESK_SHEET_ID"]
        return SheetsStore(spreadsheet_id)

    elif store_type == "supabase":
        from .supabase import SupabaseStore
        return SupabaseStore()

    else:
        raise ValueError(f"Unknown store type: {store_type}")
