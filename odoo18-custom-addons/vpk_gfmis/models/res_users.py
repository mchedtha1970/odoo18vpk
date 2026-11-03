# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _vpk_setup_gfmis_test_user(self):
        user = self.env.ref("vpk_gfmis.user_uat_gfmis", raise_if_not_found=False)
        if not user:
            user = self.sudo().search([("login", "=", "uat.gfmis")], limit=1)
        if not user:
            return
        password = self.env["ir.config_parameter"].sudo().get_param(
            "vpk_login_page.test_users_password"
        )
        vals = {
            "lang": "th_TH",
            "tz": "Asia/Bangkok",
        }
        if password:
            vals["password"] = password
        group_xmlids = [
            "account.group_account_user",
            "account.group_account_manager",
            "analytic.group_analytic_accounting",
            "base_accounting_kit.group_account_dashboard",
            "vpk_gfmis.group_gfmis_manager",
        ]
        group_commands = []
        for xmlid in group_xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                group_commands.append((4, group.id))
        if group_commands:
            vals["groups_id"] = group_commands
        user.sudo().with_context(no_reset_password=True).write(vals)
