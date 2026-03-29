"""全20カテゴリのスキーマ定義"""
from .base import CategorySchema, FieldDef


class ContractsSchema(CategorySchema):
    category_id = "contracts"
    label = "契約"
    source_type = "auto"
    fields = [
        FieldDef("contract_name", "契約名", required=True),
        FieldDef("counterpart", "相手方"),
        FieldDef("contract_type", "契約種別", hint="賃貸/リース/サービス/業務委託 等"),
        FieldDef("start_date", "開始日", type="date"),
        FieldDef("end_date", "終了日", type="date", is_primary_deadline=True),
        FieldDef("renewal_date", "更新日", type="date"),
        FieldDef("notice_deadline", "解約予告期限", type="date", is_secondary_deadline=True),
        FieldDef("monthly_fee", "月額（円）", type="int"),
        FieldDef("auto_renewal", "自動更新", type="bool"),
        FieldDef("storage_location", "保管場所"),
    ]


class EmploymentSchema(CategorySchema):
    category_id = "employment"
    label = "雇用契約"
    source_type = "auto"
    fields = [
        FieldDef("employee_name", "従業員名", required=True),
        FieldDef("employment_type", "雇用形態", hint="正社員/パート/アルバイト/契約社員"),
        FieldDef("start_date", "雇用開始日", type="date"),
        FieldDef("end_date", "契約終了日", type="date", is_primary_deadline=True),
        FieldDef("renewal_date", "更新日", type="date"),
        FieldDef("monthly_salary", "月給（円）", type="int"),
        FieldDef("hourly_wage", "時給（円）", type="int"),
    ]


class LicensesSchema(CategorySchema):
    category_id = "licenses"
    label = "許認可証"
    source_type = "auto"
    fields = [
        FieldDef("license_name", "許認可名", required=True, hint="薬局開設許可/保険薬局指定 等"),
        FieldDef("authority", "管轄機関"),
        FieldDef("license_number", "許認可番号"),
        FieldDef("issued_date", "交付日", type="date"),
        FieldDef("expiry_date", "有効期限", type="date", is_primary_deadline=True),
        FieldDef("renewal_deadline", "更新手続き期限", type="date", is_secondary_deadline=True),
        FieldDef("conditions", "条件・付帯事項"),
    ]


class InsuranceSchema(CategorySchema):
    category_id = "insurance"
    label = "保険証券"
    source_type = "auto"
    fields = [
        FieldDef("policy_name", "保険名", required=True),
        FieldDef("insurer", "保険会社"),
        FieldDef("policy_number", "証券番号"),
        FieldDef("insurance_type", "保険種別", hint="火災/賠償/労災上乗せ/団体医療 等"),
        FieldDef("coverage_summary", "補償内容（要約）"),
        FieldDef("start_date", "保険開始日", type="date"),
        FieldDef("end_date", "満期日", type="date", is_primary_deadline=True),
        FieldDef("annual_premium", "年間保険料（円）", type="int"),
    ]


class TaxDocsSchema(CategorySchema):
    category_id = "tax_docs"
    label = "税務書類"
    source_type = "auto"
    fields = [
        FieldDef("doc_type", "書類種別", required=True, hint="法人税申告/消費税申告/源泉納付 等"),
        FieldDef("fiscal_year", "事業年度"),
        FieldDef("due_date", "申告・納付期限", type="date", is_primary_deadline=True),
        FieldDef("filed_date", "申告日", type="date"),
        FieldDef("payment_status", "納付状況", hint="未払/納付済/分割納付"),
        FieldDef("amount", "金額（円）", type="int"),
    ]


class QualificationsSchema(CategorySchema):
    category_id = "qualifications"
    label = "従業員資格・免許"
    source_type = "auto"
    fields = [
        FieldDef("employee_name", "従業員名", required=True),
        FieldDef("qualification_name", "資格・免許名", required=True),
        FieldDef("registration_number", "登録番号"),
        FieldDef("issued_date", "取得日", type="date"),
        FieldDef("expiry_date", "有効期限", type="date", is_primary_deadline=True),
        FieldDef("renewal_deadline", "更新手続き期限", type="date", is_secondary_deadline=True),
        FieldDef("issuing_authority", "交付機関"),
    ]


class InspectionsSchema(CategorySchema):
    category_id = "inspections"
    label = "行政監査・指導記録"
    source_type = "auto"
    fields = [
        FieldDef("authority", "監査機関", required=True),
        FieldDef("inspection_date", "実施日", type="date"),
        FieldDef("inspection_type", "監査種別", hint="定期/抜き打ち/通報"),
        FieldDef("findings", "指摘事項"),
        FieldDef("response_status", "対応状況", hint="対応済/対応中/未対応"),
        FieldDef("response_deadline", "対応期限", type="date", is_primary_deadline=True),
    ]


