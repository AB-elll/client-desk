"""表示CLI: clientdesk show <category> [--expiring N]"""
from categories import CATEGORY_REGISTRY


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
    print(f"{'ID':<8} {'カテゴリ':<12} {'名称':<22} {'期限':<12} {'状態':<8} {'更新日':<12}")
    print("-" * 78)
    for r in records:
        schema = CATEGORY_REGISTRY.get(r["category"])
        cat_label = schema.label if schema else r["category"]
        print(
            f"{str(r.get('id','')):<8} {_fmt(cat_label, 12)} {_fmt(r.get('record_key',''), 22)}"
            f" {(r.get('primary_deadline') or '-'):<12} {r.get('status',''):<8}"
            f" {(r.get('updated_at') or '')[:10]}"
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
