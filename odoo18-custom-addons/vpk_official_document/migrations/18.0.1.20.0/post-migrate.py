def migrate(cr, version):
    cr.execute(
        """
        UPDATE vpk_official_document_type
           SET create_from_purchase_request = TRUE
         WHERE code = 'purchase_approval_memo'
        """
    )
