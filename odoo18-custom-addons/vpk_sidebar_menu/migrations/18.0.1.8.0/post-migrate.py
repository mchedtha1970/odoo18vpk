from odoo import SUPERUSER_ID, api

THEME_FIELDS = [
    "theme_style",
    "menu_position",
    "chatter_position",
    "tree_form_split_view",
    "list_view_density",
    "list_view_sticky_header",
    "sidebar_color",
    "sidebar_active_color",
    "sidebar_text_color",
    "font_family",
    "font_size",
    "loader_style",
    "sidebar_width",
    "sidebar_collapsed_width",
]


def _pick_source_config(cr, global_id):
    """Admin's per-user theme if any, otherwise the most recently saved one."""
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'res_users' AND column_name = 'vpk_theme_config_id'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            SELECT u.vpk_theme_config_id
            FROM res_users u
            JOIN ir_model_data d
              ON d.res_id = u.id AND d.model = 'res.users'
             AND d.module = 'base' AND d.name = 'user_admin'
            WHERE u.vpk_theme_config_id IS NOT NULL AND u.vpk_theme_config_id != %s
            """,
            [global_id],
        )
        row = cr.fetchone()
        if row:
            return row[0]
    cr.execute(
        "SELECT id FROM vpk_theme_config WHERE id != %s ORDER BY write_date DESC NULLS LAST LIMIT 1",
        [global_id],
    )
    row = cr.fetchone()
    return row[0] if row else None


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    global_config = env.ref("vpk_sidebar_menu.vpk_theme_config_global")
    source_id = _pick_source_config(cr, global_config.id)
    if source_id:
        source = env["vpk.theme.config"].browse(source_id)
        global_config.write({name: source[name] for name in THEME_FIELDS})

    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'res_users' AND column_name = 'vpk_theme_config_id'
        """
    )
    if cr.fetchone():
        cr.execute("UPDATE res_users SET vpk_theme_config_id = NULL")
    env["vpk.theme.config"].search([("id", "!=", global_config.id)]).unlink()
    env["ir.config_parameter"].search(
        [("key", "in", ["vpk.portal.font_family", "vpk.portal.font_size"])]
    ).unlink()
