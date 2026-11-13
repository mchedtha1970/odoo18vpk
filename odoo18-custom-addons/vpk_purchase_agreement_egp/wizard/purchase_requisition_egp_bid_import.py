# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseRequisitionEgpBidImportWizard(models.TransientModel):
    _name = "purchase.requisition.egp.bid.import.wizard"
    _description = "ดึงผู้ขายและรายการสินค้าในแผนเข้าตารางพิจารณา"

    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ e-GP",
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ชื่อผู้ขาย",
        domain="[('supplier_rank', '>', 0)]",
        context={"res_partner_search_mode": "supplier"},
    )
    line_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.bid.import.wizard.line",
        inverse_name="wizard_id",
        string="รายการสินค้าในแผน",
    )

    def action_confirm(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_("กรุณาเลือกชื่อผู้ขาย"))
        selected = self.line_ids.filtered("selected")
        if not selected:
            raise UserError(_("กรุณาเลือกรายการสินค้าในแผนอย่างน้อย 1 รายการ"))
        existing_products = set(
            self.requisition_id.egp_bid_line_ids.filtered(
                lambda line: line.partner_id == partner
            ).mapped("product_id").ids
        )
        BidLine = self.env["purchase.requisition.egp.bid.line"].with_context(
            default_requisition_id=self.requisition_id.id
        )
        vals_list = []
        for line in selected:
            if not line.product_id or line.product_id.id in existing_products:
                continue
            vals_list.append(
                {
                    "requisition_id": self.requisition_id.id,
                    "partner_id": partner.id,
                    "requisition_line_id": line.requisition_line_id.id,
                    "product_id": line.product_id.id,
                    "name": line.name,
                    "product_qty": line.product_qty,
                    "product_uom_id": line.product_uom_id.id,
                }
            )
        if not vals_list:
            raise UserError(_("ผู้ขายรายนี้มีรายการสินค้าที่เลือกอยู่ในตารางแล้ว"))
        BidLine.create(vals_list)
        return {"type": "ir.actions.act_window_close"}


class PurchaseRequisitionEgpBidImportWizardLine(models.TransientModel):
    _name = "purchase.requisition.egp.bid.import.wizard.line"
    _description = "รายการสินค้าในแผนสำหรับดึงเข้าตารางพิจารณา"

    wizard_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.bid.import.wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="เลือก", default=True)
    requisition_line_id = fields.Many2one(
        comodel_name="purchase.requisition.line",
        string="บรรทัดแผน",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า",
        readonly=True,
    )
    name = fields.Text(string="รายการ", readonly=True)
    product_qty = fields.Float(
        string="ปริมาณ",
        digits="Product Unit of Measure",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วย",
        readonly=True,
    )
