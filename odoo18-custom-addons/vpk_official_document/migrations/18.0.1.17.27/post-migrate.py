def migrate(cr, version):
    cr.execute(
        """
        UPDATE vpk_official_document_signer
           SET is_sign = TRUE
         WHERE COALESCE(is_check, FALSE) = FALSE
           AND COALESCE(is_sign, FALSE) = FALSE
        """
    )
