# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    contracts = env["purchase.contract"].search(
        [("quantity_policy", "=", "unlimited")]
    )
    contracts._release_source_bidding_budget()
    _logger.info(
        "Released price-agreement budget on %s unlimited contracts",
        len(contracts),
    )
