def migrate(cr, version):
    """Bind existing รายงานผลการพิจารณาจัดซื้อจัดจ้าง type to the module XML id."""
    cr.execute(
        """
        SELECT id FROM purchase_requisition_egp_document_type
        WHERE code = 'consider_procurement'
        LIMIT 1
        """
    )
    row = cr.fetchone()
    if not row:
        return
    cr.execute(
        """
        SELECT id FROM ir_model_data
        WHERE module = 'vpk_purchase_agreement_egp'
          AND name = 'egp_document_type_consider_procurement'
        LIMIT 1
        """
    )
    if cr.fetchone():
        return
    cr.execute(
        """
        INSERT INTO ir_model_data
            (module, name, model, res_id, noupdate)
        VALUES
            (
                'vpk_purchase_agreement_egp',
                'egp_document_type_consider_procurement',
                'purchase.requisition.egp.document.type',
                %s,
                false
            )
        """,
        (row[0],),
    )
