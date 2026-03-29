#!/usr/bin/env python3
"""
ClientDesk CLI

使い方:
  python main.py <client_id> entry <category>       # 手動エントリー
  python main.py <client_id> show [category]        # レコード表示
  python main.py <client_id> show --expiring 90     # 期限90日以内
  python main.py <client_id> summary                # サマリー
  python main.py <client_id> sync                   # ダッシュボード更新
  python main.py <client_id> import-dd              # DriveDesk取込
"""
import logging
import os
import sys

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

sys.path.insert(0, os.path.dirname(__file__))


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    client_id = args[0]
    command   = args[1]

    from config import load_config
    from store import get_store

    config = load_config(client_id)
    store  = get_store(config)

    if command == "entry":
        if len(args) < 3:
            from categories import CATEGORY_REGISTRY
            print("カテゴリを指定してください:")
            for cid, s in CATEGORY_REGISTRY.items():
                print(f"  {cid:<20} {s.label}")
            sys.exit(1)
        from cli.entry import run as entry_run
        entry_run(client_id, args[2], store)

    elif command == "show":
        category, expiring = None, None
        i = 2
        while i < len(args):
            if args[i] == "--expiring" and i + 1 < len(args):
                expiring = int(args[i + 1]); i += 2
            elif not args[i].startswith("--"):
                category = args[i]; i += 1
            else:
                i += 1
        from cli.query import show_records
        show_records(client_id, store, category, expiring)

    elif command == "summary":
        from cli.query import show_summary
        show_summary(client_id, store)

    elif command == "sync":
        from sync.sheets_sync import sync_dashboard
        sync_dashboard(client_id, store)
        print("✅ ダッシュボード更新完了")

    elif command == "import-dd":
        from ingest.drivedesk import poll
        dd_spreadsheet_id = config.get("drivedesk", {}).get("spreadsheet_id", "")
        if not dd_spreadsheet_id:
            print("❌ drivedesk.spreadsheet_id が設定されていません")
            sys.exit(1)
        count = poll(client_id, dd_spreadsheet_id, store)
        print(f"✅ DriveDesk取込完了: {count}件")

    else:
        print(f"❌ 不明なコマンド: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
