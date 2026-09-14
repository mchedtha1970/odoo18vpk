"""Clean legacy e-GP document fields before model/view reload."""

import logging

_logger = logging.getLogger(__name__)


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (table_name,))
    return bool(cr.fetchone()[0])


def _column_exists(cr, table_name, column_name):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        (table_name, column_name),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if not _table_exists(cr, "purchase_requisition_egp_document"):
        return

    if (
        _column_exists(cr, "purchase_requisition_egp_document", "document_type")
        and _table_exists(cr, "purchase_requisition_egp_document_type")
        and _column_exists(cr, "purchase_requisition_egp_document", "document_type_id")
    ):
        cr.execute(
            """
            UPDATE purchase_requisition_egp_document AS doc
               SET document_type_id = typ.id
              FROM purchase_requisition_egp_document_type AS typ
             WHERE doc.document_type = typ.code
               AND doc.document_type_id IS NULL
            """
        )

    if _column_exists(cr, "purchase_requisition_egp_document", "document_type"):
        cr.execute(
            """
            ALTER TABLE purchase_requisition_egp_document
            DROP COLUMN document_type
            """
        )

    if _column_exists(cr, "purchase_requisition_egp_document", "name"):
        cr.execute(
            """
            ALTER TABLE purchase_requisition_egp_document
            DROP COLUMN name
            """
        )

    cr.execute(
        """
        DELETE FROM ir_model_fields
         WHERE model = 'purchase.requisition.egp.document'
           AND name IN ('document_type', 'name')
        """
    )
    _logger.info("vpk_purchase_agreement_egp: legacy e-GP document fields cleaned")
