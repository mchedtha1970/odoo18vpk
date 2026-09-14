"""Initialize sequence for existing e-GP document lines."""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT id
          FROM purchase_requisition_egp_document
         ORDER BY requisition_id, id
        """
    )
    rows = cr.fetchall()
    if not rows:
        return

    current_requisition_id = None
    sequence = 0
    for (record_id,) in rows:
        cr.execute(
            """
            SELECT requisition_id
              FROM purchase_requisition_egp_document
             WHERE id = %s
            """,
            (record_id,),
        )
        requisition_id = cr.fetchone()[0]
        if requisition_id != current_requisition_id:
            current_requisition_id = requisition_id
            sequence = 0
        sequence += 10
        cr.execute(
            """
            UPDATE purchase_requisition_egp_document
               SET sequence = %s
             WHERE id = %s
            """,
            (sequence, record_id),
        )
    _logger.info(
        "vpk_purchase_agreement_egp: initialized sequence on %s document lines",
        len(rows),
    )
