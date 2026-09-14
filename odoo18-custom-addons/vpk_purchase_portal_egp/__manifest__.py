# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK e-GP Vendor Portal",
    "version": "18.0.1.2.1",
    "category": "Purchases",
    "summary": "Vendor Portal: login, list own POs, and confirm online",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "portal",
        "auth_signup",
        "vpk_purchase_agreement_egp",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "wizard/vendor_portal_user_wizard_views.xml",
        "views/res_partner_views.xml",
        "views/purchase_order_views.xml",
        "views/portal_templates.xml",
        "report/purchase_order_templates.xml",
    ],
    "installable": True,
    "application": False,
}
