# -*- coding: utf-8 -*-
"""Sheet definitions for VPK master-data Excel templates.

Each data sheet has two header rows:
    row 0 = Thai labels (for the person filling the file)
    row 1 = technical English field names (stable for import)
Samples start at row 2.
"""

# Areas the user can download separately or together.
TEMPLATE_AREAS = [
    ("warehouse", "1. คลังสินค้า / Location"),
    ("product", "2. Product Master"),
    ("product_category", "3. Product Category"),
    ("uom", "4. UoM"),
    ("asset", "5. Fixed Asset / Profile"),
    ("analytic", "6. Analytic / แผนก / Project"),
    ("equipment", "7. Equipment ยกยอด (Maintenance ↔ Asset)"),
    ("vendor", "8. Vendor / ผู้จำหน่าย"),
    ("purchase_request", "9. Purchase Request (PR)"),
    ("purchase_order", "10. Purchase Order (PO)"),
    ("coa", "11. ผังบัญชี (Chart of Accounts)"),
    ("accounting_setup", "12. ตั้งค่าบัญชี (สมุดรายวัน / ภาษี / เงื่อนไขชำระ)"),
    ("work_acceptance", "13. ตรวจรับงาน (Work Acceptance)"),
    ("vendor_bill", "14. ใบแจ้งหนี้ผู้ขาย / ใบลดหนี้ (ระบบเจ้าหนี้)"),
    ("finance", "15. การจ่ายชำระ / Statement (ระบบการเงิน)"),
    ("journal_entry", "16. รายการบัญชีทั่วไป / ยกยอด (ระบบบัญชี)"),
    ("wht_cert", "17. หนังสือรับรองหัก ณ ที่จ่าย (WHT)"),
    ("checkbook", "18. สมุดเช็ค (Checkbook)"),
]

