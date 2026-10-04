# -*- coding: utf-8 -*-
{
    "name": "VPK Stock Receipt QC",
    "version": "18.0.1.4.1",
    "category": "Inventory",
    "summary": "ตรวจคุณภาพสินค้าขาเข้าก่อนรับเข้าคลัง",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["stock", "vpk_maintenance", "vpk_procurement_auto_pr"],
    "data": [
        "security/stock_qc_security.xml",
        "security/ir.model.access.csv",
        "data/qc_sequence.xml",
        "data/qc_cold_chain_point.xml",
        "views/product_template_views.xml",
        "views/stock_qc_views.xml",
        "views/stock_picking_views.xml",
        "wizard/qc_check_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
