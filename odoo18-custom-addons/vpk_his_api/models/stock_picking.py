# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        res = super()._action_done()
        self._vpk_his_close_requisition_batches()
        return res

    def _vpk_his_close_requisition_batches(self):
        """Mark the HIS request posted only after every transfer step is done."""
        batches = self.env["vpk.his.batch"].sudo().search(
            [
                ("batch_type", "=", "stock_requisition"),
                ("state", "=", "ready"),
                ("picking_ids", "in", self.ids),
            ]
        )
        for batch in batches:
            pending = batch.picking_ids.filtered(
                lambda picking: picking.state not in ("done", "cancel")
            )
            done = batch.picking_ids.filtered(lambda picking: picking.state == "done")
            if done and not pending:
                batch.state = "posted"
                batch.message_post(body=_("โอนสินค้าจากคำขอ HIS ครบทุกขั้นตอนแล้ว"))
