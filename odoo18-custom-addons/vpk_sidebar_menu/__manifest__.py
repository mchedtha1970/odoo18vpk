# -*- coding: utf-8 -*-
{
    'name': 'VPK Sidebar App Menu',
    'version': '18.0.1.7.67',
    'category': 'Tools',
    'summary': 'Replace standard Odoo app menu with vertical sidebar navigation',
    'description': """
        Transforms the standard Odoo 18 top app menu into a vertical sidebar
        with company logo, user profile, quick action icons, theme settings panel,
        app list with nested sub-menus.
    """,
    'author': 'VPK',
    'depends': ['web', 'mail', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_asset.xml',
        'data/ir_asset_layout.xml',
        'views/portal_theme_font_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vpk_sidebar_menu/static/src/scss/remixicon.scss',
            'vpk_sidebar_menu/static/src/scss/font_icons.scss',
            'vpk_sidebar_menu/static/src/scss/sidebar_menu.scss',
            'vpk_sidebar_menu/static/src/scss/form_chatter.scss',
            'vpk_sidebar_menu/static/src/scss/theme_config_panel.scss',
            'vpk_sidebar_menu/static/src/scss/list_view_theme.scss',
            'vpk_sidebar_menu/static/src/scss/dialog_theme.scss',
            'vpk_sidebar_menu/static/src/js/theme_utils.js',
            'vpk_sidebar_menu/static/src/scss/tinymce_html_field.scss',
            'vpk_sidebar_menu/static/src/xml/tinymce_html_field.xml',
            'vpk_sidebar_menu/static/src/js/tinymce_html_field.js',
            'vpk_sidebar_menu/static/src/js/text_field_patch.js',
            'vpk_sidebar_menu/static/src/js/layout_utils.js',
            'vpk_sidebar_menu/static/src/js/form_layout_patch.js',
            'vpk_sidebar_menu/static/src/js/form_dropdown_patch.js',
            'vpk_sidebar_menu/static/src/js/theme_config_panel.js',
            'vpk_sidebar_menu/static/src/js/sidebar_menu.js',
            'vpk_sidebar_menu/static/src/xml/theme_config_panel.xml',
            'vpk_sidebar_menu/static/src/xml/dialog_inherit.xml',
            'vpk_sidebar_menu/static/src/xml/sidebar_menu.xml',
            'vpk_sidebar_menu/static/src/xml/systray_inherit.xml',
        ],
        'web.assets_frontend': [
            'vpk_sidebar_menu/static/src/scss/portal_theme_font.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
