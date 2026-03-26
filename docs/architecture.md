# ClientDesk アーキテクチャ設計書

**バージョン**: 1.0.0
**作成日**: 2026-03-26
**ステータス**: 確定

---

## 1. システム全体像

```
[Google Drive]
      ↓ ファイル流入
[DriveDesk]  ─── processed レコード ──→  [ClientDesk]
  書類処理パイプライン                      経営情報台帳
      ↓                                        ↓
  freee / JDL                         [Google Sheets]
  会計ソフト登録                         ダッシュボード
                                              ↓
                                        期限アラート
                                        DDエクスポート
```

DriveDesk が「書類処理パイプライン」、ClientDesk が「データルーム」として機能する。
両者は独立したプロセスで、ClientDesk は DriveDesk の SQLite DB を read-only でポーリングする。

---

## 2. ディレクトリ構造

```
client-desk/
├── src/
│   ├── main.py                  # CLIエントリーポイント
│   ├── config.py                # 設定読み込み（YAML + 環境変数展開）
│   ├── db.py                    # SQLite接続・init_db・共通CRUD
│   ├── google_auth.py           # Google OAuth（DriveDesk共通実装）
│   │
│   ├── categories/
│   │   ├── __init__.py          # CATEGORY_REGISTRY（20カテゴリ登録表）
│   │   ├── base.py              # CategorySchema / FieldDef 基底クラス
│   │   └── definitions.py       # 全20カテゴリのスキーマ定義
│   │
│   ├── cli/
│   │   ├── entry.py             # 手動エントリー（対話入力）
│   │   └── query.py             # レコード表示・サマリー
│   │
│   ├── ingest/
│   │   └── drivedesk.py         # DriveDesk DBポーリング取込
│   │
│   ├── sync/
│   │   └── sheets_sync.py       # Google Sheetsダッシュボード同期
│   │
│   └── alert/                   # 期限アラート（将来実装）
│
├── clients/
│   └── karas/
│       ├── clientdesk.config.yml
│       └── .env
├── docs/
│   ├── requirements.md
│   └── architecture.md
├── requirements.txt
└── clientdesk.db                # SQLite本体（gitignore）
```

---

## 3. データベース設計

### 設計方針

**単一テーブル + JSON フィールド方式**を採用。

20カテゴリを別テーブルに分けると JOIN の複雑化とマイグレーションコストが生じる。
カテゴリ固有フィールドを `fields` JSON に格納し、期限系フィールドのみカラムとして引き出す。

### `records` テーブル（主テーブル）

```sql
CREATE TABLE records (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id           TEXT NOT NULL,          -- "karas"
    category            TEXT NOT NULL,          -- "contracts" / "licenses" / ...
    record_key          TEXT,                   -- 人間が識別する自然キー
    source              TEXT DEFAULT 'manual',  -- "manual" / "drivedesk"
    drive_file_id       TEXT,                   -- DriveDesk経由時のDriveファイルID

    -- 期限系（アラートSQLクエリ用に非正規化）
    primary_deadline    DATE,
    secondary_deadline  DATE,

    status              TEXT DEFAULT 'active',  -- active / expired / cancelled / archived
    alert_sent_at       DATETIME,

    -- カテゴリ固有フィールド（JSON）
    fields              TEXT NOT NULL DEFAULT '{}',

    created_at          DATETIME NOT NULL,
    updated_at          DATETIME NOT NULL,
    created_by          TEXT DEFAULT 'manual',
    notes               TEXT
);
```

### インデックス

```sql
CREATE INDEX idx_records_client_category ON records (client_id, category);
CREATE INDEX idx_records_deadline        ON records (primary_deadline);
CREATE INDEX idx_records_drive_file_id   ON records (drive_file_id);
```

### `fields` JSON の例（contracts カテゴリ）

```json
{
  "contract_name": "事務所賃貸借契約",
  "counterpart": "株式会社○○不動産",
  "start_date": "2023-04-01",
  "end_date": "2025-03-31",
  "renewal_date": "2025-01-31",
  "notice_deadline": "2024-10-31",
  "monthly_fee": 120000,
  "auto_renewal": true
}
```

---

## 4. カテゴリスキーマ設計

### `CategorySchema` クラス（`categories/base.py`）

```python
class FieldDef:
    name: str                       # フィールドキー（英語）
    label: str                      # 表示ラベル（日本語）
    type: str                       # str / date / int / float / bool
    required: bool
    is_primary_deadline: bool       # primary_deadline カラムに昇格
    is_secondary_deadline: bool

class CategorySchema:
    category_id: str
    label: str
    source_type: str                # auto / semi_auto / manual

    def get_sheets_headers()        # Sheets列ヘッダー生成
    def extract_deadlines()         # primary/secondary_deadline 抽出
    def to_record_row()             # Sheets行データ生成
```

