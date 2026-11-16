# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_voucher_ids = fields.Many2many(
        comodel_name="vpk.payment.voucher",
        relation="vpk_payment_voucher_bill_rel",
        column1="move_id",
        column2="voucher_id",
        string="ใบสำคัญจ่าย",
        copy=False,
    )
    payment_voucher_count = fields.Integer(
        string="จำนวนใบสำคัญจ่าย",
        compute="_compute_payment_voucher_count",
    )

    @api.depends("payment_voucher_ids")
    def _compute_payment_voucher_count(self):
        for move in self:
            move.payment_voucher_count = len(
                move.payment_voucher_ids.filtered(lambda v: v.state != "cancel")
            )

    def action_view_payment_vouchers(self):
        """เปิดใบสำคัญจ่ายที่เชื่อมโยงกับใบตั้งเจ้าหนี้นี้."""
        self.ensure_one()
        vouchers = self.payment_voucher_ids.filtered(lambda v: v.state != "cancel")
        if not vouchers:
            return self.action_create_payment_voucher()
        if len(vouchers) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("ใบสำคัญจ่าย"),
                "res_model": "vpk.payment.voucher",
                "res_id": vouchers.id,
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบสำคัญจ่าย"),
            "res_model": "vpk.payment.voucher",
            "view_mode": "list,form",
            "domain": [("id", "in", vouchers.ids)],
        }

    def action_create_payment_voucher(self):
        """สร้างใบสำคัญจ่ายจากใบตั้งเจ้าหนี้ที่เลือก (ต้องผ่านการอนุมัติและ POST แล้วเท่านั้น)."""
        bills = self.filtered(
            lambda move: move.move_type == "in_invoice" and move.state == "posted"
        )
        if not bills:
            raise UserError(
                _(
                    "ก่อนทำใบสำคัญจ่าย ต้องมีการตั้งเจ้าหนี้ที่ผ่านการอนุมัติและ POST แล้วเท่านั้น"
                )
            )
        if len(bills) > 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("สร้างใบสำคัญจ่าย (รวมหลายใบตั้งหนี้)"),
                "res_model": "vpk.payment.voucher.create.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "active_model": "account.move",
                    "active_ids": bills.ids,
                },
            }
        existing = self.env["vpk.payment.voucher"].sudo().search(
            [
                ("bill_ids", "in", bills.ids),
                ("state", "!=", "cancel"),
            ],
            order="id desc",
            limit=1,
        )
        voucher = existing or self.env["vpk.payment.voucher"].create_from_bills(bills)
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบสำคัญจ่าย"),
            "res_model": "vpk.payment.voucher",
            "res_id": voucher.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
