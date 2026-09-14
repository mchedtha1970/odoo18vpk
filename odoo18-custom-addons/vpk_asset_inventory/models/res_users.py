# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    asset_inventory_analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="res_users_asset_inventory_analytic_rel",
        column1="user_id",
        column2="analytic_account_id",
        string="หน่วยงานตรวจนับทรัพย์สิน",
        help="หน่วยงานที่ผู้ใช้นี้รับผิดชอบตรวจนับผ่าน Portal",
    )
