# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK HIS Interface",
    "version": "18.0.1.8.0",
    "category": "Accounting",
    "summary": "REST API รับสรุปรายวันจาก HIS เข้าคิว staging แล้วลงบัญชีรายได้และตัดสต็อก",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "account",
        "stock",
        "mail",
    ],
    "data": [
        "security/his_api_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_config_parameter_data.xml",
        "data/stock_data.xml",
        "data/his_partner_category_data.xml",
        "data/his_partner_data.xml",
        "data/his_entitlement_map_data.xml",
        "data/his_payment_method_map_data.xml",
        "views/his_batch_views.xml",
        "views/account_payment_views.xml",
        "views/his_entitlement_map_views.xml",
        "views/his_payment_method_map_views.xml",
        "views/his_unit_map_views.xml",
        "views/his_api_log_views.xml",
        "views/his_remittance_wizard_views.xml",
        "report/his_remittance_report.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.report_assets_common": [
            "vpk_his_api/static/src/scss/his_remittance_report.scss",
        ],
    },
    "installable": True,
    "application": False,
}
