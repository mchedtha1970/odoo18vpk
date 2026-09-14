# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    purchase_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ/จ้าง/เช่า",
        compute="_compute_po_tracking",
    )
    has_po = fields.Boolean(
        string="ออกใบสั่งซื้อแล้ว",
        compute="_compute_po_tracking",
        store=True,
        index=True,
        help="มีใบสั่งซื้อ/จ้าง/เช่าที่เชื่อมกับรายการใน PR นี้แล้ว",
    )
    po_issued_status = fields.Selection(
        selection=[
            ("not_issued", "ยังไม่ออกใบสั่งซื้อ/จ้าง/เช่า"),
            ("partial", "ออกบางส่วน"),
            ("issued", "ออกใบสั่งซื้อ/จ้าง/เช่าแล้ว"),
        ],
        string="สถานะการออกใบสั่งซื้อ",
        compute="_compute_po_tracking",
        store=True,
        index=True,
    )
    confirmed_po_count = fields.Integer(
        string="จำนวน PO ยืนยันแล้ว",
        compute="_compute_po_tracking",
        store=True,
    )

    @api.model
    def _vpk_configure_pr_sequence(self):
        """เลข PR = PR + ปี พ.ศ. 2 หลัก + เดือน 2 หลัก + running 3 หลัก เช่น PR6908001"""
        sequences = self.env["ir.sequence"].search([("code", "=", "purchase.request")])
        main = self.env.ref(
            "purchase_request.seq_purchase_request", raise_if_not_found=False
        )
        if main:
            sequences |= main
        if "purchase.request.type" in self.env:
            sequences |= self.env["purchase.request.type"].search([]).mapped(
                "sequence_id"
            )
        prefix = "PR%(y_be)s%(month)s"
        for seq in sequences:
            changed = seq.prefix != prefix or seq.padding != 3 or not seq.use_date_range
            vals = {
                "prefix": prefix,
                "suffix": False,
                "padding": 3,
                "use_date_range": True,
                "number_increment": 1,
            }
            if "range_reset" in seq._fields:
                vals["range_reset"] = "monthly"
                changed = changed or seq.range_reset != "monthly"
            if changed:
                vals["number_next"] = 1
            seq.write(vals)
            if changed:
                seq.date_range_ids.unlink()

    @api.depends(
        "line_ids.purchase_lines",
        "line_ids.purchase_lines.order_id",
        "line_ids.purchase_lines.order_id.state",
        "line_ids.cancelled",
    )
    def _compute_po_tracking(self):
        for request in self:
            active_lines = request.line_ids.filtered(lambda line: not line.cancelled)
            orders = active_lines.mapped("purchase_lines.order_id")
            request.purchase_order_ids = orders
            request.has_po = bool(orders)
            confirmed = orders.filtered(lambda po: po.state in ("purchase", "done"))
            request.confirmed_po_count = len(confirmed)
            if not active_lines:
                request.po_issued_status = "not_issued"
                continue
            lines_with_po = active_lines.filtered("purchase_lines")
            if not lines_with_po:
                request.po_issued_status = "not_issued"
            elif len(lines_with_po) == len(active_lines):
                request.po_issued_status = "issued"
            else:
                request.po_issued_status = "partial"
