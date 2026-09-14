def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE name IN (
            'purchase.request.form.vpk.lot',
            'purchase.request.line.tree.vpk.lot'
        )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data imd
        USING ir_model_fields imf
        WHERE imd.model = 'ir.model.fields'
          AND imd.res_id = imf.id
          AND imf.model = 'purchase.request.line'
          AND imf.name = 'lot_id'
          AND imd.module = 'vpk_tier_validation'
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_fields
        WHERE model = 'purchase.request.line'
          AND name = 'lot_id'
        """
    )
    cr.execute(
        """
        ALTER TABLE purchase_request_line
        DROP COLUMN IF EXISTS lot_id
        """
    )