# sheet_name -> definition
SHEETS = {
    # -------------------------------------------------------------------------
    # 1. Warehouse / Location
    # -------------------------------------------------------------------------
    "Warehouse": {
        "area": "warehouse",
        "label": "คลังสินค้า",
        "headers": ["code", "name", "reception_steps", "delivery_steps", "active"],
        "widths": [10, 36, 16, 16, 10],
        "samples": [
            ["WH", "คลังกลาง", "one_step", "ship_only", 1],
            ["PHAR", "คลังยา", "two_steps", "pick_ship", 1],
        ],
        "note": (
            "code สูงสุด 5 ตัวอักษร (required) | "
            "reception_steps = one_step/two_steps/three_steps | "
            "delivery_steps = ship_only/pick_ship/pick_pack_ship | "
            "สร้างคลังแล้วระบบจะสร้าง location หลักให้อัตโนมัติ"
        ),
    },
    "Location": {
        "area": "warehouse",
        "label": "ตำแหน่งจัดเก็บ",
        "headers": [
            "name",
            "parent_path",
            "usage",
            "warehouse_code",
            "barcode",
            "active",
        ],
        "widths": [24, 40, 14, 14, 18, 10],
        "samples": [
            ["A01", "WH/Stock", "internal", "WH", "", 1],
            ["A01-01", "WH/Stock/A01", "internal", "WH", "", 1],
            ["Shelf-B", "PHAR/Stock", "internal", "PHAR", "", 1],
        ],
        "note": (
            "parent_path = path ของ location แม่ เช่น WH/Stock | "
            "usage = internal/view/supplier/customer/inventory/production/transit | "
            "warehouse_code อ้างอิงชีต Warehouse (สำหรับจัดกลุ่ม)"
        ),
    },
    # -------------------------------------------------------------------------
    # 2. Product
    # -------------------------------------------------------------------------
    "Product": {
        "area": "product",
        "label": "สินค้า",
        "headers": [
            "default_code",
            "name",
            "egp_purchase_name",
            "categ_path",
            "uom",
            "uom_po",
            "type",
            "is_storable",
            "tracking",
            "use_expiration_date",
            "expiration_time",
            "purchase_ok",
            "sale_ok",
            "purchase_method",
            "list_price",
            "standard_price",
            "barcode",
            "description",
        ],
        "widths": [
            14, 36, 36, 40, 12, 12, 10, 12, 10, 18, 14, 12, 10, 16, 12, 14, 16, 30,
        ],
        "samples": [
            [
                "3012815",
                "Syringe Dispos 10ml",
                "Syringe Disposable 10 ml",
                "All / กลุ่มพัสดุ / 2.เวชภัณฑ์มิใช่ยา",
                "หน่วย",
                "กล่อง-100",
                "consu",
                1,
                "lot",
                1,
                365,
                1,
                1,
                "receive",
                1.00,
                1.71,
                "",
                "",
            ],
            [
                "DEMO-001",
                "ตัวอย่างสินค้าทั่วไป",
                "ตัวอย่างสินค้าทั่วไป (e-GP)",
                "All / กลุ่มพัสดุ / 5.วัสดุทั่วไป",
                "หน่วย",
                "หน่วย",
                "consu",
                1,
                "none",
                0,
                "",
                1,
                1,
                "purchase",
                10,
                8,
                "",
                "ตัวอย่าง",
            ],
        ],
        "note": (
            "default_code = รหัสสินค้า (key) | egp_purchase_name = ชื่อสำหรับซื้อใน e-GP | categ_path = path หมวดหมู่เต็ม | "
            "type = consu/service | is_storable/tracking/purchase_ok/sale_ok/"
            "use_expiration_date = 1 หรือ 0 | tracking = none/lot/serial | "
            "purchase_method = receive หรือ purchase | "
            "นำเข้าได้ที่ Inventory > Import Product Master"
        ),
    },
    # -------------------------------------------------------------------------
    # 3. Product Category
    # -------------------------------------------------------------------------
    "ProductCategory": {
        "area": "product_category",
        "label": "หมวดหมู่สินค้า",
        "headers": ["name", "parent_path", "active"],
        "widths": [36, 50, 10],
        "samples": [
            ["กลุ่มพัสดุ", "All", 1],
            ["1.เวชภัณฑ์ ยา", "All / กลุ่มพัสดุ", 1],
            ["2.เวชภัณฑ์มิใช่ยา", "All / กลุ่มพัสดุ", 1],
            ["5.วัสดุทั่วไป", "All / กลุ่มพัสดุ", 1],
        ],
        "note": (
            "parent_path = path หมวดแม่ เช่น All หรือ All / กลุ่มพัสดุ | "
            "ถ้า parent_path ว่าง จะสร้างภายใต้ All | "
            "หลังสร้าง path เต็มจะเป็น เช่น All / กลุ่มพัสดุ / 5.วัสดุทั่วไป"
        ),
    },
    # -------------------------------------------------------------------------
    # 4. UoM
    # -------------------------------------------------------------------------
    "UoMCategory": {
        "area": "uom",
        "label": "หมวดหน่วยนับ",
        "headers": ["name"],
        "widths": [36],
        "samples": [
            ["หน่วย"],
            ["น้ำหนัก"],
            ["ปริมาตร"],
            ["กล่องแพ็ค"],
        ],
        "note": "สร้างหมวดหน่วยก่อน แล้วค่อยสร้าง UoM ในชีต UoM",
    },
    "UoM": {
        "area": "uom",
        "label": "หน่วยนับ",
        "headers": [
            "name",
            "category",
            "uom_type",
            "factor",
            "rounding",
            "active",
        ],
        "widths": [20, 20, 14, 12, 12, 10],
        "samples": [
            ["หน่วย", "หน่วย", "reference", 1, 1, 1],
            ["กล่อง-100", "กล่องแพ็ค", "reference", 1, 1, 1],
            ["ชิ้นในกล่อง", "กล่องแพ็ค", "smaller", 100, 1, 1],
            ["กิโลกรัม", "น้ำหนัก", "reference", 1, 0.001, 1],
            ["กรัม", "น้ำหนัก", "smaller", 1000, 1, 1],
        ],
        "note": (
            "category = ชื่อจากชีต UoMCategory | "
            "uom_type = reference / bigger / smaller | "
            "แต่ละหมวดต้องมี reference เพียง 1 หน่วย | "
            "factor = สัดส่วนเทียบกับหน่วยอ้างอิง "
            "(1 reference = factor × หน่วยนี้)"
        ),
    },
    # -------------------------------------------------------------------------
    # 5. Asset Profile / Asset Card
    # -------------------------------------------------------------------------
    "AssetProfile": {
        "area": "asset",
        "label": "Asset Profile (โปรไฟล์สินทรัพย์)",
        "headers": [
            "name",
            "method",
            "method_time",
            "method_number",
            "method_period",
            "account_asset_code",
            "account_depreciation_code",
            "account_expense_code",
            "journal_code",
            "salvage_value",
            "note",
        ],
        "widths": [28, 14, 12, 14, 14, 18, 22, 18, 14, 14, 30],
        "samples": [
            [
                "ครุภัณฑ์การแพทย์ 5 ปี",
                "linear",
                "year",
                5,
                "year",
                "1201",
                "1202",
                "5301",
                "MISC",
                1,
                "",
            ],
            [
                "ครุภัณฑ์คอมพิวเตอร์ 3 ปี",
                "linear",
                "year",
                3,
                "year",
                "1201",
                "1202",
                "5301",
                "MISC",
                1,
                "",
            ],
        ],
        "note": (
            "method = linear/linear-limit/degressive/... | "
            "method_time = year/number | method_period = year/month | "
            "account_*_code = รหัสบัญชีแยกประเภท | journal_code = รหัสสมุดรายวัน "
            "(ประเภท general) | ต้องมีบัญชีและสมุดรายวันในระบบก่อน"
        ),
    },
    "AssetCard": {
        "area": "asset",
        "label": "บัตรสินทรัพย์ (Fixed Asset)",
        "headers": [
            "code",
            "name",
            "profile_name",
            "purchase_value",
            "salvage_value",
            "date_start",
            "partner_ref",
            "owning_analytic_code",
            "project_code",
            "project_name",
            "fiscal_year",
            "useful_life_years",
            "location",
            "product_code",
            "note",
        ],
        "widths": [
            16, 36, 28, 14, 14, 14, 14, 18, 14, 24, 12, 14, 20, 14, 30,
        ],
        "samples": [
            [
                "AST-0001",
                "เครื่อง Ultrasound",
                "ครุภัณฑ์การแพทย์ 5 ปี",
                850000,
                1,
                "2025-10-01",
                "V001",
                "DEPT-RAD",
                "PRJ-64-01",
                "โครงการจัดซื้อครุภัณฑ์",
                "2568",
                5,
                "ห้องตรวจ 2",
                "",
                "",
            ],
        ],
        "note": (
            "profile_name อ้างอิงชีต AssetProfile | "
            "date_start = วันที่เริ่มคิดค่าเสื่อม (YYYY-MM-DD) | "
            "owning_analytic_code = รหัสบัญชีวิเคราะห์/แผนกเจ้าของ | "
            "product_code = default_code สินค้าต้นทาง (ถ้ามี) | "
            "นำเข้าเป็นสถานะ draft ก่อน แล้วค่อย Validate ในระบบ"
        ),
    },
    # -------------------------------------------------------------------------
    # 6. Analytic / Department / Project
    # -------------------------------------------------------------------------
    "AnalyticPlan": {
        "area": "analytic",
        "label": "แผนบัญชีวิเคราะห์",
        "headers": ["name", "parent_name", "default_applicability"],
        "widths": [28, 28, 20],
        "samples": [
            ["หน่วยงาน", "", "optional"],
            ["โครงการ", "", "optional"],
            ["แผนก", "หน่วยงาน", "optional"],
        ],
        "note": (
            "parent_name = ชื่อแผนแม่ (ว่างได้) | "
            "default_applicability = optional/mandatory/unavailable | "
            "ในระบบ VPK มักใช้แผน 'หน่วยงาน' สำหรับแผนก/กลุ่มงาน"
        ),
    },
    "AnalyticAccount": {
        "area": "analytic",
        "label": "บัญชีวิเคราะห์ / แผนก",
        "headers": ["code", "name", "plan_name", "parent_code", "active"],
        "widths": [16, 36, 20, 16, 10],
        "samples": [
            ["DEPT-RAD", "รังสีวิทยา", "หน่วยงาน", "", 1],
            ["DEPT-LAB", "ห้องปฏิบัติการ", "หน่วยงาน", "", 1],
            ["DEPT-PHAR", "เภสัชกรรม", "หน่วยงาน", "", 1],
            ["GRP-MED", "กลุ่มงานการแพทย์", "หน่วยงาน", "", 1],
        ],
        "note": (
            "plan_name อ้างอิงชีต AnalyticPlan | "
            "ใช้เป็นแผนก/หน่วยงานในงบประมาณและสินทรัพย์ | "
            "code แนะนำให้ไม่ซ้ำเพื่อใช้อ้างอิงตอน import"
        ),
    },
    "Project": {
        "area": "analytic",
        "label": "โครงการ",
        "headers": [
            "code",
            "name",
            "plan_name",
            "analytic_code",
            "partner_ref",
            "active",
            "note",
        ],
        "widths": [16, 40, 16, 16, 14, 10, 30],
        "samples": [
            [
                "PRJ-64-01",
                "โครงการจัดซื้อครุภัณฑ์ปี 2568",
                "โครงการ",
                "PRJ-64-01",
                "",
                1,
                "สร้างเป็น analytic account ภายใต้แผนโครงการ",
            ],
            [
                "PRJ-64-02",
                "โครงการปรับปรุงอาคาร",
                "โครงการ",
                "PRJ-64-02",
                "",
                1,
                "",
            ],
        ],
        "note": (
            "ใน VPK โครงการบนสินทรัพย์เก็บเป็น project_code/project_name (ข้อความ) | "
            "แนะนำสร้าง analytic account ภายใต้แผน 'โครงการ' ด้วย code เดียวกัน "
            "เพื่อใช้วิเคราะห์ต้นทุน | analytic_code = รหัสบัญชีวิเคราะห์ที่จะสร้าง/อ้างอิง"
        ),
    },
    # -------------------------------------------------------------------------
    # 7. Equipment opening balance (Maintenance ↔ Asset)
    # -------------------------------------------------------------------------
    "EquipmentCategory": {
        "area": "equipment",
        "label": "หมวด Equipment",
        "headers": ["name", "active"],
        "widths": [36, 10],
        "samples": [
            ["ครุภัณฑ์การแพทย์ 5 ปี", 1],
            ["ครุภัณฑ์คอมพิวเตอร์ 3 ปี", 1],
            ["ครุภัณฑ์สำนักงาน", 1],
        ],
        "note": (
            "ชื่อหมวดควรตรงกับ Asset Profile ถ้าต้องการให้ระบบ map อัตโนมัติ "
            "(vpk_asset_equipment ใช้ชื่อ profile เป็นชื่อ category)"
        ),
    },
    "Equipment": {
        "area": "equipment",
        "label": "ยกยอด Equipment + เชื่อม Asset",
        "headers": [
            "name",
            "category_name",
            "asset_number",
            "asset_code",
            "serial_no",
            "model",
            "location",
            "partner_ref",
            "cost",
            "effective_date",
            "assign_date",
            "warranty_date",
            "owner_login",
            "technician_login",
            "maintenance_team",
            "active",
            "note",
        ],
        "widths": [
            36, 28, 18, 16, 18, 18, 20, 16, 14, 14, 14, 14, 16, 16, 18, 10, 30,
        ],
        "samples": [
            [
                "เครื่อง Ultrasound",
                "ครุภัณฑ์การแพทย์ 5 ปี",
                "AST-0001",
                "",
                "SN-US-001",
                "GE-Vivid",
                "ห้องตรวจ 2",
                "BILL-2024-001",
                850000,
                "2024-01-15",
                "2024-01-20",
                "2027-01-15",
                "",
                "",
                "Maintenance Team",
                1,
                "ยกยอดจากระบบเดิม",
            ],
            [
                "คอมพิวเตอร์ตั้งโต๊ะ ห้องบัญชี",
                "ครุภัณฑ์คอมพิวเตอร์ 3 ปี",
                "AST-0102",
                "",
                "SN-PC-8899",
                "Dell OptiPlex",
                "ฝ่ายบัญชี",
                "",
                28500,
                "2023-06-01",
                "2023-06-01",
                "2026-06-01",
                "",
                "",
                "Maintenance Team",
                1,
                "",
            ],
        ],
        "note": (
            "ยกยอด Equipment ใน Maintenance และเชื่อม Fixed Asset | "
            "asset_number = หมายเลขทรัพย์สิน (account.asset.number) — คีย์หลักในการลิงก์ | "
            "asset_code = รหัสอ้างอิง asset (account.asset.code) ใช้เมื่อยังไม่มี number | "
            "category_name อ้างอิงชีต EquipmentCategory | "
            "serial_no ต้องไม่ซ้ำในระบบ | วันที่ใช้ YYYY-MM-DD | "
            "หลัง import ควรได้ equipment.asset_id และ asset.equipment_id ครบทั้งสองฝั่ง"
        ),
    },
    # -------------------------------------------------------------------------
    # 8. Vendor / ผู้จำหน่าย
    # -------------------------------------------------------------------------
    "Vendor": {
        "area": "vendor",
        "label": "ผู้จำหน่าย (res.partner)",
        "headers": [
            "ref",
            "name",
            "name_company",
            "company_type",
            "vat",
            "company_registry",
            "vat_type",
            "vendor_trade_group",
            "street",
            "street2",
            "city",
            "state",
            "zip",
            "country",
            "phone",
            "mobile",
            "email",
            "website",
            "payment_term",
            "supplier_rank",
            "active",
            "comment",
            "vpk_vendor_external_id",
        ],
        "widths": [
            12, 36, 28, 14, 16, 16, 18, 18, 28, 20, 18, 16, 10, 14, 14, 14, 26, 20, 14, 14, 10, 28, 18,
        ],
        "samples": [
            [
                "V001",
                "บริษัท เมดิซัพพลาย จำกัด",
                "เมดิซัพพลาย",
                "company",
                "0105558123456",
                "00000",
                "vat_registered",
                "regular",
                "123 ถ.พญาไท",
                "",
                "กรุงเทพมหานคร",
                "Bangkok",
                "10400",
                "Thailand",
                "022221111",
                "0812345678",
                "vendor@example.com",
                "",
                "30 Days",
                1,
                1,
                "",
                "",
            ],
            [
                "V002",
                "หจก. เภสัชภัณฑ์ไทย",
                "เภสัชภัณฑ์ไทย",
                "company",
                "0103549988776",
                "00000",
                "vat_registered",
                "regular",
                "88 ถ.เพชรบุรี",
                "",
                "กรุงเทพมหานคร",
                "Bangkok",
                "10400",
                "Thailand",
                "022223333",
                "",
                "phar@example.com",
                "",
                "Immediate Payment",
                1,
                1,
                "",
                "",
            ],
            [
                "V003",
                "นายสมชาย ขายตรง",
                "",
                "person",
                "1234567890123",
                "",
                "vat_non_registered",
                "regular",
                "10 หมู่ 5",
                "",
                "นนทบุรี",
                "Nonthaburi",
                "11000",
                "Thailand",
                "",
                "0899990000",
                "",
                "",
                "",
                1,
                1,
                "ผู้ขายไม่จด VAT",
                "",
            ],
        ],
        "note": (
            "ref = รหัสผู้จำหน่าย (key ใช้อ้างอิงชีตอื่น) | "
            "นิติบุคคล: กรอก name_company (name จะถูกคำนวณตามประเภทบริษัท) | "
            "บุคคลธรรมดา: กรอก name และ company_type=person | "
            "vat = เลขผู้เสียภาษี 13 หลัก | company_registry = รหัสสาขา เช่น 00000 สำนักงานใหญ่ | "
            "vat_type = vat_registered / vat_non_registered / vat_exempt / government / foreign | "
            "vendor_trade_group = regular (ผู้ค้าปกติ) / unselected_bidder | "
            "supplier_rank ต้องเป็น 1 เพื่อให้เป็น Vendor | "
            "นำเข้าที่ Contacts หรือ Purchase > Vendors (Import)"
        ),
    },
    "VendorBank": {
        "area": "vendor",
        "label": "บัญชีธนาคารผู้จำหน่าย",
        "headers": [
            "partner_ref",
            "acc_number",
            "acc_holder_name",
            "bank_name",
            "bank_bic",
            "active",
        ],
        "widths": [14, 18, 28, 28, 14, 10],
        "samples": [
            ["V001", "1234567890", "บริษัท เมดิซัพพลาย จำกัด", "ธนาคารกรุงไทย", "KTTHTHBK", 1],
            ["V002", "9988776655", "หจก. เภสัชภัณฑ์ไทย", "ธนาคารกรุงเทพ", "BKKBTHBK", 1],
        ],
        "note": (
            "partner_ref อ้างอิงชีต Vendor.ref | "
            "acc_number = เลขที่บัญชี | bank_name = ชื่อธนาคารในระบบ (res.bank) | "
            "bank_bic = SWIFT/BIC ถ้ามี | "
            "นำเข้าโมเดล res.partner.bank โดยจับคู่ partner จาก ref"
        ),
    },
    "VendorPricelist": {
        "area": "vendor",
        "label": "ราคาผู้จำหน่าย / MOQ",
        "headers": [
            "partner_ref",
            "product_code",
            "product_name",
            "min_qty",
            "price",
            "delay",
            "moq_qty",
            "order_multiple",
            "uom",
            "currency",
        ],
        "widths": [14, 14, 36, 12, 12, 10, 12, 14, 12, 12],
        "samples": [
            [
                "V001",
                "3012815",
                "Syringe Dispos 10ml",
                1,
                1.71,
                7,
                100,
                100,
                "กล่อง-100",
                "THB",
            ],
            [
                "V002",
                "DEMO-001",
                "ตัวอย่างสินค้าทั่วไป",
                1,
                8.50,
                3,
                1,
                1,
                "หน่วย",
                "THB",
            ],
        ],
        "note": (
            "โมเดล product.supplierinfo (Vendors บนสินค้า) | "
            "partner_ref อ้างอิง Vendor.ref | product_code = default_code สินค้า | "
            "min_qty = จำนวนขั้นต่ำของราคา | delay = วันนำเข้า (lead time) | "
            "moq_qty / order_multiple จากโมดูล vpk_purchase_moq | "
            "ต้องมีสินค้าและผู้จำหน่ายในระบบก่อน"
        ),
    },
    # -------------------------------------------------------------------------
    # 9. Purchase Request (PR)
    # -------------------------------------------------------------------------
    "PurchaseRequest": {
        "area": "purchase_request",
        "label": "ใบขอซื้อ (Header)",
        "headers": [
            "name",
            "date_start",
            "requested_by",
            "department",
            "assigned_to",
            "origin",
            "description",
            "procurement_type",
            "purchase_type",
            "procurement_method",
            "expense_reason",
            "warehouse_code",
            "urgency_level",
            "urgency_reason",
            "urgency_needed_date",
            "budget_analytic_code",
            "budget_fund_source",
            "budget_group",
            "budget_post",
            "budget_section_key",
            "state",
        ],
        "widths": [
            16, 14, 16, 20, 16, 16, 32, 18, 18, 18, 24, 14, 14, 28, 16, 18, 16, 16, 18, 16, 12,
        ],
        "samples": [
            [
                "PR-2568-0001",
                "2025-10-01",
                "admin",
                "เภสัชกรรม",
                "",
                "",
                "ขอซื้อเวชภัณฑ์ประจำเดือน",
                "พัสดุ",
                "จัดซื้อ",
                "เฉพาะเจาะจง",
                "",
                "PHAR",
                "normal",
                "",
                "",
                "DEPT-PHAR",
                "งบประมาณแผ่นดิน",
                "",
                "",
                "material",
                "draft",
            ],
            [
                "PR-2568-0002",
                "2025-10-05",
                "admin",
                "รังสีวิทยา",
                "",
                "MEMO-001",
                "ขอซื้อเร่งด่วนวัสดุการแพทย์",
                "พัสดุ",
                "จัดซื้อ",
                "เฉพาะเจาะจง",
                "",
                "WH",
                "urgent",
                "ของหมด ใช้กับผู้ป่วยฉุกเฉิน",
                "2025-10-10",
                "DEPT-RAD",
                "งบประมาณแผ่นดิน",
                "",
                "",
                "material",
                "draft",
            ],
        ],
        "note": (
            "name = เลขที่ PR จากระบบเดิม (key ไปชีต PurchaseRequestLine) ถ้าว่างระบบจะออกเลขใหม่ | "
            "requested_by / assigned_to = login ของ user | department = ชื่อหน่วยงาน (hr.department) | "
            "procurement_type / purchase_type / procurement_method = ชื่อในระบบ "
            "(l10n_th_gov_purchase_request) ต้องมี master ก่อน | "
            "warehouse_code อ้างอิงชีต Warehouse เพื่อหา picking type รับเข้า | "
            "urgency_level = normal/urgent/emergency (urgent/emergency ต้องมี urgency_reason "
            "และ urgency_needed_date) | "
            "budget_section_key = material/asset/project/construction | "
            "budget_* อ้างอิงรหัส/ชื่อ master งบประมาณ | "
            "state แนะนำ draft แล้วยืนยันในระบบ (อย่า import เป็น approved/done โดยตรง "
            "ถ้ายังไม่พร้อมเรื่องงบ/อนุมัติ) | โมเดล purchase.request"
        ),
    },
    "PurchaseRequestLine": {
        "area": "purchase_request",
        "label": "รายการใบขอซื้อ (Lines)",
        "headers": [
            "pr_name",
            "product_code",
            "name",
            "product_qty",
            "uom",
            "estimated_cost",
            "date_required",
            "specifications",
            "supplier_ref",
        ],
        "widths": [16, 14, 36, 12, 12, 16, 14, 32, 14],
        "samples": [
            [
                "PR-2568-0001",
                "3012815",
                "Syringe Dispos 10ml",
                10,
                "กล่อง-100",
                1710,
                "2025-10-15",
                "",
                "V001",
            ],
            [
                "PR-2568-0001",
                "DEMO-001",
                "ตัวอย่างสินค้าทั่วไป",
                20,
                "หน่วย",
                160,
                "2025-10-15",
                "",
                "V002",
            ],
            [
                "PR-2568-0002",
                "3012815",
                "Syringe Dispos 10ml",
                2,
                "กล่อง-100",
                342,
                "2025-10-10",
                "ใช้กับห้องฉุกเฉิน",
                "V001",
            ],
        ],
        "note": (
            "pr_name ต้องตรงกับ PurchaseRequest.name | "
            "product_code = default_code สินค้า (ต้องมีในระบบ) | "
            "estimated_cost = มูลค่ารวมโดยประมาณของบรรทัด (ไม่ใช่ราคาต่อหน่วย) | "
            "uom ต้องอยู่ในหมวดเดียวกับหน่วยของสินค้า | "
            "supplier_ref = รหัสผู้จำหน่ายที่ต้องการ (optional) | "
            "โมเดล purchase.request.line"
        ),
    },
    # -------------------------------------------------------------------------
    # 10. Purchase Order (PO)
    # -------------------------------------------------------------------------
    "PurchaseOrder": {
        "area": "purchase_order",
        "label": "ใบสั่งซื้อ (Header)",
        "headers": [
            "name",
            "partner_ref",
            "date_order",
            "date_planned",
            "date_approve",
            "origin",
            "pr_name",
            "vendor_order_ref",
            "buyer_login",
            "payment_term",
            "warehouse_code",
            "currency",
            "notes",
            "state",
        ],
        "widths": [
            16, 14, 14, 14, 14, 16, 16, 18, 14, 18, 14, 10, 28, 12,
        ],
        "samples": [
            [
                "PO-2568-0001",
                "V001",
                "2025-10-08",
                "2025-10-20",
                "2025-10-08",
                "PR-2568-0001",
                "PR-2568-0001",
                "",
                "admin",
                "30 Days",
                "PHAR",
                "THB",
                "",
                "draft",
            ],
            [
                "PO-2568-0002",
                "V002",
                "2025-10-09",
                "2025-10-18",
                "",
                "PR-2568-0001",
                "PR-2568-0001",
                "QT-8899",
                "admin",
                "Immediate Payment",
                "WH",
                "THB",
                "",
                "draft",
            ],
        ],
        "note": (
            "name = เลขที่ PO จากระบบเดิม (key ไปชีต PurchaseOrderLine) | "
            "partner_ref = รหัสผู้จำหน่าย (Vendor.ref) ต้องมีก่อน | "
            "pr_name = เลขที่ PR ที่อ้างอิง (optional, ใช้ลิงก์ purchase.request) | "
            "origin มักใส่เลขที่ PR/เอกสารต้นทาง | "
            "vendor_order_ref = เลขที่เอกสารของผู้ขาย (ฟิลด์ partner_ref ของ PO) | "
            "warehouse_code ใช้หา picking type รับเข้า | "
            "state แนะนำ draft แล้ว Confirm ในระบบ "
            "(Confirm จะสร้างใบรับสินค้า — ห้าม import เป็น purchase/done "
            "ถ้ายังไม่พร้อมเรื่องสต็อก) | โมเดล purchase.order"
        ),
    },
    "PurchaseOrderLine": {
        "area": "purchase_order",
        "label": "รายการใบสั่งซื้อ (Lines)",
        "headers": [
            "po_name",
            "product_code",
            "name",
            "product_qty",
            "uom",
            "price_unit",
            "discount",
            "taxes",
            "date_planned",
            "pr_name",
        ],
        "widths": [16, 14, 36, 12, 12, 12, 10, 14, 14, 16],
        "samples": [
            [
                "PO-2568-0001",
                "3012815",
                "Syringe Dispos 10ml",
                10,
                "กล่อง-100",
                171.00,
                0,
                "7%",
                "2025-10-20",
                "PR-2568-0001",
            ],
            [
                "PO-2568-0002",
                "DEMO-001",
                "ตัวอย่างสินค้าทั่วไป",
                20,
                "หน่วย",
                8.00,
                0,
                "7%",
                "2025-10-18",
                "PR-2568-0001",
            ],
        ],
        "note": (
            "po_name ต้องตรงกับ PurchaseOrder.name | "
            "product_code = default_code | price_unit = ราคาต่อหน่วย (ยังไม่รวม/รวมภาษีตามตั้งค่าสินค้า) | "
            "taxes = ชื่อภาษีซื้อในระบบ เช่น 7% (คั่นด้วย comma ถ้าหลายตัว) | "
            "pr_name ใช้ลิงก์กลับไป purchase.request.line ถ้าต้องการ | "
            "โมเดล purchase.order.line"
        ),
    },
    # -------------------------------------------------------------------------
    # 11. Chart of Accounts
    # -------------------------------------------------------------------------
    "ChartOfAccounts": {
        "area": "coa",
        "label": "ผังบัญชี",
        "headers": [
            "code",
            "name",
            "account_type",
            "reconcile",
            "wht_account",
            "deprecated",
            "note",
        ],
        "widths": [16, 40, 22, 12, 12, 12, 36],
        "samples": [
            ["110101", "เงินสดย่อย", "asset_cash", 0, 0, 0, ""],
            ["110201", "เงินฝากธนาคารกรุงไทย", "asset_cash", 0, 0, 0, ""],
            ["120101", "ลูกหนี้การค้า", "asset_receivable", 1, 0, 0, ""],
            ["210101", "เจ้าหนี้การค้า", "liability_payable", 1, 0, 0, ""],
            ["210201", "ภาษีหัก ณ ที่จ่ายค้างจ่าย", "liability_current", 0, 1, 0, "บัญชี WHT"],
            ["210301", "ภาษีซื้อ", "asset_current", 0, 0, 0, "VAT Input"],
            ["210401", "ภาษีขาย", "liability_current", 0, 0, 0, "VAT Output"],
            ["310101", "ทุน / ดุลยกมา", "equity", 0, 0, 0, ""],
            ["410101", "รายได้ค่าบริการ", "income", 0, 0, 0, ""],
            ["510101", "ค่าวัสดุการแพทย์", "expense", 0, 0, 0, ""],
            ["510201", "ค่าบริการวิชาชีพ", "expense", 0, 0, 0, ""],
            ["530101", "ค่าเสื่อมราคาครุภัณฑ์", "expense_depreciation", 0, 0, 0, ""],
        ],
        "note": (
            "โมเดล account.account | code = รหัสบัญชี (key) | "
            "account_type = asset_receivable / asset_cash / asset_current / "
            "asset_non_current / asset_prepayments / asset_fixed / "
            "liability_payable / liability_credit_card / liability_current / "
            "liability_non_current / equity / equity_unaffected / income / "
            "income_other / expense / expense_depreciation / expense_direct_cost / "
            "off_balance | reconcile = 1 สำหรับลูกหนี้/เจ้าหนี้ | "
            "wht_account = 1 ถ้าเป็นบัญชีภาษีหัก ณ ที่จ่าย (l10n_th_account_tax) | "
            "deprecated = 1 เพื่อเลิกใช้บัญชี"
        ),
    },
    # -------------------------------------------------------------------------
    # 12. Accounting setup (journals / tax / payment terms / company bank)
    # -------------------------------------------------------------------------
    "Journal": {
        "area": "accounting_setup",
        "label": "สมุดรายวัน",
        "headers": [
            "code",
            "name",
            "type",
            "default_account_code",
            "currency",
            "bank_acc_number",
            "active",
        ],
        "widths": [10, 28, 12, 20, 10, 18, 10],
        "samples": [
            ["BILL", "ใบแจ้งหนี้ผู้ขาย", "purchase", "", "THB", "", 1],
            ["INV", "ใบแจ้งหนี้ลูกหนี้", "sale", "", "THB", "", 1],
            ["CASH", "เงินสด", "cash", "110101", "THB", "", 1],
            ["BNK1", "ธนาคารกรุงไทย", "bank", "110201", "THB", "123-0-12345-6", 1],
            ["MISC", "รายการทั่วไป", "general", "", "THB", "", 1],
            ["WHT", "ภาษีหัก ณ ที่จ่าย", "general", "210201", "THB", "", 1],
        ],
        "note": (
            "โมเดล account.journal | code สูงสุด 5 ตัวอักษร (key) | "
            "type = sale/purchase/cash/bank/credit/general | "
            "default_account_code = รหัสบัญชีจากชีต ChartOfAccounts "
            "(จำเป็นสำหรับ cash/bank) | "
            "bank_acc_number อ้างอิงชีต CompanyBank เมื่อ type=bank"
        ),
    },
    "Tax": {
        "area": "accounting_setup",
        "label": "ภาษีมูลค่าเพิ่ม",
        "headers": [
            "name",
            "type_tax_use",
            "amount_type",
            "amount",
            "invoice_label",
            "account_code",
            "active",
        ],
        "widths": [16, 14, 14, 10, 16, 16, 10],
        "samples": [
            ["7%", "purchase", "percent", 7, "VAT 7%", "210301", 1],
            ["7%", "sale", "percent", 7, "VAT 7%", "210401", 1],
            ["0%", "purchase", "percent", 0, "VAT 0%", "", 1],
            ["Exempt", "purchase", "percent", 0, "ยกเว้น VAT", "", 1],
        ],
        "note": (
            "โมเดล account.tax | name ใช้อ้างอิงคอลัมน์ taxes ในใบแจ้งหนี้/PO | "
            "type_tax_use = sale/purchase/none | "
            "amount_type = percent/fixed/group | amount = อัตรา เช่น 7 | "
            "account_code = บัญชีภาษีซื้อ/ขาย"
        ),
    },
    "WithholdingTax": {
        "area": "accounting_setup",
        "label": "ภาษีหัก ณ ที่จ่าย (Master)",
        "headers": [
            "name",
            "percent",
            "account_code",
            "income_tax_form",
            "wht_cert_income_type",
            "is_pit",
        ],
        "widths": [18, 10, 16, 16, 22, 10],
        "samples": [
            ["WHT 1%", 1, "210201", "pnd53", "5", 0],
            ["WHT 2%", 2, "210201", "pnd53", "5", 0],
            ["WHT 3%", 3, "210201", "pnd53", "5", 0],
            ["WHT 5%", 5, "210201", "pnd3", "2", 0],
            ["PIT", 0, "210201", "pnd1", "1", 1],
        ],
        "note": (
            "โมเดล account.withholding.tax (l10n_th_account_tax) | "
            "account_code ต้องเป็นบัญชีที่ wht_account=1 | "
            "income_tax_form = pnd1/pnd2/pnd3/pnd3a/pnd53 | "
            "wht_cert_income_type = 1 / 2 / 3 / 4A / 4B11 / 5 / 6 ฯลฯ | "
            "is_pit = 1 สำหรับภาษีเงินได้บุคคลธรรมดา (มีได้เพียง 1 รายการ)"
        ),
    },
    "PaymentTerm": {
        "area": "accounting_setup",
        "label": "เงื่อนไขการชำระเงิน",
        "headers": ["name", "note", "active"],
        "widths": [22, 40, 10],
        "samples": [
            ["Immediate Payment", "ชำระทันที", 1],
            ["30 Days", "เครดิต 30 วัน", 1],
            ["45 Days", "เครดิต 45 วัน", 1],
            ["End of Month", "สิ้นเดือน", 1],
        ],
        "note": (
            "โมเดล account.payment.term | name เป็นคีย์ไปชีต PaymentTermLine "
            "และ VendorBill.payment_term"
        ),
    },
    "PaymentTermLine": {
        "area": "accounting_setup",
        "label": "รายละเอียดเงื่อนไขชำระ",
        "headers": [
            "payment_term",
            "value",
            "value_amount",
            "delay_type",
            "nb_days",
        ],
        "widths": [22, 12, 14, 28, 10],
        "samples": [
            ["Immediate Payment", "percent", 100, "days_after", 0],
            ["30 Days", "percent", 100, "days_after", 30],
            ["45 Days", "percent", 100, "days_after", 45],
            ["End of Month", "percent", 100, "days_after_end_of_month", 0],
        ],
        "note": (
            "payment_term อ้างอิงชีต PaymentTerm.name | "
            "value = percent หรือ fixed | value_amount = 100 สำหรับ percent ทั้งจำนวน | "
            "delay_type = days_after / days_after_end_of_month / "
            "days_after_end_of_next_month / days_end_of_month_on_the"
        ),
    },
    "CompanyBank": {
        "area": "accounting_setup",
        "label": "บัญชีธนาคารของหน่วยงาน",
        "headers": [
            "acc_number",
            "acc_holder_name",
            "bank_name",
            "bank_bic",
            "journal_code",
            "active",
        ],
        "widths": [18, 36, 28, 14, 14, 10],
        "samples": [
            [
                "123-0-12345-6",
                "โรงพยาบาลวชิระภูเก็ต",
                "ธนาคารกรุงไทย",
                "KTTHTHBK",
                "BNK1",
                1,
            ],
        ],
        "note": (
            "โมเดล res.partner.bank ของบริษัท (ไม่ใช่ Vendor) | "
            "journal_code อ้างอิงชีต Journal ที่ type=bank | "
            "ใช้เป็นบัญชีต้นทางตอนจ่ายชำระในระบบการเงิน"
        ),
    },
    # -------------------------------------------------------------------------
    # 13. Work Acceptance
    # -------------------------------------------------------------------------
    "WorkAcceptance": {
        "area": "work_acceptance",
        "label": "ใบตรวจรับงาน (Header)",
        "headers": [
            "name",
            "po_name",
            "partner_ref",
            "invoice_ref",
            "date_receive",
            "date_due",
            "acceptance_date",
            "delivery_date",
            "due_date_contract",
            "acceptance_type",
            "responsible_login",
            "inspector_login",
            "penalty_amount",
            "warranty_end_date",
            "notes",
            "state",
        ],
        "widths": [
            16, 16, 14, 18, 14, 14, 16, 14, 18, 16, 16, 16, 14, 16, 28, 12,
        ],
        "samples": [
            [
                "WA-2568-0001",
                "PO-2568-0001",
                "V001",
                "INV-V001-2568-001",
                "2025-10-20",
                "2025-10-25",
                "2025-10-21",
                "2025-10-20",
                "2025-10-31",
                "full",
                "admin",
                "admin",
                0,
                "2027-10-20",
                "",
                "draft",
            ],
        ],
        "note": (
            "โมเดล work.acceptance | name = เลขที่ใบตรวจรับ (key) | "
            "po_name อ้างอิง PurchaseOrder.name ต้องมี PO ก่อน | "
            "partner_ref = Vendor.ref | invoice_ref = เลขที่ใบแจ้งหนี้ผู้ขาย | "
            "acceptance_type = full/partial/reject | "
            "วันที่ใช้ YYYY-MM-DD (ระบบแปลงเป็น datetime) | "
            "state แนะนำ draft แล้วกดตรวจรับในระบบ | "
            "ใบแจ้งหนี้ผู้ขายสามารถอ้าง wa_name ได้"
        ),
    },
    "WorkAcceptanceLine": {
        "area": "work_acceptance",
        "label": "รายการตรวจรับ (Lines)",
        "headers": [
            "wa_name",
            "product_code",
            "name",
            "product_qty",
            "uom",
            "price_unit",
            "po_name",
        ],
        "widths": [16, 14, 36, 12, 12, 12, 16],
        "samples": [
            [
                "WA-2568-0001",
                "3012815",
                "Syringe Dispos 10ml",
                10,
                "กล่อง-100",
                171.00,
                "PO-2568-0001",
            ],
        ],
        "note": (
            "โมเดล work.acceptance.line | wa_name ต้องตรงกับ WorkAcceptance.name | "
            "product_code = default_code | price_unit = ราคาต่อหน่วยตาม PO | "
            "จำนวนที่ตรวจรับต้องไม่เกินจำนวนค้างรับของ PO"
        ),
    },
    "WorkAcceptanceCommittee": {
        "area": "work_acceptance",
        "label": "คณะกรรมการตรวจรับ",
        "headers": ["wa_name", "sequence", "role", "name", "position", "user_login", "note"],
        "widths": [16, 10, 14, 28, 24, 14, 24],
        "samples": [
            ["WA-2568-0001", 1, "chairman", "นายประธาน ตรวจรับ", "หัวหน้ากลุ่มงาน", "", ""],
            ["WA-2568-0001", 2, "member", "นางสาวกรรมการ หนึ่ง", "เภสัชกร", "", ""],
            ["WA-2568-0001", 3, "secretary", "นายเลขา ตรวจรับ", "เจ้าหน้าที่พัสดุ", "", ""],
        ],
        "note": (
            "โมเดล work.acceptance.committee (vpk_work_acceptance) | "
            "role = chairman (ประธาน) / member (กรรมการ) / secretary (เลขานุการ) | "
            "user_login = login ของผู้ใช้งานถ้ามีในระบบ"
        ),
    },
    # -------------------------------------------------------------------------
    # 14. Vendor bills / credit notes (Accounts Payable)
    # -------------------------------------------------------------------------
    "VendorBill": {
        "area": "vendor_bill",
        "label": "ใบแจ้งหนี้ผู้ขาย (Header)",
        "headers": [
            "name",
            "partner_ref",
            "ref",
            "invoice_date",
            "invoice_date_due",
            "date",
            "journal_code",
            "payment_term",
            "po_name",
            "wa_name",
            "currency",
            "narration",
            "budget_analytic_code",
            "budget_fund_source",
            "state",
        ],
        "widths": [
            16, 14, 20, 14, 16, 14, 14, 18, 16, 16, 10, 28, 18, 18, 12,
        ],
        "samples": [
            [
                "BILL-2568-0001",
                "V001",
                "INV-V001-2568-001",
                "2025-10-21",
                "2025-11-20",
                "2025-10-21",
                "BILL",
                "30 Days",
                "PO-2568-0001",
                "WA-2568-0001",
                "THB",
                "ตั้งเจ้าหนี้ตามใบแจ้งหนี้ผู้ขาย",
                "DEPT-PHAR",
                "งบประมาณแผ่นดิน",
                "draft",
            ],
        ],
        "note": (
            "โมเดล account.move (move_type=in_invoice) | "
            "name = เลขที่เอกสารในระบบ (ถ้าว่างระบบจะออกเลขจากสมุดรายวัน) | "
            "ref = เลขที่ใบแจ้งหนี้ของผู้ขาย (สำคัญ ไม่ควรซ้ำคู่ vendor+วันที่) | "
            "partner_ref = Vendor.ref ต้องมีก่อน | "
            "po_name / wa_name ใช้ลิงก์ PO และใบตรวจรับ | "
            "journal_code ต้องเป็นสมุดรายวัน type=purchase | "
            "state แนะนำ draft แล้ว Post ในระบบ "
            "(Post จะตั้งเจ้าหนี้และกระทบงบประมาณ) | "
            "budget_* อ้างอิงหน่วยงาน/แหล่งเงิน"
        ),
    },
    "VendorBillLine": {
        "area": "vendor_bill",
        "label": "รายการใบแจ้งหนี้ผู้ขาย",
        "headers": [
            "bill_name",
            "product_code",
            "name",
            "quantity",
            "uom",
            "price_unit",
            "discount",
            "taxes",
            "wht_tax",
            "account_code",
            "analytic_code",
            "po_name",
            "budget_post",
        ],
        "widths": [
            16, 14, 36, 12, 12, 12, 10, 10, 12, 14, 14, 16, 16,
        ],
        "samples": [
            [
                "BILL-2568-0001",
                "3012815",
                "Syringe Dispos 10ml",
                10,
                "กล่อง-100",
                171.00,
                0,
                "7%",
                "WHT 1%",
                "510101",
                "DEPT-PHAR",
                "PO-2568-0001",
                "",
            ],
        ],
        "note": (
            "โมเดล account.move.line (invoice lines) | "
            "bill_name ต้องตรงกับ VendorBill.name | "
            "taxes = ชื่อภาษีซื้อจากชีต Tax คั่นด้วย comma | "
            "wht_tax = ชื่อจากชีต WithholdingTax (optional) | "
            "account_code = บัญชีค่าใช้จ่าย/สินทรัพย์ ถ้าว่างระบบใช้จากหมวดสินค้า | "
            "analytic_code = รหัสบัญชีวิเคราะห์/แผนก"
        ),
    },
    "VendorCreditNote": {
        "area": "vendor_bill",
        "label": "ใบลดหนี้ผู้ขาย (Header)",
        "headers": [
            "name",
            "partner_ref",
            "ref",
            "invoice_date",
            "date",
            "journal_code",
            "reversed_bill_name",
            "po_name",
            "currency",
            "narration",
            "state",
        ],
        "widths": [16, 14, 20, 14, 14, 14, 18, 16, 10, 32, 12],
        "samples": [
            [
                "CN-2568-0001",
                "V001",
                "CN-V001-001",
                "2025-10-25",
                "2025-10-25",
                "BILL",
                "BILL-2568-0001",
                "PO-2568-0001",
                "THB",
                "คืนสินค้า / ลดหนี้ตามใบลดหนี้ผู้ขาย",
                "draft",
            ],
        ],
        "note": (
            "โมเดล account.move (move_type=in_refund) | "
            "reversed_bill_name = เลขที่ใบแจ้งหนี้ต้นทางที่ต้องการลดหนี้ | "
            "state แนะนำ draft | ใช้เมื่อคืนสินค้าหรือปรับลดยอดเจ้าหนี้"
        ),
    },
    "VendorCreditNoteLine": {
        "area": "vendor_bill",
        "label": "รายการใบลดหนี้ผู้ขาย",
        "headers": [
            "cn_name",
            "product_code",
            "name",
            "quantity",
            "uom",
            "price_unit",
            "taxes",
            "account_code",
            "analytic_code",
        ],
        "widths": [16, 14, 36, 12, 12, 12, 10, 14, 14],
        "samples": [
            [
                "CN-2568-0001",
                "3012815",
                "Syringe Dispos 10ml",
                1,
                "กล่อง-100",
                171.00,
                "7%",
                "510101",
                "DEPT-PHAR",
            ],
        ],
        "note": (
            "cn_name ต้องตรงกับ VendorCreditNote.name | "
            "จำนวนและราคาต้องสอดคล้องกับใบแจ้งหนี้ต้นทาง"
        ),
    },
    "TaxInvoice": {
        "area": "vendor_bill",
        "label": "ใบกำกับภาษีซื้อ",
        "headers": [
            "bill_name",
            "tax_invoice_number",
            "tax_invoice_date",
            "partner_ref",
            "tax_base_amount",
            "tax_amount",
            "report_late_mo",
        ],
        "widths": [16, 22, 16, 14, 16, 14, 14],
        "samples": [
            [
                "BILL-2568-0001",
                "INV-V001-2568-001",
                "2025-10-21",
                "V001",
                1710.00,
                119.70,
                "0",
            ],
        ],
        "note": (
            "โมเดล account.move.tax.invoice (l10n_th_account_tax) | "
            "bill_name อ้างอิง VendorBill | tax_invoice_number = เลขที่ใบกำกับภาษี | "
            "report_late_mo = 0-6 (เดือนที่รายงานล่าช้า) | "
            "ใช้ยื่น ภ.พ.30 — ต้องตรงกับยอด VAT ในใบแจ้งหนี้"
        ),
    },
    # -------------------------------------------------------------------------
    # 15. Finance (payments / bank statement)
    # -------------------------------------------------------------------------
    "VendorPayment": {
        "area": "finance",
        "label": "ใบจ่ายชำระเจ้าหนี้ (Header)",
        "headers": [
            "name",
            "partner_ref",
            "date",
            "journal_code",
            "amount",
            "currency",
            "payment_method",
            "memo",
            "wht_tax",
            "wht_amount",
            "bank_acc_number",
            "state",
        ],
        "widths": [16, 14, 14, 14, 14, 10, 16, 28, 12, 12, 18, 12],
        "samples": [
            [
                "PAY-2568-0001",
                "V001",
                "2025-11-20",
                "BNK1",
                1810.53,
                "THB",
                "manual",
                "จ่ายตาม BILL-2568-0001",
                "WHT 1%",
                17.10,
                "123-0-12345-6",
                "draft",
            ],
        ],
        "note": (
            "โมเดล account.payment (payment_type=outbound, partner_type=supplier) | "
            "journal_code ต้องเป็น cash หรือ bank | "
            "amount = ยอดที่จ่ายจริง (หลังหัก WHT ถ้าหักตอนจ่าย) | "
            "payment_method = manual / check / batch_payment ตามที่ตั้งในสมุดรายวัน | "
            "wht_tax / wht_amount กรอกเมื่อหัก ณ ที่จ่ายตอนจ่าย "
            "(account_payment_multi_deduction / l10n_th_account_tax) | "
            "state แนะนำ draft แล้ว Confirm/Post ในระบบ เพื่อกระทบยอดเจ้าหนี้"
        ),
    },
    "VendorPaymentLine": {
        "area": "finance",
        "label": "รายการกระทบยอดใบแจ้งหนี้",
        "headers": [
            "payment_name",
            "bill_name",
            "bill_ref",
            "amount",
            "currency",
        ],
        "widths": [16, 16, 20, 14, 10],
        "samples": [
            ["PAY-2568-0001", "BILL-2568-0001", "INV-V001-2568-001", 1829.70, "THB"],
        ],
        "note": (
            "ระบุใบแจ้งหนี้ที่ต้องการจ่ายในแต่ละใบจ่าย | "
            "payment_name อ้างอิง VendorPayment.name | "
            "bill_name หรือ bill_ref อย่างน้อยหนึ่งค่า (เลขที่ในระบบ หรือเลขที่ผู้ขาย) | "
            "amount = ยอดที่จ่ายกับใบนั้น (รองรับจ่ายบางส่วน) | "
            "ผลรวม amount ของบรรทัดควรเท่ากับ VendorPayment.amount + WHT"
        ),
    },
    "BankStatement": {
        "area": "finance",
        "label": "ใบแจ้งยอดธนาคาร (Header)",
        "headers": [
            "name",
            "journal_code",
            "date",
            "balance_start",
            "balance_end_real",
        ],
        "widths": [20, 14, 14, 16, 16],
        "samples": [
            ["STMT-KTB-2025-10", "BNK1", "2025-10-31", 1500000.00, 1498189.47],
        ],
        "note": (
            "โมเดล account.bank.statement | "
            "journal_code ต้องเป็นสมุดรายวัน type=bank หรือ cash | "
            "balance_start = ยอดยกมา | balance_end_real = ยอดตาม Statement ธนาคาร | "
            "ใช้กระทบยอดเงินฝากในระบบการเงิน"
        ),
    },
    "BankStatementLine": {
        "area": "finance",
        "label": "รายการ Statement",
        "headers": [
            "statement_name",
            "date",
            "payment_ref",
            "partner_ref",
            "amount",
            "ref",
        ],
        "widths": [20, 14, 32, 14, 14, 18],
        "samples": [
            [
                "STMT-KTB-2025-10",
                "2025-10-05",
                "รับโอนรายได้",
                "",
                50000.00,
                "",
            ],
            [
                "STMT-KTB-2025-10",
                "2025-11-20",
                "จ่าย V001 ตาม PAY-2568-0001",
                "V001",
                -1810.53,
                "PAY-2568-0001",
            ],
        ],
        "note": (
            "โมเดล account.bank.statement.line | "
            "statement_name อ้างอิง BankStatement.name | "
            "amount บวก = เงินเข้า, ลบ = เงินออก | "
            "partner_ref อ้างอิง Vendor/ลูกค้าถ้าทราบ | "
            "หลังนำเข้าให้ Reconcile กับใบจ่าย/ใบเสร็จในระบบ"
        ),
    },
    # -------------------------------------------------------------------------
    # 16. General journal / opening balance
    # -------------------------------------------------------------------------
    "JournalEntry": {
        "area": "journal_entry",
        "label": "รายการบัญชีทั่วไป (Header)",
        "headers": [
            "name",
            "journal_code",
            "date",
            "ref",
            "narration",
            "state",
        ],
        "widths": [16, 14, 14, 20, 40, 12],
        "samples": [
            [
                "MISC-2568-0001",
                "MISC",
                "2025-10-31",
                "JV-2568-001",
                "ปรับปรุงค่าใช้จ่ายสิ้นเดือน",
                "draft",
            ],
        ],
        "note": (
            "โมเดล account.move (move_type=entry) | "
            "journal_code ต้องเป็นสมุดรายวัน type=general | "
            "name ถ้าว่างระบบจะออกเลขจากสมุดรายวัน | "
            "แต่ละเอกสารเดบิตต้องเท่ากับเครดิต (ดูชีต JournalEntryLine) | "
            "state แนะนำ draft แล้ว Post ในระบบ"
        ),
    },
    "JournalEntryLine": {
        "area": "journal_entry",
        "label": "รายการบัญชีทั่วไป (Lines)",
        "headers": [
            "entry_name",
            "account_code",
            "name",
            "partner_ref",
            "analytic_code",
            "debit",
            "credit",
        ],
        "widths": [16, 14, 36, 14, 14, 14, 14],
        "samples": [
            [
                "MISC-2568-0001",
                "510201",
                "ค่าบริการวิชาชีพ ตุลาคม 2568",
                "",
                "DEPT-RAD",
                25000.00,
                0,
            ],
            [
                "MISC-2568-0001",
                "210101",
                "ตั้งเจ้าหนี้ค่าบริการ",
                "V002",
                "",
                0,
                25000.00,
            ],
        ],
        "note": (
            "entry_name ต้องตรงกับ JournalEntry.name | "
            "แต่ละบรรทัดกรอก debit หรือ credit อย่างใดอย่างหนึ่ง | "
            "ผลรวม debit ของเอกสารต้องเท่ากับผลรวม credit | "
            "partner_ref ใส่เมื่อบัญชีเป็นลูกหนี้/เจ้าหนี้ (reconcile=1)"
        ),
    },
    "OpeningBalance": {
        "area": "journal_entry",
        "label": "ยกยอดบัญชี (Header)",
        "headers": [
            "name",
            "journal_code",
            "date",
            "ref",
            "narration",
            "state",
        ],
        "widths": [16, 14, 14, 16, 40, 12],
        "samples": [
            [
                "OB-2568",
                "MISC",
                "2025-10-01",
                "OPENING",
                "ยกยอดเปิดระบบ ณ วันที่เริ่มใช้ Odoo",
                "draft",
            ],
        ],
        "note": (
            "ใช้ account.move ประเภท entry สำหรับยกยอดเปิดระบบ | "
            "date = วันเริ่มใช้ระบบ (วันก่อนรายการจริงวันแรก) | "
            "บัญชีกำไรขาดทุนไม่ควรยกยอด — ยกเฉพาะสินทรัพย์ หนี้สิน ส่วนทุน | "
            "เจ้าหนี้คงค้างที่ยังไม่จ่าย แนะนำใช้ชีต VendorBill แทน "
            "เพื่อให้มี partner และนำไปจ่ายในระบบการเงินได้"
        ),
    },
    "OpeningBalanceLine": {
        "area": "journal_entry",
        "label": "รายการยกยอดบัญชี",
        "headers": [
            "entry_name",
            "account_code",
            "name",
            "partner_ref",
            "analytic_code",
            "debit",
            "credit",
        ],
        "widths": [16, 14, 36, 14, 14, 14, 14],
        "samples": [
            ["OB-2568", "110101", "ยกยอดเงินสดย่อย", "", "", 25000.00, 0],
            ["OB-2568", "110201", "ยกยอดเงินฝากธนาคาร", "", "", 1500000.00, 0],
            ["OB-2568", "210101", "ยกยอดเจ้าหนี้การค้า", "V001", "", 0, 1829.70],
            ["OB-2568", "310101", "ส่วนทุน / ดุลยกมา", "", "", 0, 1523170.30],
        ],
        "note": (
            "รูปแบบเดียวกับ JournalEntryLine | "
            "ผลรวม debit ต้องเท่ากับ credit ทั้งชุดยกยอด | "
            "ถ้ามีเจ้าหนี้หลายราย ให้แยกบรรทัดตาม partner_ref | "
            "หลัง Post ควรกระทบยอด Trial Balance กับระบบเดิม"
        ),
    },
    # -------------------------------------------------------------------------
    # 17. Withholding tax certificates
    # -------------------------------------------------------------------------
    "WHTCert": {
        "area": "wht_cert",
        "label": "หนังสือรับรองหัก ณ ที่จ่าย (Header)",
        "headers": [
            "number",
            "partner_ref",
            "date",
            "income_tax_form",
            "tax_payer",
            "payment_name",
            "bill_name",
            "state",
        ],
        "widths": [16, 14, 14, 16, 16, 16, 16, 12],
        "samples": [
            [
                "WHT-2568-0001",
                "V001",
                "2025-11-20",
                "pnd53",
                "withholding",
                "PAY-2568-0001",
                "BILL-2568-0001",
                "draft",
            ],
        ],
        "note": (
            "โมเดล withholding.tax.cert (l10n_th_account_tax) | "
            "number = เลขที่หนังสือรับรอง (ถ้าว่างใช้ / ให้ระบบออกเลข) | "
            "income_tax_form = pnd1/pnd2/pnd3/pnd3a/pnd53 | "
            "tax_payer = withholding / paid_one_time / paid_continue | "
            "payment_name / bill_name ใช้อ้างอิงใบจ่ายหรือใบแจ้งหนี้ | "
            "ปกติระบบสร้างใบรับรองตอนจ่ายที่มี WHT — ชีตนี้ใช้ยกยอดใบรับรองระบบเดิม"
        ),
    },
    "WHTCertLine": {
        "area": "wht_cert",
        "label": "รายการหนังสือรับรองหัก ณ ที่จ่าย",
        "headers": [
            "cert_number",
            "wht_cert_income_type",
            "wht_cert_income_desc",
            "base",
            "wht_tax",
            "amount",
        ],
        "widths": [16, 22, 36, 14, 12, 14],
        "samples": [
            [
                "WHT-2568-0001",
                "5",
                "ค่าจ้างทำของ / ค่าบริการ 3 เตรส",
                1710.00,
                "WHT 1%",
                17.10,
            ],
        ],
        "note": (
            "โมเดล withholding.tax.cert.line | "
            "cert_number อ้างอิง WHTCert.number | "
            "wht_cert_income_type = 1 เงินเดือน / 2 ค่าธรรมเนียม / 3 ลิขสิทธิ์ / "
            "4A ดอกเบี้ย / 5 ค่าจ้างทำของ ค่าบริการ / 6 อื่นๆ | "
            "base = ฐานภาษี | amount = ภาษีที่หัก | "
            "wht_tax อ้างอิงชีต WithholdingTax.name"
        ),
    },
    # -------------------------------------------------------------------------
    # 18. Checkbook (สมุดเช็ค)
    # -------------------------------------------------------------------------
    "Checkbook": {
        "area": "checkbook",
        "label": "สมุดเช็ค (Header)",
        "headers": [
            "name",
            "journal_code",
            "bank_acc_number",
            "start_number",
            "end_number",
            "next_number",
            "issue_date",
            "state",
            "notes",
        ],
        "widths": [20, 14, 18, 16, 16, 16, 16, 12, 36],
        "samples": [
            [
                "CB-KTB-2568-01",
                "BNK1",
                "123-0-12345-6",
                "100001",
                "100050",
                "100003",
                "2025-10-01",
                "active",
                "สมุดเช็คกรุงไทย ชุดที่ 1 ปี 2568",
            ],
        ],
        "note": (
            "สมุดเช็คของหน่วยงาน (หนึ่งแถวต่อหนึ่งเล่ม) | "
            "name = เลขที่/รหัสสมุดเช็ค (key) | "
            "journal_code อ้างอิงชีต Journal ที่ type=bank | "
            "bank_acc_number อ้างอิงชีต CompanyBank | "
            "start_number / end_number = ช่วงเลขที่เช็คในเล่ม | "
            "next_number = เลขที่เช็คใบถัดไปที่ยังไม่ใช้ | "
            "state = draft / active / used / cancelled | "
            "ต้องมีสมุดรายวันธนาคารและบัญชีธนาคารก่อน | "
            "รายการเช็คแต่ละใบกรอกในชีต CheckbookLine"
        ),
    },
    "CheckbookLine": {
        "area": "checkbook",
        "label": "รายการเช็คในสมุด",
        "headers": [
            "checkbook_name",
            "check_number",
            "check_date",
            "partner_ref",
            "partner_name",
            "amount",
            "payment_name",
            "memo",
            "state",
        ],
        "widths": [20, 14, 14, 14, 28, 14, 16, 32, 12],
        "samples": [
            [
                "CB-KTB-2568-01",
                "100001",
                "2025-11-20",
                "V001",
                "บริษัท ตัวอย่าง จำกัด",
                1810.53,
                "PAY-2568-0001",
                "จ่ายตาม BILL-2568-0001",
                "issued",
            ],
            [
                "CB-KTB-2568-01",
                "100002",
                "",
                "",
                "",
                "",
                "",
                "",
                "available",
            ],
        ],
        "note": (
            "หนึ่งแถวต่อหนึ่งใบเช็ค | "
            "checkbook_name ต้องตรงกับ Checkbook.name | "
            "check_number ต้องอยู่ในช่วง start_number–end_number ของสมุดนั้น | "
            "partner_ref = รหัสผู้รับเงิน (Vendor.ref) เมื่อออกเช็คแล้ว | "
            "payment_name อ้างอิง VendorPayment.name ถ้าผูกกับใบจ่าย | "
            "state = available (ยังไม่ใช้) / issued (ออกเช็คแล้ว) / "
            "cashed (ขึ้นเงินแล้ว) / void (ยกเลิก/เสีย) | "
            "ใช้ทั้งเปิดสมุดใหม่ (ส่วนใหญ่ available) และยกยอดเช็คค้างจ่าย (issued)"
        ),
    },
}


