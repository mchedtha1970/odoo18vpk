def migrate(cr, version):
    # Type records are noupdate, so set the flag on the existing ใบตรวจรับ type.
    cr.execute(
        """
        UPDATE vpk_official_document_type
           SET create_from_work_acceptance = TRUE
         WHERE code = 'inspection_report'
        """
    )
