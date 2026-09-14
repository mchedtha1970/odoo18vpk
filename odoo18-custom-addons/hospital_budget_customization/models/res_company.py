from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    th_garuda_emblem = fields.Binary(
        string="Thai Garuda Emblem",
        attachment=True,
        help="ตราครุฑสำหรับเอกสารราชการ เช่น บันทึกข้อความ",
    )
