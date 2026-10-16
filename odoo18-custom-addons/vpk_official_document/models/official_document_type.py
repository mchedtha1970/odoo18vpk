# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

FALLBACK_DOCUMENT_TYPES = [
    ("wa_committee_order", "คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ"),
    ("integrity_over_100k", "แบบแสดงความบริสุทธิ์ใจ (วงเงินมากกว่า ๑๐๐,๐๐๐ บาท)"),
    (
        "spec_price_committee",
        "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดรายละเอียดคุณลักษณะ",
    ),
    (
        "specific_method_approval",
        "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
    ),
    ("winner_announcement", "ประกาศผู้ชนะการเสนอราคา"),
    ("award_approval", "รายงานผลการพิจารณาจัดซื้อจัดจ้าง"),
    ("purchase_approval_memo", "บันทึกข้อความอนุมัติขอซื้อ"),
    ("inspection_report", "ใบตรวจรับการจัดซื้อ/จัดจ้าง"),
]


class OfficialDocumentType(models.Model):
    _name = "vpk.official.document.type"
    _description = "ประเภทหนังสือราชการ"
    _order = "sequence, id"

    name = fields.Char(string="ชื่อประเภท", required=True, translate=True)
    code = fields.Char(
        string="รหัส",
        index=True,
        copy=False,
        help="เว้นว่างได้ ระบบจะออกให้เอง ไม่เปลี่ยนรหัสของประเภทที่มากับระบบ",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_system = fields.Boolean(
        string="ประเภทของระบบ",
        default=False,
        copy=False,
        help="ประเภทที่มากับระบบ แก้ชื่อได้ แต่ลบหรือเปลี่ยนรหัสไม่ได้",
    )
    create_from_purchase_request = fields.Boolean(
        string="สร้างจากใบขอซื้อ",
        help="แสดงในช่องเอกสารที่จะสร้างของแท็บเอกสารราชการที่เกี่ยวข้อง",
    )
    create_from_work_acceptance = fields.Boolean(
        string="สร้างจากใบรับมอบงาน",
        help="แสดงในช่องเอกสารที่จะสร้างของแท็บเอกสารราชการที่เกี่ยวข้องในใบรับมอบงาน",
    )
    note = fields.Text(string="คำอธิบาย")

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            "รหัสประเภทเอกสารต้องไม่ซ้ำ",
        ),
    ]

    @api.model
    def selection_pairs(self):
        """Options for document type dropdowns. Falls back while the table is loading."""
        if not self.env.registry.ready:
            return list(FALLBACK_DOCUMENT_TYPES)
        types = self.sudo().with_context(active_test=False).search([])
        if not types:
            return list(FALLBACK_DOCUMENT_TYPES)
        return [(item.code, item.name) for item in types if item.active]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code(
                        "vpk.official.document.type"
                    )
                    or "type"
                )
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("code"):
            protected = self.filtered("is_system")
            if any(rec.code != vals["code"] for rec in protected):
                raise UserError(_("ไม่สามารถเปลี่ยนรหัสประเภทเอกสารของระบบ"))
        return super().write(vals)

    def unlink(self):
        if any(self.mapped("is_system")):
            raise UserError(_("ไม่สามารถลบประเภทเอกสารของระบบ ปิดการใช้งานแทนได้"))
        return super().unlink()
