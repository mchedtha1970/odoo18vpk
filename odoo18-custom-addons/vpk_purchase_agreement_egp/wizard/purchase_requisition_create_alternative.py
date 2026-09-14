# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models


class PurchaseRequisitionCreateAlternative(models.TransientModel):
    _inherit = "purchase.requisition.create.alternative"

    def _get_alternative_values(self):
        vals = super()._get_alternative_values()
        origin_po = self.origin_po_id
        if origin_po.requisition_id:
            vals["requisition_id"] = origin_po.requisition_id.id
            vals["origin"] = origin_po.origin or origin_po.requisition_id._get_rfq_origin()
            vals["egp_bid_reference"] = origin_po.egp_bid_reference
        return vals
