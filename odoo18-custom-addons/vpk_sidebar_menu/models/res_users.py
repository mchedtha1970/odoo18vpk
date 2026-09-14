# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    vpk_theme_config_id = fields.Many2one(
        'vpk.theme.config',
        string='VPK Theme Config',
        copy=False,
    )

    def _get_vpk_theme_config(self):
        self.ensure_one()
        if not self.vpk_theme_config_id:
            self.sudo().vpk_theme_config_id = self.env['vpk.theme.config'].sudo().create({})
        return self.vpk_theme_config_id