class AssetsSchema(CategorySchema):
    category_id = "assets"
    label = "固定資産"
    source_type = "semi_auto"
    fields = [
        FieldDef("asset_name", "資産名", required=True),
        FieldDef("asset_category", "区分", hint="建物/機械/車両/備品 等"),
        FieldDef("purchase_date", "取得日", type="date"),
        FieldDef("purchase_price", "取得価額（円）", type="int"),
        FieldDef("useful_life_years", "耐用年数", type="int"),
        FieldDef("depreciation_method", "償却方法", hint="定額/定率"),
        FieldDef("is_lease", "リース", type="bool"),
        FieldDef("disposal_date", "廃棄・売却日", type="date"),
    ]


class LoanablesSchema(CategorySchema):
    category_id = "loanables"
    label = "貸与物"
    source_type = "semi_auto"
    fields = [
        FieldDef("item_name", "品目", required=True),
        FieldDef("employee_name", "貸与先（従業員）", required=True),
        FieldDef("loan_date", "貸与日", type="date"),
        FieldDef("expected_return_date", "返却予定日", type="date", is_primary_deadline=True),
        FieldDef("actual_return_date", "返却日", type="date"),
        FieldDef("return_status", "返却状況", hint="貸与中/返却済/紛失"),
        FieldDef("serial_number", "シリアル/管理番号"),
    ]


class SaasSchema(CategorySchema):
    category_id = "saas"
    label = "IT・SaaS"
    source_type = "semi_auto"
    fields = [
        FieldDef("service_name", "サービス名", required=True),
        FieldDef("contractor", "契約者"),
        FieldDef("plan", "プラン"),
        FieldDef("monthly_fee", "月額（円）", type="int"),
        FieldDef("renewal_date", "更新日", type="date", is_primary_deadline=True),
        FieldDef("account_count", "アカウント数", type="int"),
        FieldDef("account_status", "アカウント状況", hint="正常/停止/解約"),
        FieldDef("login_url", "ログインURL"),
        FieldDef("admin_email", "管理者メール"),
    ]


class SubsidiesSchema(CategorySchema):
    category_id = "subsidies"
    label = "補助金・助成金"
    source_type = "semi_auto"
    fields = [
        FieldDef("subsidy_name", "補助金・助成金名", required=True),
        FieldDef("grantor", "交付機関"),
        FieldDef("received_amount", "受給額（円）", type="int"),
        FieldDef("report_deadline", "報告期限", type="date", is_primary_deadline=True),
        FieldDef("conditions", "交付条件"),
        FieldDef("repayment_risk", "返還リスク", hint="なし/低/中/高"),
        FieldDef("expiry_date", "補助金有効期限", type="date"),
    ]


class PharmaceuticalsSchema(CategorySchema):
    category_id = "pharmaceuticals"
    label = "医薬品・在庫管理"
    source_type = "semi_auto"
    fields = [
        FieldDef("drug_name", "薬品名", required=True),
        FieldDef("drug_type", "区分", hint="麻薬/向精神薬/一般"),
        FieldDef("lot_number", "ロット番号"),
        FieldDef("expiry_date", "使用期限", type="date", is_primary_deadline=True),
        FieldDef("quantity", "数量", type="int"),
        FieldDef("disposal_date", "廃棄日", type="date"),
        FieldDef("disposal_record", "廃棄記録番号"),
        FieldDef("storage_location", "保管場所"),
    ]


class IpSchema(CategorySchema):
    category_id = "ip"
    label = "知的財産"
    source_type = "semi_auto"
    fields = [
        FieldDef("ip_name", "名称", required=True),
        FieldDef("ip_type", "種別", hint="商標/ドメイン/特許/著作権"),
        FieldDef("registration_number", "登録番号"),
        FieldDef("expiry_date", "有効期限", type="date", is_primary_deadline=True),
        FieldDef("renewal_deadline", "更新期限", type="date", is_secondary_deadline=True),
        FieldDef("owner", "権利帰属"),
        FieldDef("registrar", "登録機関"),
    ]


class ShareholdersSchema(CategorySchema):
    category_id = "shareholders"
    label = "出資・社員構成"
    source_type = "manual"
    fields = [
        FieldDef("member_name", "社員名", required=True),
        FieldDef("investment_amount", "出資額（円）", type="int"),
        FieldDef("investment_ratio", "出資比率（%）", type="float"),
        FieldDef("has_executive_rights", "業務執行権限", type="bool"),
        FieldDef("address", "住所"),
        FieldDef("notes", "備考"),
    ]


