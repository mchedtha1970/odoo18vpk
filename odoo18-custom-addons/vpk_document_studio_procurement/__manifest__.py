# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Document Studio - Procurement",
    "version": "18.0.1.2.0",
    "category": "Purchases",
    "summary": "เอกสารจัดซื้อจัดจ้าง (คำสั่งแต่งตั้ง, รายงานขออนุมัติ, ใบตรวจรับ) ด้วย Document Studio",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase_request",
        "l10n_th_gov_purchase_request",
        "l10n_th_base_utils",
        "purchase_work_acceptance",
        "vpk_work_acceptance",
        "vpk_purchase_agreement_egp",
        "vpk_tier_validation",
        "vpk_document_studio_sign",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/document_template_data.xml",
        "wizard/studio_document_add_views.xml",
        "wizard/egp_document_add_views.xml",
        "views/studio_document_views.xml",
        "views/purchase_requisition_egp_views.xml",
        "views/purchase_request_views.xml",
        "views/work_acceptance_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
