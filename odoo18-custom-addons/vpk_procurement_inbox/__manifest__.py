{
    "name": "VPK Procurement Inbox Dashboard",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "Dashboard ให้พัสดุ monitor และรับงานใบขอซื้อจากหน่วยงาน",
    "description": """
Procurement Inbox (รอรับจากหน่วยงาน)
====================================

- แสดงใบขอซื้อที่หน่วยงานกด ส่งพัสดุ แล้ว
- KPI: ทั้งหมด / ยังไม่มีผู้รับ / ของฉัน / ค้างเกิน 3 วัน
- ปุ่ม รับงาน / คืนคิว เพื่อดึงมาทำงานง่าย
- Badge จำนวนรายการบนเมนู
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase_request",
        "purchase_request_department",
        "vpk_tier_validation",
        "vpk_th_purchase_menu",
        "vpk_sidebar_menu",
    ],
    "data": [
        "data/ir_cron_data.xml",
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
