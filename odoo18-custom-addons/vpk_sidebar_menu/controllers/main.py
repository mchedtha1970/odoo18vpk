# -*- coding: utf-8 -*-
from odoo import _, http
from odoo.exceptions import AccessError
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
    'sidebar_bg_style',
    'sidebar_bg_top',
    'sidebar_bg_bottom',
    'font_family',
    'font_size',
    'loader_style',
    'badge_style',
    'sidebar_width',
    'sidebar_collapsed_width',
]


class VpkThemeController(http.Controller):

    @http.route('/vpk/theme/config', type='json', auth='user')
    def get_theme_config(self):
        config = request.env['vpk.theme.config'].sudo()._get_global_config()
        return config._to_dict()

    @http.route('/vpk/theme/config/save', type='json', auth='user')
    def save_theme_config(self, **kwargs):
        if not request.env.user.has_group('base.group_system'):
            raise AccessError(_("Only System Administrators can change the theme."))
        config = request.env['vpk.theme.config']._get_global_config()
        values = {key: kwargs[key] for key in CONFIG_FIELDS if key in kwargs}
        config.write(values)
        return config._to_dict()