### 20カテゴリ一覧

| # | category_id | ラベル | source_type | primary_deadline |
|---|---|---|---|---|
| 1 | contracts | 契約 | auto | end_date / renewal_date |
| 2 | employment | 雇用契約 | auto | end_date |
| 3 | licenses | 許認可証 | auto | expiry_date |
| 4 | insurance | 保険証券 | auto | end_date |
| 5 | tax_docs | 税務書類 | auto | due_date |
| 6 | qualifications | 従業員資格・免許 | auto | expiry_date |
| 7 | inspections | 行政監査・指導記録 | auto | response_deadline |
| 8 | assets | 固定資産 | semi_auto | — |
| 9 | loanables | 貸与物 | semi_auto | expected_return_date |
| 10 | saas | IT・SaaS | semi_auto | renewal_date |
| 11 | subsidies | 補助金・助成金 | semi_auto | report_deadline |
| 12 | pharmaceuticals | 医薬品・在庫管理 | semi_auto | expiry_date |
| 13 | ip | 知的財産 | semi_auto | expiry_date |
| 14 | shareholders | 出資・社員構成 | manual | — |
| 15 | legal_risks | 訴訟・クレームリスク | manual | resolution_deadline |
| 16 | seals | 印章・署名権限 | manual | — |
| 17 | banking | 銀行・財務 | manual | maturity_date |
| 18 | bcp | 緊急連絡・BCP | manual | — |
| 19 | partners | 取引先 | manual | contract_renewal_date |
| 20 | privacy | 個人情報管理 | manual | next_review_date |

---

## 5. DriveDesk 連携

### 方式：DB直接ポーリング（read-only）

DriveDesk の `drivedesk.db` を定期的に SELECT し、`status='processed'` かつ `updated_at > 前回チェック時刻` のレコードを取込む。

DriveDesk 側コードへの変更なし。疎結合を維持。

### subcategory マッピング

```python
DRIVEDESK_MAP = {
    "employment_contract": "employment",
    "contract":            "contracts",
    "lease_agreement":     "contracts",
    "service_contract":    "contracts",
    "license":             "licenses",
    "permit":              "licenses",
    "insurance_policy":    "insurance",
    "tax_return":          "tax_docs",
    "qualification":       "qualifications",
    "inspection_record":   "inspections",
}
```

マッピングにない subcategory はスキップ。

### 将来拡張

DriveDesk 側に `clientdesk` プロセッサープラグインを追加し、処理完了と同時に取込む方式に移行可能。インターフェースは同一。

---

## 6. CLI インターフェース

```bash
# 手動エントリー
python src/main.py karas entry <category>

# レコード表示
python src/main.py karas show [category]
python src/main.py karas show --expiring 90

# サマリー
python src/main.py karas summary

# Google Sheets同期
python src/main.py karas sync

# DriveDesk取込
python src/main.py karas import-dd
```

---

## 7. Google Sheets ダッシュボード

### シート構成

| シート名 | 内容 |
|---|---|
| 契約 | contracts テーブル全件 |
| 雇用契約 | employment テーブル全件 |
| ... | （カテゴリ別20シート） |
| ⚠️ 期限アラート | primary_deadline が近い全レコード |

### 同期方式

`batchUpdate` で全シートを一括上書き。`sync_state` テーブルに最終同期日時を記録。

---

## 8. 設定ファイル

```yaml
# clients/karas/clientdesk.config.yml
client:
  name: "合同会社Kara's"
  id: "karas"

drivedesk:
  db_path: "${DRIVEDESK_DB_PATH}"
  poll_interval_seconds: 300

sheets:
  spreadsheet_id: "${CLIENTDESK_SHEET_ID}"

alerts:
  default_thresholds_days: [90, 30, 7]
```

---

## 9. 将来の拡張

| 機能 | 概要 |
|---|---|
| Webダッシュボード | FastAPI + React による GUI管理画面 |
| Papermark連携 | カテゴリ指定URL発行・閲覧権限管理・M&A DDエクスポート |
| 複数クライアント対応 | `client_id` による横断サマリー |
| 自動アラート通知 | Telegram通知（DriveDesk Notifierと共通化） |
| Docling連携 | PDF抽出精度向上 |

---

## 10. 非機能要件

| 項目 | 実装 |
|---|---|
| 汎用性 | `clients/<id>/` で任意クライアントに対応 |
| セキュリティ | クレデンシャルは `.env` 管理・gitignore |
| 可観測性 | `sync_state` に最終同期日時記録 |
| OSS | MITライセンス |
