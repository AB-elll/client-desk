"""表示CLI: clientdesk show <category> [--expiring N]"""
import json as _json
from categories import CATEGORY_REGISTRY

# カテゴリごとに「補足」列に表示するフィールド
_KEY_FIELDS: dict[str, tuple] = {
    "email_accounts": ("email_address", "linked_service"),
    "saas":           ("admin_email", "plan"),
    "partners":       ("contact_email", "partner_type"),
    "qualifications": ("employee_name", "qualification_name"),
    "licenses":       ("license_name", "license_number"),
    "contracts":      ("counterpart", "contract_type"),
    "employment":     ("employee_name", "employment_type"),
    "banking":        ("bank_name", "account_number"),
}


def _fmt(val, width=20):
    s = str(val) if val is not None else "-"
    if len(s) > width:
        s = s[:width - 1] + "…"
    return s.ljust(width)


def show_records(client_id: str, store, category_id: str = None,
                 expiring_days: int = None, status: str = "active"):
    if expiring_days is not None:
        records = store.get_expiring(client_id, expiring_days)
        if category_id:
            records = [r for r in records if r["category"] == category_id]
        title = f"期限{expiring_days}日以内"
    else:
        records = store.get_all(client_id, category_id, status)
        schema = CATEGORY_REGISTRY.get(category_id) if category_id else None
        title = schema.label if schema else (category_id or "全カテゴリ")

    if not records:
        print(f"該当レコードなし ({title})")
        return

    print(f"\n📋 {title}  ({len(records)}件)\n")
    print(f"{'ID':<8} {'カテゴリ':<12} {'名称':<20} {'期限':<12} {'状態':<8} {'補足':<30}")
    print("-" * 92)
    for r in records:
        schema = CATEGORY_REGISTRY.get(r["category"])
        cat_label = schema.label if schema else r["category"]

        fields = r.get("fields") or {}
        if isinstance(fields, str):
            try:
                fields = _json.loads(fields)
            except Exception:
                fields = {}

        extra_keys = _KEY_FIELDS.get(r["category"], ())
        extra = "  ".join(str(fields[k]) for k in extra_keys if fields.get(k))

        print(
            f"{str(r.get('id','')):<8} {_fmt(cat_label, 12)} {_fmt(r.get('record_key',''), 20)}"
            f" {(r.get('primary_deadline') or '-'):<12} {r.get('status',''):<8}"
            f" {_fmt(extra, 30)}"
        )
    print()


def show_summary(client_id: str, store):
    all_records  = store.get_all(client_id, status="all")
    expiring_90  = store.get_expiring(client_id, 90)
    expiring_30  = store.get_expiring(client_id, 30)

    counts: dict[str, int] = {}
    for r in all_records:
        counts[r["category"]] = counts.get(r["category"], 0) + 1

    print(f"\n📊 ClientDesk サマリー  [{client_id}]\n")
    print(f"  総レコード数    : {len(all_records)}")
    print(f"  期限90日以内    : {len(expiring_90)} 件")
    print(f"  期限30日以内    : {len(expiring_30)} 件 ⚠️")
    print()
    print(f"  {'カテゴリ':<20} {'件数':>5}")
    print("  " + "-" * 27)
    for cat_id, schema in CATEGORY_REGISTRY.items():
        c = counts.get(cat_id, 0)
        if c > 0:
            print(f"  {schema.label:<20} {c:>5}")
    print()
