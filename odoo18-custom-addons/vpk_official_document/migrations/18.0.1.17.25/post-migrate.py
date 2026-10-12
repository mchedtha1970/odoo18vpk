# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).


def migrate(cr, version):
    cr.execute(
        """
        UPDATE vpk_official_document_type
           SET create_from_purchase_request = TRUE
         WHERE code IN (
                'wa_committee_order',
                'spec_price_committee',
                'integrity_over_100k',
                'specific_method_approval'
            )
        """
    )
