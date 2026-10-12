# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).


def migrate(cr, version):
    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'purchase_request'
           AND column_name = 'official_document_to_create'
        """
    )
    row = cr.fetchone()
    if row and row[0] != "integer":
        cr.execute(
            "ALTER TABLE purchase_request DROP COLUMN official_document_to_create"
        )
