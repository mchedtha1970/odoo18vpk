{
    "name": "VPK PR Saraban - เชื่อมสารบรรณขอเลขหนังสือจาก PR",
    "version": "18.0.1.1.2",
    "category": "Purchases",
    "summary": "ออกเลขงานสารบรรณจากหนังสือราชการที่เกี่ยวข้องกับใบขอซื้อ และเชื่อมเลขที่หนังสือในเอกสารแต่ละฉบับ",
    "depends": [
        "purchase_request",
        "vpk_tier_validation",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/saraban_document_views.xml",
        "views/purchase_request_saraban_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
