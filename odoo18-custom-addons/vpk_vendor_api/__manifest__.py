# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Vendor Registration API",
    "version": "18.0.1.1.0",
    "category": "Purchases",
    "summary": "HTTP API รับลงทะเบียนโปรไฟล์และเอกสารทางการค้าผู้จำหน่ายจากระบบภายนอก",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "portal",
        "auth_signup",
        "l10n_th_partner",
    ],
    "data": [
        "security/vendor_api_security.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter_data.xml",
        "views/vendor_api_log_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
