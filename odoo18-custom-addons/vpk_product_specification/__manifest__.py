{
    "name": "VPK Product Specification - รายละเอียดคุณลักษณะพัสดุ",
    "version": "18.0.1.3.0",
    "category": "Purchases",
    "summary": "คุณลักษณะพัสดุ Auto generate จาก PR ที่มีสัญญา + แนบเอกสาร/รูป Scan แยกรายการสินค้า",
    "depends": [
        "purchase_request",
        "vpk_purchase_contract",
        "product",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/product_specification_views.xml",
        "views/purchase_request_views.xml",
        "views/menu_views.xml",
        "report/product_specification_report.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
