# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models
from odoo.tools import SQL


class ProcurementVendorGroup(models.Model):
    _name = "procurement.vendor.group"
    _description = "กลุ่มผู้จำหน่ายจัดซื้อ"
    _order = "sequence, name, id"

    name = fields.Char(string="ชื่อกลุ่มผู้จำหน่าย", required=True)
    code = fields.Char(string="รหัสกลุ่ม", required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(string="รายละเอียด")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "procurement_vendor_group_code_unique",
            "unique(code)",
            "รหัสกลุ่มผู้จำหน่ายต้องไม่ซ้ำกัน",
        ),
    ]


class ResPartner(models.Model):
    _inherit = "res.partner"

    procurement_vendor_group_id = fields.Many2one(
        comodel_name="procurement.vendor.group",
        string="กลุ่มผู้จำหน่ายจัดซื้อ",
        index=True,
        tracking=True,
    )


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    procurement_vendor_group_id = fields.Many2one(
        comodel_name="procurement.vendor.group",
        string="กลุ่มผู้จำหน่ายจัดซื้อ",
        readonly=True,
    )

    def _select(self) -> SQL:
        return SQL(
            "%s, partner.procurement_vendor_group_id "
            "AS procurement_vendor_group_id",
            super()._select(),
        )

    def _group_by(self) -> SQL:
        return SQL(
            "%s, partner.procurement_vendor_group_id",
            super()._group_by(),
        )
