def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'vpk_tier_validation'
         WHERE module = 'vpk_official_document'
           AND name = 'user_director_secretary'
           AND NOT EXISTS (
               SELECT 1 FROM ir_model_data
                WHERE module = 'vpk_tier_validation'
                  AND name = 'user_director_secretary'
           )
        """
    )
