"""手動エントリーCLI: clientdesk entry <category>"""
import sys
from datetime import datetime

sys.path.insert(0, __file__.rsplit("/", 2)[0])

from categories import CATEGORY_REGISTRY
from db import init_db, upsert_record


def prompt_field(fd):
    """フィールドを対話入力。Enterでスキップ（任意フィールドの場合）"""
    hint = f" [{fd.hint}]" if fd.hint else ""
    required_mark = " *" if fd.required else ""
    prompt = f"  {fd.label}{required_mark}{hint}: "
    while True:
        val = input(prompt).strip()
        if not val:
            if fd.required:
                print("    ※ 必須項目です")
                continue
            return None
        if fd.type == "date":
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                try:
                    # YYYY/MM/DD も受け付ける
                    d = datetime.strptime(val, "%Y/%m/%d")
                    val = d.strftime("%Y-%m-%d")
                except ValueError:
                    print("    ※ 日付は YYYY-MM-DD 形式で入力してください")
                    continue
        if fd.type == "int":
            try:
                val = int(val.replace(",", ""))
            except ValueError:
                print("    ※ 数値を入力してください")
                continue
        if fd.type == "float":
            try:
                val = float(val)
            except ValueError:
                print("    ※ 数値を入力してください")
                continue
        if fd.type == "bool":
            val = val.lower() in ("yes", "y", "true", "1", "はい")
        return val


def run(client_id: str, category_id: str):
    if category_id not in CATEGORY_REGISTRY:
        print(f"❌ カテゴリ '{category_id}' が存在しません。")
        print("利用可能:", ", ".join(CATEGORY_REGISTRY.keys()))
        return

    schema = CATEGORY_REGISTRY[category_id]
    init_db()

    print(f"\n📋 [{schema.label}] 新規エントリー")
    print("  (* 必須項目 / Enterでスキップ可)")
    print()

    fields = {}
    for fd in schema.fields:
        val = prompt_field(fd)
        if val is not None:
            fields[fd.name] = val

    notes = input("  メモ（任意）: ").strip() or None

    # record_key は最初の必須フィールドの値、なければ入力値から生成
    required_fields = [f for f in schema.fields if f.required]
    if required_fields:
        record_key = str(fields.get(required_fields[0].name, ""))
    else:
        record_key = str(fields.get(schema.fields[0].name, "")) if schema.fields else "entry"

    primary_deadline, secondary_deadline = schema.extract_deadlines(fields)

    record_id = upsert_record(
        client_id=client_id,
        category=category_id,
        record_key=record_key,
        fields=fields,
        primary_deadline=str(primary_deadline) if primary_deadline else None,
        secondary_deadline=str(secondary_deadline) if secondary_deadline else None,
        notes=notes,
        source="manual",
    )

    print(f"\n✅ 登録完了 (id={record_id})")
    if primary_deadline:
        print(f"   期限: {primary_deadline}")
