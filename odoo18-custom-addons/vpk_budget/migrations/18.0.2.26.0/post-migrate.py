def migrate(cr, version):
    cr.execute(
        """
        UPDATE purchase_request
           SET budget_reservation_active = TRUE
         WHERE budget_reservation_active IS NOT TRUE
           AND (
                state IN ('to_approve', 'approved', 'in_progress')
                OR (
                    state = 'draft'
                    AND validation_status IN ('waiting', 'pending', 'validated')
                )
           )
        """
    )
