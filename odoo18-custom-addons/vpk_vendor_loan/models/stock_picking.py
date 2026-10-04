# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    vpk_vendor_loan_id = fields.Many2one(
        "vpk.vendor.loan",
        string="ใบยืมจากผู้ขาย",
        copy=False,
        index=True,
    )

    def _check_receipt_qc_passed(self):
        if self.env.context.get("vpk_skip_loan_qc"):
            self = self.filtered(lambda picking: not picking.vpk_vendor_loan_id)
        return super()._check_receipt_qc_passed()

    def action_confirm(self):
        result = super().action_confirm()
        self._vpk_route_followup_receipt_to_loan()
        return result

    def _vpk_route_followup_receipt_to_loan(self):
        """ใบรับที่ซื้อตามหลังยืม ให้ปลายทางเป็นคลังยืม หักล้างจะเกิดในคลังนั้น"""
        for picking in self:
            destinations = self.env["stock.location"]
            routed = self.env["stock.move"]
            for move in picking.move_ids.filtered(lambda item: item.state not in ("done", "cancel")):
                location = move._vpk_loan_followup_location()
                if not location:
                    continue
                move.write({"location_dest_id": location.id})
                if move.move_line_ids:
                    move.move_line_ids.write({"location_dest_id": location.id})
                destinations |= location
                routed |= move
            if routed and destinations and routed == picking.move_ids.filtered(
                lambda item: item.state not in ("done", "cancel")
            ):
                picking.location_dest_id = destinations[:1].id

    def button_validate(self):
        self._vpk_route_followup_receipt_to_loan()
        loans = self.filtered("vpk_vendor_loan_id")
        others = self - loans
        result = True
        if others:
            result = super(StockPicking, others).button_validate()
        if loans:
            result = super(
                StockPicking, loans.with_context(skip_qc_wizard=True, vpk_skip_loan_qc=True)
            ).button_validate()
            if not isinstance(result, dict):
                loans.exists()._vpk_after_loan_receipt_validate()
        return result

    def _vpk_after_loan_receipt_validate(self):
        done = self.filtered(lambda picking: picking.state == "done" and picking.vpk_vendor_loan_id)
        done.mapped("vpk_vendor_loan_id")._vpk_mark_received_from_pickings()
