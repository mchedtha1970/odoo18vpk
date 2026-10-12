# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class VpkHrPayrollComponentMap(models.Model):
    _name = "vpk.hr.payroll.component.map"
    _description = "แมปรหัสเงินเดือน HR เข้าบัญชี"
    _order = "sequence, code"

    sequence = fields.Integer(default=10)
    code = fields.Char(string="รหัสจาก HR", required=True, index=True)
    name = fields.Char(string="ชื่อรายการ", required=True)
    side = fields.Selection(
        [("debit", "เดบิต"), ("credit", "เครดิต")],
        string="ด้านบัญชี",
        required=True,
        default="debit",
    )
    account_id = fields.Many2one(
        "account.account",
        string="บัญชี",
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "รหัสเงินเดือนซ้ำในบริษัทเดียวกัน",
        ),
    ]
