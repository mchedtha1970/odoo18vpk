# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE purchase_requisition AS req
           SET purchase_request_id = pr.id
          FROM purchase_request AS pr
         WHERE req.purchase_request_id IS NULL
           AND req.reference IS NOT NULL
           AND req.reference = pr.name
           AND req.requisition_type = 'egp_procurement'
        """
    )
    _logger.info(
        "vpk_purchase_agreement_egp: linked %s agreements to purchase requests by reference",
        cr.rowcount,
    )