class LegalRisksSchema(CategorySchema):
    category_id = "legal_risks"
    label = "訴訟・クレームリスク"
    source_type = "manual"
    fields = [
        FieldDef("title", "件名", required=True),
        FieldDef("risk_type", "種別", hint="訴訟/クレーム/行政処分リスク"),
        FieldDef("description", "内容"),
        FieldDef("status", "状況", hint="係争中/和解/解決済"),
        FieldDef("potential_liability", "潜在債務額（円）", type="int"),
        FieldDef("resolution_deadline", "解決期限", type="date", is_primary_deadline=True),
        FieldDef("lawyer", "担当弁護士"),
    ]


class SealsSchema(CategorySchema):
    category_id = "seals"
    label = "印章・署名権限"
    source_type = "manual"
    fields = [
        FieldDef("seal_name", "印章名", required=True, hint="代表印/銀行印/角印"),
        FieldDef("storage_location", "保管場所"),
        FieldDef("custodian", "管理者"),
        FieldDef("authorized_users", "使用権限者"),
        FieldDef("registration_status", "登録状況", hint="法務局登録済/未登録"),
    ]


class BankingSchema(CategorySchema):
    category_id = "banking"
    label = "銀行・財務"
    source_type = "manual"
    fields = [
        FieldDef("bank_name", "銀行名", required=True),
        FieldDef("branch", "支店名"),
        FieldDef("account_type", "口座種別", hint="普通/当座"),
        FieldDef("account_number", "口座番号"),
        FieldDef("loan_amount", "借入残高（円）", type="int"),
        FieldDef("repayment_schedule", "返済スケジュール"),
        FieldDef("maturity_date", "返済期限", type="date", is_primary_deadline=True),
        FieldDef("interest_rate", "金利（%）", type="float"),
    ]


class BcpSchema(CategorySchema):
    category_id = "bcp"
    label = "緊急連絡・BCP"
    source_type = "manual"
    fields = [
        FieldDef("role", "役割", required=True, hint="代表/経理担当/薬剤師責任者 等"),
        FieldDef("name", "氏名", required=True),
        FieldDef("phone", "電話番号"),
        FieldDef("email", "メール"),
        FieldDef("backup_name", "代替者名"),
        FieldDef("backup_phone", "代替者電話"),
        FieldDef("notes", "備考"),
    ]


class PartnersSchema(CategorySchema):
    category_id = "partners"
    label = "取引先"
    source_type = "manual"
    fields = [
        FieldDef("company_name", "会社名", required=True),
        FieldDef("partner_type", "区分", hint="仕入先/販売先/外注先"),
        FieldDef("credit_limit", "与信枠（円）", type="int"),
        FieldDef("payment_terms", "支払条件", hint="月末締め翌月払 等"),
        FieldDef("contact_name", "担当者名"),
        FieldDef("contact_phone", "担当者電話"),
        FieldDef("contact_email", "担当者メール"),
        FieldDef("contract_renewal_date", "契約更新日", type="date", is_primary_deadline=True),
    ]


class PrivacySchema(CategorySchema):
    category_id = "privacy"
    label = "個人情報管理"
    source_type = "manual"
    fields = [
        FieldDef("policy_version", "規程バージョン"),
        FieldDef("manager_name", "管理責任者"),
        FieldDef("last_review_date", "最終見直し日", type="date"),
        FieldDef("next_review_date", "次回見直し予定", type="date", is_primary_deadline=True),
        FieldDef("data_items", "取扱個人情報項目"),
        FieldDef("incident_history", "インシデント履歴"),
        FieldDef("third_party_provision", "第三者提供", hint="あり/なし"),
    ]


class EmailAccountsSchema(CategorySchema):
    category_id = "email_accounts"
    label = "メールアカウント"
    source_type = "manual"
    fields = [
        FieldDef("email_address", "メールアドレス", required=True),
        FieldDef("purpose", "用途", hint="代表窓口/受付/店舗連絡/システム管理/個人 等"),
        FieldDef("owner", "管理者/利用者"),
        FieldDef("linked_service", "関連サービス", hint="Gmail/Outlook/独自ドメイン/Google Workspace 等"),
        FieldDef("renewal_date", "更新・確認予定日", type="date", is_primary_deadline=True),
        FieldDef("notes", "備考"),
    ]


# ── 一元レジストリ ─────────────────────────────────────────────
CATEGORY_REGISTRY: dict[str, CategorySchema] = {
    s.category_id: s for s in [
        ContractsSchema(),
        EmploymentSchema(),
        LicensesSchema(),
        InsuranceSchema(),
        TaxDocsSchema(),
        QualificationsSchema(),
        InspectionsSchema(),
        AssetsSchema(),
        LoanablesSchema(),
        SaasSchema(),
        SubsidiesSchema(),
        PharmaceuticalsSchema(),
        IpSchema(),
        ShareholdersSchema(),
        LegalRisksSchema(),
        SealsSchema(),
        BankingSchema(),
        BcpSchema(),
        PartnersSchema(),
        PrivacySchema(),
        EmailAccountsSchema(),
    ]
}
