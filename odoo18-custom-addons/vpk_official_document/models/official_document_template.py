# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class OfficialDocumentTemplate(models.Model):
    _name = "vpk.official.document.template"
    _description = "แบบฟอร์มหนังสือราชการ"
    _order = "sequence, id"

    name = fields.Char(string="ชื่อแบบฟอร์ม", required=True)
    code = fields.Char(string="รหัส", required=True, index=True)
    sequence = fields.Integer(default=10)
    document_type = fields.Selection(
        selection=[
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
        ],
        string="ประเภทเอกสาร",
        required=True,
        default="wa_committee_order",
    )
    datas = fields.Binary(string="ไฟล์ Word (.docx)", required=True, attachment=True)
    filename = fields.Char(string="ชื่อไฟล์")
    note = fields.Text(
        string="คำอธิบาย",
        default=(
            "ใช้แบบฟอร์มคำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ\n"
            "ระบบจะแทนที่หัวคำสั่ง เลขที่ เรื่อง ย่อหน้าแรก รายชื่อกรรมการ และผู้ลงนาม"
        ),
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "รหัสแบบฟอร์มต้องไม่ซ้ำในบริษัทเดียวกัน",
        ),
    ]
