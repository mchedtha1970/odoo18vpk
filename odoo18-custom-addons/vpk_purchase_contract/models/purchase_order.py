# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="รหัสสัญญาอ้างอิง",
        tracking=True,
        index=True,
        copy=False,
        domain="[('state', '=', 'confirmed'), ('company_id', 'in', [company_id, False])]",
    )
    contract_amount_remaining = fields.Monetary(
        related="contract_id.amount_remaining",
        string="มูลค่าคงเหลือสัญญา",
        readonly=True,
        currency_field="currency_id",
    )
    contract_type_id = fields.Many2one(
        related="contract_id.contract_type_id",
        string="ประเภทสัญญา",
    )
    contract_quantity_policy = fields.Selection(
        related="contract_id.quantity_policy",
        string="ลักษณะปริมาณ",
    )
    contract_category_id = fields.Many2one(
        related="contract_id.contract_category_id",
        string="หมวดสัญญา",
    )
    contract_egp_control_no = fields.Char(
        related="contract_id.egp_contract_control_no",
        string="เลขคุมสัญญาในระบบ e-GP",
    )
    contract_po_number = fields.Char(
        related="contract_id.contract_po_number",
        string="เลขที่สัญญา / ใบสั่งซื้อ",
    )
    source_project_reference = fields.Char(
        string="เลขที่โครงการ",
        compute="_compute_source_documents",
    )
    source_project_name = fields.Char(
        string="ชื่อโครงการ",
        compute="_compute_source_documents",
    )
    source_requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="การจัดซื้อ",
        compute="_compute_source_documents",
    )
    source_request_ids = fields.Many2many(
        comodel_name="purchase.request",
        string="เลข PR",
        compute="_compute_source_documents",
    )

    @api.depends(
        "contract_id",
        "contract_id.egp_reference",
        "contract_id.requisition_id",
        "contract_id.requisition_id.egp_reference",
        "contract_id.requisition_id.egp_project_name",
        "requisition_id",
        "requisition_id.egp_reference",
        "requisition_id.egp_project_name",
        "order_line.purchase_request_lines.request_id",
        "order_line.purchase_request_lines.request_id.egp_project_reference",
        "order_line.purchase_request_lines.request_id.egp_project_name",
        "order_line.purchase_request_lines.request_id.egp_requisition_id",
    )
    def _compute_source_documents(self):
        for order in self:
            requests = order.order_line.mapped("purchase_request_lines.request_id")
            request = requests[:1]
            requisition = order.contract_id.requisition_id or order.requisition_id
            if not requisition and request:
                requisition = request.egp_requisition_id
            project_no = False
            project_name = False
            if order.contract_id and order.contract_id.egp_reference:
                project_no = order.contract_id.egp_reference
            elif requisition and requisition.egp_reference:
                project_no = requisition.egp_reference
            elif request and request.egp_project_reference:
                project_no = request.egp_project_reference
            if requisition and requisition.egp_project_name:
                project_name = requisition.egp_project_name
            elif request and request.egp_project_name:
                project_name = request.egp_project_name
            order.source_request_ids = requests
            order.source_requisition_id = requisition
            order.source_project_reference = project_no
            order.source_project_name = project_name

    def _get_contract_from_purchase_request(self):
        self.ensure_one()
        return self.order_line.mapped(
            "purchase_request_lines.request_id.contract_id"
        )[:1]

    def _sync_contract_from_purchase_request(self):
        for order in self:
            if order.contract_id:
                continue
            contract = order._get_contract_from_purchase_request()
            if contract:
                order.contract_id = contract

    def button_confirm(self):
        self._sync_contract_from_purchase_request()
        for order in self:
            if not order.contract_id:
                continue
            if order.contract_id.quantity_policy == "unlimited":
                continue
            # ขั้นตอนที่ 11: ตรวจก่อนยืนยัน แล้วตัดลดยอดแบบเรียลไทม์ผ่าน compute
            order.contract_id._check_amount_available(
                required_amount=order.amount_untaxed,
                exclude_orders=order,
            )
        res = super().button_confirm()
        for order in self.filtered(
            lambda po: po.contract_id
            and po.contract_id.quantity_policy != "unlimited"
            and po.state in ("purchase", "done")
        ):
            order.contract_id.invalidate_recordset()
            order.message_post(
                body=_(
                    "ตัดลดยอดคงเหลือสัญญา %(contract)s แล้ว "
                    "(ยอด PO %(amount)s / คงเหลือ %(remaining)s)"
                )
                % {
                    "contract": order.contract_id.display_name,
                    "amount": "{:,.2f}".format(order.amount_untaxed or 0.0),
                    "remaining": "{:,.2f}".format(
                        order.contract_id.amount_remaining or 0.0
                    ),
                }
            )
        self._release_contract_purchase_requests()
        return res

    def _release_contract_purchase_requests(self):
        """ปลดรายการ PR ที่ผูกสัญญาเมื่อ PO ยืนยันแล้ว — เปลี่ยนสถานะเป็น done."""
        for order in self.filtered(
            lambda po: po.contract_id and po.state in ("purchase", "done")
        ):
            requests = order.order_line.mapped(
                "purchase_request_lines.request_id"
            ).filtered(
                lambda pr: pr.contract_id
                and pr.state in ("approved", "in_progress")
            )
            for request in requests:
                request.with_context(skip_budget_check_reset=True).write(
                    {"state": "done"}
                )
                request.message_post(
                    body=_(
                        "ปลดรายการ PR อัตโนมัติ — PO %(po)s ยืนยันแล้ว "
                        "(สัญญา %(contract)s)"
                    )
                    % {
                        "po": order.display_name,
                        "contract": order.contract_id.display_name,
                    }
                )

    def button_cancel(self):
        contracts = self.mapped("contract_id")
        res = super().button_cancel()
        if contracts:
            contracts.invalidate_recordset()
        return res

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.contract_id:
            vals["contract_id"] = self.contract_id.id
        return vals

    @api.onchange("order_line")
    def _onchange_order_line_sync_contract(self):
        if not self.contract_id:
            contract = self._get_contract_from_purchase_request()
            if contract:
                self.contract_id = contract