AREA_SHEETS = {
    area: [name for name, spec in SHEETS.items() if spec["area"] == area]
    for area, _label in TEMPLATE_AREAS
}

# Default Thai labels for technical column names. Sheet-specific wording
# (e.g. name = เลขที่เอกสาร vs รายละเอียด) lives in SHEET_HEADER_THAI.
HEADER_THAI = {
    "acc_holder_name": "ชื่อบัญชี",
    "acc_number": "เลขที่บัญชีธนาคาร",
    "acceptance_date": "วันที่ตรวจรับ",
    "acceptance_type": "ผลการตรวจรับ",
    "account_asset_code": "รหัสบัญชีสินทรัพย์",
    "account_code": "รหัสบัญชี",
    "account_depreciation_code": "รหัสบัญชีค่าเสื่อมสะสม",
    "account_expense_code": "รหัสบัญชีค่าเสื่อม",
    "account_type": "ประเภทบัญชี",
    "active": "ใช้งาน",
    "amount": "จำนวนเงิน",
    "amount_type": "วิธีคำนวณภาษี",
    "analytic_code": "รหัสบัญชีวิเคราะห์",
    "asset_code": "รหัสสินทรัพย์",
    "asset_number": "หมายเลขทรัพย์สิน",
    "assign_date": "วันที่มอบหมาย",
    "assigned_to": "ผู้รับผิดชอบ (login)",
    "balance_end_real": "ยอดตาม Statement",
    "balance_start": "ยอดยกมา",
    "bank_acc_number": "เลขที่บัญชีธนาคาร",
    "bank_bic": "SWIFT/BIC",
    "bank_name": "ธนาคาร",
    "barcode": "บาร์โค้ด",
    "base": "ฐานภาษี",
    "bill_name": "เลขที่ใบแจ้งหนี้",
    "bill_ref": "เลขที่ใบแจ้งหนี้ผู้ขาย",
    "budget_analytic_code": "รหัสหน่วยงานงบประมาณ",
    "budget_fund_source": "แหล่งเงิน",
    "budget_group": "กลุ่มงบประมาณ",
    "budget_post": "หมวดงบประมาณ",
    "budget_section_key": "ประเภทงบ",
    "buyer_login": "ผู้ซื้อ (login)",
    "categ_path": "หมวดหมู่สินค้า (path)",
    "category": "หมวดหน่วยนับ",
    "category_name": "หมวด Equipment",
    "cert_number": "เลขที่หนังสือรับรอง",
    "check_date": "วันที่เช็ค",
    "check_number": "เลขที่เช็ค",
    "checkbook_name": "เลขที่สมุดเช็ค",
    "city": "อำเภอ/เขต",
    "cn_name": "เลขที่ใบลดหนี้",
    "code": "รหัส",
    "comment": "หมายเหตุ",
    "company_registry": "รหัสสาขา",
    "company_type": "ประเภทคู่ค้า",
    "cost": "มูลค่า",
    "country": "ประเทศ",
    "credit": "เครดิต",
    "currency": "สกุลเงิน",
    "date": "วันที่",
    "date_approve": "วันที่อนุมัติ",
    "date_due": "วันครบกำหนด",
    "date_order": "วันที่สั่งซื้อ",
    "date_planned": "วันที่กำหนดรับ",
    "date_receive": "วันที่รับของ",
    "date_required": "วันที่ต้องการ",
    "date_start": "วันที่เริ่ม",
    "debit": "เดบิต",
    "default_account_code": "รหัสบัญชีเริ่มต้น",
    "default_applicability": "การใช้บัญชีวิเคราะห์",
    "default_code": "รหัสสินค้า",
    "delay": "Lead time (วัน)",
    "delay_type": "วิธีนับวันครบกำหนด",
    "delivery_date": "วันที่ส่งมอบ",
    "delivery_steps": "ขั้นตอนจ่ายของ",
    "department": "หน่วยงาน",
    "deprecated": "เลิกใช้",
    "description": "คำอธิบาย",
    "discount": "ส่วนลด (%)",
    "due_date_contract": "วันครบกำหนดตามสัญญา",
    "effective_date": "วันที่เริ่มใช้",
    "email": "อีเมล",
    "egp_purchase_name": "ชื่อสำหรับซื้อใน e-GP",
    "entry_name": "เลขที่รายการบัญชี",
    "end_number": "เลขที่เช็คสิ้นสุด",
    "estimated_cost": "มูลค่าประมาณ",
    "expense_reason": "เหตุผลค่าใช้จ่าย",
    "expiration_time": "อายุใช้งาน (วัน)",
    "factor": "อัตราส่วนหน่วย",
    "fiscal_year": "ปีงบประมาณ",
    "income_tax_form": "ภงด.",
    "inspector_login": "ผู้ตรวจรับ (login)",
    "invoice_date": "วันที่ใบแจ้งหนี้",
    "invoice_date_due": "วันครบกำหนดชำระ",
    "issue_date": "วันที่รับสมุดเช็ค",
    "invoice_label": "ป้ายบนใบแจ้งหนี้",
    "invoice_ref": "เลขที่ใบแจ้งหนี้ผู้ขาย",
    "is_pit": "เป็น PIT",
    "is_storable": "เก็บสต็อก",
    "journal_code": "รหัสสมุดรายวัน",
    "list_price": "ราคาขาย",
    "location": "สถานที่",
    "maintenance_team": "ทีมซ่อมบำรุง",
    "memo": "บันทึกช่วยจำ",
    "method": "วิธีคิดค่าเสื่อม",
    "method_number": "อายุการใช้งาน",
    "method_period": "หน่วยช่วงเวลา",
    "method_time": "นับอายุเป็น",
    "min_qty": "จำนวนขั้นต่ำ",
    "mobile": "มือถือ",
    "model": "รุ่น",
    "moq_qty": "MOQ",
    "name": "ชื่อ",
    "name_company": "ชื่อบริษัท (ไม่ใส่คำนำหน้า)",
    "narration": "คำอธิบายรายการ",
    "next_number": "เลขที่เช็คถัดไป",
    "nb_days": "จำนวนวัน",
    "note": "หมายเหตุ",
    "notes": "หมายเหตุ",
    "number": "เลขที่หนังสือรับรอง",
    "order_multiple": "ตัวคูณสั่งซื้อ",
    "origin": "เอกสารต้นทาง",
    "owner_login": "ผู้ครอบครอง (login)",
    "owning_analytic_code": "รหัสหน่วยงานเจ้าของ",
    "parent_code": "รหัสบัญชีแม่",
    "parent_name": "ชื่อแผนแม่",
    "parent_path": "path หมวดแม่",
    "partner_ref": "รหัสผู้จำหน่าย",
    "partner_name": "ชื่อผู้รับเงิน",
    "payment_method": "วิธีจ่ายเงิน",
    "payment_name": "เลขที่ใบจ่าย",
    "payment_ref": "รายละเอียดรายการ",
    "payment_term": "เงื่อนไขการชำระ",
    "penalty_amount": "ค่าปรับ",
    "percent": "อัตรา (%)",
    "phone": "โทรศัพท์",
    "plan_name": "ชื่อแผนบัญชีวิเคราะห์",
    "po_name": "เลขที่ PO",
    "position": "ตำแหน่ง",
    "pr_name": "เลขที่ PR",
    "price": "ราคา",
    "price_unit": "ราคาต่อหน่วย",
    "procurement_method": "วิธีการจัดซื้อ",
    "procurement_type": "ประเภทพัสดุ",
    "product_code": "รหัสสินค้า",
    "product_name": "ชื่อสินค้า",
    "product_qty": "จำนวน",
    "profile_name": "ชื่อ Asset Profile",
    "project_code": "รหัสโครงการ",
    "project_name": "ชื่อโครงการ",
    "purchase_method": "วิธีบันทึกซื้อ",
    "purchase_ok": "ซื้อได้",
    "purchase_type": "ประเภทการซื้อ",
    "purchase_value": "มูลค่าซื้อ",
    "quantity": "จำนวน",
    "reception_steps": "ขั้นตอนรับของ",
    "reconcile": "กระทบยอดได้",
    "ref": "อ้างอิง",
    "report_late_mo": "รายงานล่าช้า (เดือน)",
    "requested_by": "ผู้ขอซื้อ (login)",
    "responsible_login": "ผู้รับผิดชอบ (login)",
    "reversed_bill_name": "เลขที่ใบแจ้งหนี้ต้นทาง",
    "role": "บทบาท",
    "rounding": "ปัดเศษ",
    "sale_ok": "ขายได้",
    "salvage_value": "มูลค่าซาก",
    "sequence": "ลำดับ",
    "serial_no": "หมายเลขเครื่อง",
    "specifications": "คุณลักษณะ",
    "standard_price": "ต้นทุน",
    "start_number": "เลขที่เช็คเริ่มต้น",
    "state": "สถานะ",
    "statement_name": "เลขที่ Statement",
    "street": "ที่อยู่",
    "street2": "ที่อยู่บรรทัด 2",
    "supplier_rank": "เป็นผู้จำหน่าย",
    "supplier_ref": "รหัสผู้จำหน่ายที่ต้องการ",
    "tax_amount": "ยอดภาษี",
    "tax_base_amount": "ฐานภาษี",
    "tax_invoice_date": "วันที่ใบกำกับภาษี",
    "tax_invoice_number": "เลขที่ใบกำกับภาษี",
    "tax_payer": "ผู้มีหน้าที่หัก",
    "taxes": "ภาษีซื้อ",
    "technician_login": "ช่างเทคนิค (login)",
    "tracking": "ติดตามล็อต/ซีเรียล",
    "type": "ประเภท",
    "type_tax_use": "ใช้กับภาษี",
    "uom": "หน่วยนับ",
    "uom_po": "หน่วยซื้อ",
    "uom_type": "ชนิดหน่วย",
    "urgency_level": "ระดับความเร่งด่วน",
    "urgency_needed_date": "วันที่ต้องการใช้ (เร่งด่วน)",
    "urgency_reason": "เหตุผลเร่งด่วน",
    "usage": "ประเภทตำแหน่ง",
    "use_expiration_date": "ใช้วันหมดอายุ",
    "useful_life_years": "อายุการใช้งาน (ปี)",
    "user_login": "ผู้ใช้งาน (login)",
    "value": "ชนิดยอด",
    "value_amount": "สัดส่วน/จำนวน",
    "vat": "เลขผู้เสียภาษี",
    "vat_type": "ประเภท VAT",
    "vendor_order_ref": "เลขที่เอกสารผู้ขาย",
    "vendor_trade_group": "กลุ่มผู้ค้า",
    "vpk_vendor_external_id": "รหัสภายนอกผู้จำหน่าย",
    "wa_name": "เลขที่ใบตรวจรับ",
    "warehouse_code": "รหัสคลัง",
    "warranty_date": "วันสิ้นสุดประกัน",
    "warranty_end_date": "วันสิ้นสุดประกัน",
    "website": "เว็บไซต์",
    "wht_account": "บัญชีหัก ณ ที่จ่าย",
    "wht_amount": "ยอดหัก ณ ที่จ่าย",
    "wht_cert_income_desc": "รายละเอียดเงินได้",
    "wht_cert_income_type": "ประเภทเงินได้",
    "wht_tax": "ภาษีหัก ณ ที่จ่าย",
    "zip": "รหัสไปรษณีย์",
}

