def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'vpk_stock_replenishment'
          AND name IN (
              'view_purchase_request_form_vpk_lot',
              'view_purchase_request_line_tree_vpk_lot'
          )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE name IN (
            'purchase.request.form.vpk.lot',
            'purchase.request.line.tree.vpk.lot'
        )
        """
    )
