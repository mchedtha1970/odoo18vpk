# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    vpk_hr_payroll_journal_id = fields.Many2one(
        "account.journal",
        string="สมุดรายวันเงินเดือน",
        domain="[('type', '=', 'general')]",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    vpk_hr_payroll_api_enabled = fields.Boolean(
        string="เปิดรับ API เงินเดือน",
        config_parameter="vpk_hr_payroll_api.enabled",
        default=True,
    )
    vpk_hr_payroll_api_key = fields.Char(
        string="HR API Key",
        config_parameter="vpk_hr_payroll_api.api_key",
    )
    vpk_hr_payroll_journal_id = fields.Many2one(
        related="company_id.vpk_hr_payroll_journal_id",
        readonly=False,
        string="สมุดรายวันเงินเดือน",
    )