# Override Thai wording where the same English field means different things.
SHEET_HEADER_THAI = {
    "Warehouse": {"code": "รหัสคลัง", "name": "ชื่อคลัง"},
    "Location": {"name": "ชื่อตำแหน่ง"},
    "Product": {"name": "ชื่อสินค้า", "type": "ประเภทสินค้า"},
    "ProductCategory": {"name": "ชื่อหมวดหมู่"},
    "UoMCategory": {"name": "ชื่อหมวดหน่วยนับ"},
    "UoM": {"name": "ชื่อหน่วยนับ"},
    "AssetProfile": {"name": "ชื่อโปรไฟล์สินทรัพย์"},
    "AssetCard": {"code": "รหัสสินทรัพย์", "name": "ชื่อสินทรัพย์"},
    "AnalyticPlan": {"name": "ชื่อแผน"},
    "AnalyticAccount": {"code": "รหัสหน่วยงาน", "name": "ชื่อหน่วยงาน"},
    "Project": {"code": "รหัสโครงการ", "name": "ชื่อโครงการ"},
    "EquipmentCategory": {"name": "ชื่อหมวด"},
    "Equipment": {"name": "ชื่อครุภัณฑ์"},
    "Vendor": {"ref": "รหัสผู้จำหน่าย", "name": "ชื่อผู้จำหน่าย"},
    "PurchaseRequest": {"name": "เลขที่ PR", "date_start": "วันที่ขอซื้อ"},
    "PurchaseRequestLine": {"name": "รายละเอียด"},
    "PurchaseOrder": {"name": "เลขที่ PO"},
    "PurchaseOrderLine": {"name": "รายละเอียด"},
    "ChartOfAccounts": {"code": "รหัสบัญชี", "name": "ชื่อบัญชี"},
    "Journal": {"code": "รหัสสมุดรายวัน", "name": "ชื่อสมุดรายวัน", "type": "ประเภทสมุดรายวัน"},
    "Tax": {"name": "ชื่อภาษี", "amount": "อัตรา (%)", "account_code": "รหัสบัญชีภาษี"},
    "WithholdingTax": {"name": "ชื่อภาษีหัก ณ ที่จ่าย", "account_code": "รหัสบัญชี WHT"},
    "PaymentTerm": {"name": "ชื่อเงื่อนไขชำระ"},
    "WorkAcceptance": {"name": "เลขที่ใบตรวจรับ"},
    "WorkAcceptanceLine": {"name": "รายละเอียด"},
    "WorkAcceptanceCommittee": {"name": "ชื่อ-สกุล"},
    "VendorBill": {
        "name": "เลขที่เอกสาร",
        "ref": "เลขที่ใบแจ้งหนี้ผู้ขาย",
        "date": "วันที่ลงบัญชี",
    },
    "VendorBillLine": {"name": "รายละเอียด"},
    "VendorCreditNote": {
        "name": "เลขที่เอกสาร",
        "ref": "เลขที่ใบลดหนี้ผู้ขาย",
        "date": "วันที่ลงบัญชี",
    },
    "VendorCreditNoteLine": {"name": "รายละเอียด"},
    "VendorPayment": {"name": "เลขที่ใบจ่าย", "date": "วันที่จ่าย", "amount": "ยอดที่จ่ายจริง"},
    "VendorPaymentLine": {"amount": "ยอดจ่ายตามใบนี้"},
    "BankStatement": {"name": "เลขที่ Statement", "date": "วันที่ Statement"},
    "BankStatementLine": {"amount": "จำนวนเงิน (+เข้า / -ออก)", "ref": "อ้างอิง"},
    "JournalEntry": {"name": "เลขที่รายการ", "date": "วันที่รายการ", "ref": "เอกสารอ้างอิง"},
    "JournalEntryLine": {"name": "รายละเอียด"},
    "OpeningBalance": {"name": "เลขที่รายการยกยอด", "date": "วันที่ยกยอด", "ref": "เอกสารอ้างอิง"},
    "OpeningBalanceLine": {"name": "รายละเอียด"},
    "WHTCert": {"date": "วันที่หักภาษี"},
    "Checkbook": {"name": "เลขที่สมุดเช็ค", "state": "สถานะสมุดเช็ค"},
    "CheckbookLine": {
        "partner_ref": "รหัสผู้รับเงิน",
        "state": "สถานะเช็ค",
    },
}


