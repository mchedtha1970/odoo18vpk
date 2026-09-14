# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

CONFIG_FIELDS = [
    'theme_style',
    'menu_position',
    'chatter_position',
    'tree_form_split_view',
    'list_view_density',
    'list_view_sticky_header',
    'sidebar_color',
    'sidebar_active_color',
    'sidebar_text_color',
    'font_family',
    'font_size',
    'loader_style',
    'sidebar_width',
    'sidebar_collapsed_width',
]


class VpkThemeController(http.Controller):

    @http.route('/vpk/theme/config', type='json', auth='user')
    def get_theme_config(self):
        config = request.env.user._get_vpk_theme_config()
        return config._to_dict()

    @http.route('/vpk/theme/config/save', type='json', auth='user')
    def save_theme_config(self, **kwargs):
        config = request.env.user._get_vpk_theme_config()
        values = {key: kwargs[key] for key in CONFIG_FIELDS if key in kwargs}
        config.sudo().write(values)
        config._sync_portal_font_params()
        return config._to_dict()
