# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Purchase Contract Documents",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "แท็บเอกสารสัญญา: ดึงจาก Document Studio หรือแนบไฟล์ แล้วส่งลงนามตามลำดับผู้อนุมัติ",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "vpk_purchase_contract",
        "vpk_document_studio_procurement",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/studio_document_type_data.xml",
        "wizard/contract_document_add_views.xml",
        "views/purchase_contract_document_views.xml",
    ],
    "installable": True,
    "application": False,
}
