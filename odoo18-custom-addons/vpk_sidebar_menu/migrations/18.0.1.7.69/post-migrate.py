def migrate(cr, version):
    cr.execute(
        """
        UPDATE vpk_theme_config
        SET sidebar_width = ROUND(sidebar_width * 0.9)::int
        WHERE sidebar_width IS NOT NULL
        """
    )