def thai_label(sheet_name, header):
    """Return the Thai column title for a technical header."""
    override = SHEET_HEADER_THAI.get(sheet_name, {}).get(header)
    if override:
        return override
    return HEADER_THAI.get(header, header)


def write_data_sheet(
    ws,
    sheet_name,
    spec,
    header_fmt,
    tech_fmt,
    sample_fmt,
    note_fmt,
    rows=None,
    extra_note="",
):
    """Write Thai + English headers, data rows and the note row onto a worksheet.

    If ``rows`` is provided it replaces the sample data (used when exporting
    live records such as Chart of Accounts from the database).
    """
    headers = spec["headers"]
    widths = spec["widths"]
    data_rows = list(rows) if rows is not None else list(spec.get("samples") or [])
    for col, (eng, width) in enumerate(zip(headers, widths)):
        thai = thai_label(sheet_name, eng)
        col_w = max(width, min(len(thai) + 2, 42))
        ws.write(0, col, thai, header_fmt)
        ws.write(1, col, eng, tech_fmt)
        ws.set_column(col, col, col_w)
    ws.set_row(0, 22)
    ws.freeze_panes(2, 0)
    for r_idx, row in enumerate(data_rows, start=2):
        for c_idx, value in enumerate(row):
            ws.write(r_idx, c_idx, value, sample_fmt)
    if data_rows:
        ws.autofilter(1, 0, 1 + len(data_rows), len(headers) - 1)
    note_row = max(len(data_rows) + 4, 6)
    note = spec["note"]
    if extra_note:
        note = "%s | %s" % (extra_note, note)
    ws.write(note_row, 0, "หมายเหตุ: %s" % note, note_fmt)


