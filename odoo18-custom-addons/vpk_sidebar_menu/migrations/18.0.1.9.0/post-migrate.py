from odoo import SUPERUSER_ID, api

MODERN_DEFAULTS = {
    "theme_style": "rounded",
    "sidebar_color": "#2563eb",
    "sidebar_active_color": "#1d4ed8",
    "sidebar_text_color": "#ffffff",
    "font_family": "inter",
    "font_size": "medium",
    "sidebar_width": 256,
    "sidebar_collapsed_width": 80,
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["vpk.theme.config"]._get_global_config().write(MODERN_DEFAULTS)
