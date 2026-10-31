# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, fields, models


class PurchaseContract(models.Model):
    _inherit = "purchase.contract"

    contract_document_ids = fields.One2many(
        comodel_name="purchase.contract.document",
        inverse_name="contract_id",
        string="รายการเอกสารสัญญา",
    )

    def action_open_add_contract_document_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เพิ่มเอกสาร"),
            "res_model": "vpk.contract.document.add.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_contract_id": self.id},
        }
