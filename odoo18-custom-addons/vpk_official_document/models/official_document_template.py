# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class OfficialDocumentTemplate(models.Model):
    _name = "vpk.official.document.template"
    _description = "แบบฟอร์มหนังสือราชการ"
    _order = "sequence, id"

    name = fields.Char(string="ชื่อแบบฟอร์ม", required=True)
    code = fields.Char(string="รหัส", required=True, index=True)
    sequence = fields.Integer(default=10)
    document_type = fields.Selection(
        selection="_selection_document_type",
        string="ประเภทเอกสาร",
        required=True,
        default="wa_committee_order",
    )

    @api.model
    def _selection_document_type(self):
        return self.env["vpk.official.document.type"].selection_pairs()
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
