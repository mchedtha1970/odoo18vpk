def migrate(cr, version):
    cr.execute(
        """
        UPDATE vpk_approval_line
           SET is_sign = TRUE
         WHERE COALESCE(is_check, FALSE) = FALSE
           AND COALESCE(is_sign, FALSE) = FALSE
        """
    )
