from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["vpk.theme.config"]._get_global_config().write({"sidebar_bg_style": "gradient"})
