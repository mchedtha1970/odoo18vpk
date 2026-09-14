{
    "name": "VPK Sequential Approval Workflow",
    "version": "18.0.1.5.47",
    "category": "Tools",
    "summary": "Multi-level sequential approval for Purchase, Stock, Bills and more",
    "description": """
Sequential Tier Approval (VPK Bundle)
=====================================

Enables unlimited approval levels (Tier 1, 2, 3, ...) with
**Approve by sequence** so each approver acts in order.

Supported documents out of the box:
- Purchase Request (ใบขอซื้อ)
- Purchase Order (ใบสั่งซื้อ)
- Vendor Bill / Invoice (บิล/ใบแจ้งหนี้)
- Stock Transfer (การรับ-จ่ายสินค้า)
- Expense (ค่าใช้จ่าย)

Configure at: Settings → การอนุมัติตามลำดับ → กำหนดลำดับการอนุมัติ
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "html_editor",
        "base_tier_validation",
        "base_tier_validation_formula",
        "purchase_request_tier_validation",
        "purchase_tier_validation",
        "account_move_tier_validation",
        "stock_picking_tier_validation",
        "hr_expense_tier_validation",
        "l10n_th_tier_department",
        "l10n_th_gov_purchase_request",
        "l10n_th_base_utils",
        "purchase_request",
        "vpk_sidebar_menu",
        "vpk_th_purchase_menu",
    ],
    "data": [
        "security/vpk_pr_security_groups.xml",
        "data/vpk_pr_user_groups.xml",
        "data/report_paperformat.xml",
        "report/purchase_request_official_memo_templates.xml",
        "report/purchase_request_official_memo_report.xml",
        "views/purchase_request_memo_views.xml",
        "views/purchase_request_views.xml",
        "views/tier_review_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "vpk_tier_validation/static/src/scss/official_memo_report.scss",
        ],
        "web.assets_backend": [
            (
                "after",
                "html_editor/static/src/main/align_plugin.js",
                "vpk_tier_validation/static/src/js/memo_editor_enhancements.js",
            ),
            "vpk_tier_validation/static/src/js/memo_html_field.js",
            "vpk_tier_validation/static/src/scss/memo_html_field.scss",
            "vpk_tier_validation/static/src/scss/pending_review_kanban.scss",
            "vpk_tier_validation/static/src/scss/pending_review_dashboard.scss",
            "vpk_tier_validation/static/src/dashboard/pending_review_dashboard.js",
            "vpk_tier_validation/static/src/dashboard/pending_review_dashboard.xml",
            "vpk_tier_validation/static/src/js/sidebar_menu_badge.js",
            "vpk_tier_validation/static/src/xml/sidebar_menu_badge.xml",
            "vpk_tier_validation/static/src/xml/tier_review_widget_label.xml",
            "vpk_tier_validation/static/src/js/tier_review_widget_expand.js",
            "vpk_tier_validation/static/src/scss/tier_review_widget_theme_font.scss",
        ],
    },
    "installable": True,
    "application": True,
}
