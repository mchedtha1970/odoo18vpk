# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    "name": "VPK ใบรับรองการหักภาษี ณ ที่จ่าย (แบบ 4235)",
    "version": "18.0.1.0.2",
    "category": "Accounting/Accounting",
    "summary": "ใบรับรองการหักภาษี ณ ที่จ่าย (แบบ 4235) มีโมเดลและรายการเอกสารของตัวเอง พิมพ์ได้จากใบสำคัญจ่าย",
    "description": """
ใบรับรองการหักภาษี ณ ที่จ่าย (แบบ 4235)
========================================
* โมเดล vpk.wht.cert.4235 แยกออกจากใบสำคัญจ่าย
* แสดงรายการใบรับรองการหักภาษี ณ ที่จ่าย และรายการเอกสาร PDF ของตัวเอง
* พิมพ์ออกรายการจากแบบฟอร์ม Word (template_ใบรับรองการหักภาษี_แบบ4235.docx)
* สั่งพิมพ์ได้จากหน้าใบสำคัญจ่าย (vpk.payment.voucher) เหมือนเดิม
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "account",
        "mail",
        "l10n_th_amount_to_text",
        "vpk_payment_voucher",
        "vpk_document_studio",
        "vpk_document_studio_procurement",
        "vpk_document_studio_sign",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/document_type_data.xml",
        "views/wht_cert_4235_views.xml",
        "views/payment_voucher_views.xml",
        "views/studio_document_views.xml",
    ],
    "installable": True,
    "application": False,
}
