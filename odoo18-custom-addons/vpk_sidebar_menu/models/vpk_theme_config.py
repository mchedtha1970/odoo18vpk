# -*- coding: utf-8 -*-
from odoo import api, fields, models

FONT_FAMILY_CSS = {
    "default": "",
    "inter": "'Inter', 'Noto Sans Thai', sans-serif",
    "ibm_plex_thai": "'IBM Plex Sans Thai', sans-serif",
    "anuphan": "'Anuphan', sans-serif",
    "kanit": "'Kanit', sans-serif",
    "sarabun": "'Sarabun', sans-serif",
    "prompt": "'Prompt', sans-serif",
    "roboto": "'Roboto', sans-serif",
}

FONT_SIZE_MD = {
    "small": "12px",
    "medium": "13px",
    "large": "14px",
}

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700&"
    "family=Noto+Sans+Thai:wght@400;500;600;700&"
    "family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&"
    "family=Anuphan:wght@300;400;500;600;700&"
    "family=Kanit:wght@300;400;500;600;700&"
    "family=Prompt:wght@300;400;500;600;700&"
    "family=Roboto:wght@300;400;500;700&"
    "family=Sarabun:wght@300;400;500;600;700&"
    "display=swap"
)


class VpkThemeConfig(models.Model):
    _name = "vpk.theme.config"
    _description = "VPK Global Theme Configuration"

    name = fields.Char(default="Theme Config")

    theme_style = fields.Selection(
        selection=[
            ("rounded", "Rounded"),
            ("standard", "Standard"),
            ("square", "Square"),
        ],
        default="rounded",
        required=True,
    )
    menu_position = fields.Selection(
        selection=[
            ("vertical", "Vertical Sidebar"),
            ("horizontal", "Horizontal Top Menu"),
        ],
        default="vertical",
        required=True,
    )
    chatter_position = fields.Selection(
        selection=[
            ("right", "Right"),
            ("bottom", "Bottom"),
        ],
        default="bottom",
        required=True,
    )
    tree_form_split_view = fields.Boolean(default=False)
    list_view_density = fields.Selection(
        selection=[
            ("comfortable", "Comfortable"),
            ("compact", "Compact"),
        ],
        default="comfortable",
        required=True,
    )
    list_view_sticky_header = fields.Boolean(default=False)

    sidebar_color = fields.Char(string="Primary Color", default="#2563eb")
    sidebar_active_color = fields.Char(string="Primary Hover Color", default="#1d4ed8")
    sidebar_text_color = fields.Char(string="Text on Primary", default="#ffffff")
    sidebar_bg_style = fields.Selection(
        selection=[
            ("light", "Light"),
            ("gradient", "Gradient"),
        ],
        default="light",
        required=True,
    )
    sidebar_bg_top = fields.Char(string="Sidebar Gradient Top", default="#15803d")
    sidebar_bg_bottom = fields.Char(string="Sidebar Gradient Bottom", default="#14532d")

    font_family = fields.Selection(
        selection=[
            ("default", "Default"),
            ("inter", "Inter"),
            ("ibm_plex_thai", "IBM Plex Sans Thai"),
            ("anuphan", "Anuphan"),
            ("kanit", "Kanit"),
            ("sarabun", "Sarabun"),
            ("prompt", "Prompt"),
            ("roboto", "Roboto"),
        ],
        default="inter",
        required=True,
    )
    font_size = fields.Selection(
        selection=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        default="medium",
        required=True,
    )
    loader_style = fields.Selection(
        selection=[
            ("default", "Default"),
            ("dots", "Dots"),
            ("bars", "Bars"),
        ],
        default="default",
        required=True,
    )
    badge_style = fields.Selection(
        selection=[
            ("pill", "Pill"),
            ("rounded", "Rounded"),
            ("square", "Square"),
        ],
        default="pill",
        required=True,
    )
    sidebar_width = fields.Integer(default=256)
    sidebar_collapsed_width = fields.Integer(default=80)

    @staticmethod
    def _clamp_sidebar_vals(vals):
        if "sidebar_width" in vals:
            vals["sidebar_width"] = min(420, max(200, int(vals["sidebar_width"] or 256)))
        if "sidebar_collapsed_width" in vals:
            vals["sidebar_collapsed_width"] = min(
                120, max(56, int(vals["sidebar_collapsed_width"] or 80))
            )
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._clamp_sidebar_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._clamp_sidebar_vals(vals)
        return super().write(vals)

    @api.model
    def _get_global_config(self):
        """The single theme shared by every user; only System Admin may write it."""
        config = self.env.ref(
            "vpk_sidebar_menu.vpk_theme_config_global", raise_if_not_found=False
        )
        if not config:
            config = self.sudo().search([], order="id", limit=1) or self.sudo().create(
                {"name": "Global Theme"}
            )
        return config

    def _to_dict(self):
        self.ensure_one()
        return {
            "theme_style": self.theme_style,
            "menu_position": self.menu_position,
            "chatter_position": self.chatter_position,
            "tree_form_split_view": self.tree_form_split_view,
            "list_view_density": self.list_view_density,
            "list_view_sticky_header": self.list_view_sticky_header,
            "sidebar_color": self.sidebar_color,
            "sidebar_active_color": self.sidebar_active_color,
            "sidebar_text_color": self.sidebar_text_color,
            "sidebar_bg_style": self.sidebar_bg_style,
            "sidebar_bg_top": self.sidebar_bg_top,
            "sidebar_bg_bottom": self.sidebar_bg_bottom,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "loader_style": self.loader_style,
            "badge_style": self.badge_style,
            "sidebar_width": self.sidebar_width,
            "sidebar_collapsed_width": self.sidebar_collapsed_width,
        }

    @api.model
    def _get_portal_font_settings(self):
        """Font settings for portal / login pages (same as backend theme)."""
        config = self.sudo()._get_global_config()
        font_family = config.font_family or "default"
        font_size = config.font_size or "medium"
        font_css = FONT_FAMILY_CSS.get(font_family) or ""
        return {
            "font_family": font_family,
            "font_size": font_size,
            "font_family_css": font_css or "inherit",
            "font_size_md": FONT_SIZE_MD.get(font_size, "12px"),
            "load_google_fonts": bool(font_css),
            "google_fonts_url": GOOGLE_FONTS_URL if font_css else "",
        }