INSTRUCTIONS = [
    ("ลำดับเตรียมข้อมูลที่แนะนำ", ""),
    ("1", "UoMCategory → UoM"),
    ("2", "ProductCategory → Product"),
    ("3", "Warehouse → Location"),
    ("4", "AnalyticPlan → AnalyticAccount (แผนก) → Project"),
    ("5", "AssetProfile → AssetCard (นำเข้า Fixed Asset ก่อน)"),
    ("6", "EquipmentCategory → Equipment (ยกยอด + ลิงก์ Asset ด้วย asset_number)"),
    ("7", "Vendor → VendorBank → VendorPricelist"),
    ("8", "PurchaseRequest → PurchaseRequestLine (ต้องมีสินค้า / หน่วยงาน / ประเภทจัดซื้อก่อน)"),
    ("9", "PurchaseOrder → PurchaseOrderLine (ต้องมี Vendor และควรมี PR ก่อนถ้าต้องการลิงก์)"),
    ("10", "ChartOfAccounts → Journal / Tax / WithholdingTax / PaymentTerm → CompanyBank"),
    ("11", "WorkAcceptance → Lines / Committee (ต้องมี PO ก่อน)"),
    ("12", "VendorBill → VendorBillLine → TaxInvoice (ต้องมี Vendor, บัญชี, ภาษี และควรมี WA/PO)"),
    ("13", "VendorPayment → VendorPaymentLine (ต้องมีใบแจ้งหนี้ค้างจ่าย และสมุดรายวันธนาคาร/เงินสด)"),
    ("14", "Checkbook → CheckbookLine (ต้องมีสมุดรายวันธนาคาร / บัญชีธนาคารก่อน)"),
    ("15", "JournalEntry / OpeningBalance (เดบิตต้องเท่ากับเครดิต) → WHTCert ถ้ายกยอดใบหัก ณ ที่จ่าย"),
    ("", ""),
    ("วิธีใช้", "แถว 1 = หัวคอลัมน์ภาษาไทย (สำหรับผู้กรอก) | แถว 2 = ชื่อฟิลด์ภาษาอังกฤษ (ใช้ตอนนำเข้า) | กรอกข้อมูลจากแถว 3 เป็นต้นไป แล้วส่งไฟล์ให้ทีมนำเข้า"),
    ("ค่า 1/0", "1 = ใช่/เปิดใช้งาน, 0 = ไม่/ปิดใช้งาน"),
    ("วันที่", "ใช้รูปแบบ YYYY-MM-DD เช่น 2025-10-01"),
    ("Product import", "มีเมนู Inventory > Import Product Master อยู่แล้ว"),
    ("Budget master", "มีเมนู งบประมาณ > การกำหนดค่า > Import Budget Master"),
    (
        "Equipment ↔ Asset",
        "ใช้ asset_number จับคู่กับบัตรสินทรัพย์ | ต้องมีโมดูล vpk_asset_equipment",
    ),
    (
        "Vendor",
        "ref เป็นคีย์หลัก | นิติบุคคลใช้ name_company | vat 13 หลัก + สาขา 00000 | "
        "supplier_rank=1 | vat_type กำหนด Fiscal Position",
    ),
    (
        "PR / PO",
        "แยกชีต Header กับ Line โดยใช้ name / pr_name / po_name เป็นคีย์ | "
        "แนะนำนำเข้าสถานะ draft แล้วยืนยันในระบบ | "
        "Confirm PO จะสร้างใบรับสินค้า — อย่า import เป็น purchase/done ถ้ายังไม่พร้อมเรื่องสต็อก",
    ),
    (
        "ผังบัญชี / ตั้งค่า",
        "นำเข้า ChartOfAccounts ก่อน Journal และ Tax | "
        "บัญชีเจ้าหนี้/ลูกหนี้ต้อง reconcile=1 | "
        "บัญชี WHT ต้อง wht_account=1 ก่อนสร้าง WithholdingTax",
    ),
    (
        "ระบบเจ้าหนี้",
        "ลำดับเอกสาร: PO → ตรวจรับ (WA) → ใบแจ้งหนี้ผู้ขาย → จ่ายชำระ | "
        "ref = เลขที่ใบแจ้งหนี้ของผู้ขาย | "
        "แนะนำนำเข้าสถานะ draft แล้ว Post ในระบบ เพื่อตั้งเจ้าหนี้และกระทบงบ",
    ),
    (
        "ระบบการเงิน",
        "VendorPayment ใช้อ้างอิงใบแจ้งหนี้ใน VendorPaymentLine | "
        "journal เป็น bank/cash | หัก WHT ตอนจ่ายแล้วค่อยออกหนังสือรับรอง | "
        "BankStatement ใช้กระทบยอดเงินฝากหลังมีรายการจ่าย/รับ | "
        "สมุดเช็ค: Checkbook หนึ่งแถวต่อหนึ่งเล่ม แล้วกรอกใบเช็คใน CheckbookLine "
        "(available = ยังไม่ใช้, issued = ออกเช็คแล้ว)",
    ),
    (
        "ระบบบัญชี",
        "JournalEntry สำหรับรายการปรับปรุงทั่วไป | "
        "OpeningBalance สำหรับยกยอดเปิดระบบ (สินทรัพย์ หนี้สิน ส่วนทุน) | "
        "เจ้าหนี้คงค้างแนะนำใช้ VendorBill ไม่ใช่แค่ยกยอดบัญชี "
        "เพื่อให้จ่ายชำระและออกรายงานเจ้าหนี้ได้",
    ),
]
