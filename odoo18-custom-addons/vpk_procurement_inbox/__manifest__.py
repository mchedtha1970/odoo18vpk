{
    "name": "VPK Procurement Inbox Dashboard",
    "version": "18.0.1.5.2",
    "category": "Purchases",
    "summary": "กล่องรวมงานใบขอซื้อ ให้หัวหน้าตรวจสอบแล้วมอบหมายให้เจ้าหน้าที่",
    "description": """
Procurement Inbox (กล่องรวมงานใบขอซื้อ)
====================================

- เมื่อหน่วยงานกด ส่งจัดซื้อ ใบขอซื้อจะรวมที่กล่องกลาง
- หัวหน้าพัสดุ/admin ตรวจสอบ แล้วมอบหมายหรือส่งต่องานให้เจ้าหน้าที่ที่เกี่ยวข้อง
- เจ้าหน้าที่พัสดุทำงานจากรายการที่ได้รับมอบหมาย
- KPI: ทั้งหมด / รอมอบหมาย / มอบหมายแล้ว / ของฉัน / ค้างเกิน 3 วัน
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "purchase_request",
        "purchase_request_department",
        "vpk_tier_validation",
        "vpk_budget",
        "vpk_purchase_agreement_egp",
        "vpk_th_purchase_menu",
        "vpk_sidebar_menu",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/procurement_inbox_rules.xml",
        "data/ir_cron_data.xml",
        "data/procurement_test_users.xml",
        "wizard/purchase_request_return_wizard_views.xml",
        "wizard/purchase_request_assign_wizard_views.xml",
        "views/purchase_request_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_procurement_inbox/static/src/scss/procurement_inbox_dashboard.scss",
            "vpk_procurement_inbox/static/src/scss/procurement_inbox_kanban.scss",
            "vpk_procurement_inbox/static/src/dashboard/procurement_inbox_dashboard.js",
            "vpk_procurement_inbox/static/src/dashboard/procurement_inbox_dashboard.xml",
            "vpk_procurement_inbox/static/src/js/sidebar_menu_badge.js",
            "vpk_procurement_inbox/static/src/xml/sidebar_menu_badge.xml",
        ],
    },
    "installable": True,
    "application": False,
}
