# -*- coding: utf-8 -*-
from odoo import api, fields, models

FONT_FAMILY_CSS = {
    "default": "",
    "kanit": "'Kanit', sans-serif",
    "sarabun": "'Sarabun', sans-serif",
    "prompt": "'Prompt', sans-serif",
    "roboto": "'Roboto', sans-serif",
}

FONT_SIZE_MD = {
    "small": "10px",
    "medium": "12px",
    "large": "15px",
}

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Kanit:wght@300;400;500;600;700&"
    "family=Prompt:wght@300;400;500;600;700&"
    "family=Roboto:wght@300;400;500;700&"
    "family=Sarabun:wght@300;400;500;600;700&"
    "display=swap"
)


class VpkThemeConfig(models.Model):
    _name = "vpk.theme.config"
    _description = "VPK Sidebar Theme Configuration"

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

    sidebar_color = fields.Char(default="#00a884")
    sidebar_active_color = fields.Char(default="#063a32")
    sidebar_text_color = fields.Char(default="#ffffff")

    font_family = fields.Selection(
        selection=[
            ("default", "Default"),
            ("kanit", "Kanit"),
            ("sarabun", "Sarabun"),
            ("prompt", "Prompt"),
            ("roboto", "Roboto"),
        ],
        default="default",
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
    sidebar_width = fields.Integer(default=288)
    sidebar_collapsed_width = fields.Integer(default=72)

    @staticmethod
    def _clamp_sidebar_vals(vals):
        if "sidebar_width" in vals:
            vals["sidebar_width"] = min(420, max(200, int(vals["sidebar_width"] or 288)))
        if "sidebar_collapsed_width" in vals:
            vals["sidebar_collapsed_width"] = min(
                120, max(56, int(vals["sidebar_collapsed_width"] or 72))
            )
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._clamp_sidebar_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._clamp_sidebar_vals(vals)
        res = super().write(vals)
        if any(key in vals for key in ("font_family", "font_size")):
            for config in self:
                config._sync_portal_font_params()
        return res

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
            "font_family": self.font_family,
            "font_size": self.font_size,
            "loader_style": self.loader_style,
            "sidebar_width": self.sidebar_width,
            "sidebar_collapsed_width": self.sidebar_collapsed_width,
        }

    def _sync_portal_font_params(self):
        """Keep portal font in sync with the saved backend theme font."""
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("vpk.portal.font_family", self.font_family or "default")
        ICP.set_param("vpk.portal.font_size", self.font_size or "medium")

    @api.model
    def _get_portal_font_settings(self):
        """Font settings for portal / login pages (same as backend theme)."""
        ICP = self.env["ir.config_parameter"].sudo()
        font_family = ICP.get_param("vpk.portal.font_family")
        font_size = ICP.get_param("vpk.portal.font_size")
        if not font_family or not font_size:
            config = self.sudo().search([], order="write_date desc", limit=1)
            if config:
                font_family = font_family or config.font_family
                font_size = font_size or config.font_size
                config._sync_portal_font_params()
        font_family = font_family or "default"
        font_size = font_size or "medium"
        font_css = FONT_FAMILY_CSS.get(font_family) or ""
        return {
            "font_family": font_family,
            "font_size": font_size,
            "font_family_css": font_css or "inherit",
            "font_size_md": FONT_SIZE_MD.get(font_size, "12px"),
            "load_google_fonts": bool(font_css),
            "google_fonts_url": GOOGLE_FONTS_URL if font_css else "",
        }
