def migrate(cr, version):
    cr.execute(
        """
        UPDATE vpk_theme_config
        SET sidebar_width = 288
        WHERE sidebar_width = 240
        """
    )
