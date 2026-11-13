# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends(
        "requisition_id",
        "requisition_id.requisition_type",
        "contract_id",
    )
    def _compute_require_vendor_signature(self):
        """ใบสั่งซื้อตามสัญญาก็ต้องให้ผู้ขายยืนยันในแอปเหมือนใบ e-GP."""
        for order in self:
            is_egp = (
                order.requisition_id
                and order.requisition_id.requisition_type == "egp_procurement"
            )
            order.require_vendor_signature = bool(is_egp or order.contract_id)

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

    @api.depends(
        "requisition_id",
        "requisition_id.egp_disbursement_type",
        "contract_id",
        "contract_id.requisition_id",
        "contract_id.requisition_id.egp_disbursement_type",
    )
    def _compute_egp_disbursement_type(self):
        for order in self:
            requisition = order.requisition_id or order.contract_id.requisition_id
            order.egp_disbursement_type = (
                requisition.egp_disbursement_type if requisition else False
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
    source_request_count = fields.Integer(
        string="จำนวนใบขอซื้อ",
        compute="_compute_source_documents",
    )
    source_requisition_count = fields.Integer(
        string="จำนวน e-GP",
        compute="_compute_source_documents",
    )
    source_contract_count = fields.Integer(
        string="จำนวนสัญญา",
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
            requisition = order.contract_id.requisition_id or order.requisition_id
            if not requisition and requests[:1] and "egp_requisition_id" in requests._fields:
                requisition = requests[:1].egp_requisition_id
            if (
                not requests
                and requisition
                and requisition.purchase_request_id
            ):
                requests = requisition.purchase_request_id
            request = requests[:1]
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
            order.source_request_count = len(requests)
            order.source_requisition_count = 1 if requisition else 0
            order.source_contract_count = 1 if order.contract_id else 0

    def _get_contract_from_purchase_request(self):
        self.ensure_one()
        return self.order_line.mapped(
            "purchase_request_lines.request_id.contract_id"
        )[:1]

    def _get_contract_from_requisition(self):
        """ดึงสัญญาที่สร้างจากเอกสาร e-GP เดียวกัน (และคู่ค้าตรงกันถ้ามี)."""
        self.ensure_one()
        requisition = self.requisition_id
        if not requisition or "contract_ids" not in requisition._fields:
            return self.env["purchase.contract"]
        contracts = requisition.contract_ids.filtered(
            lambda contract: contract.state in ("draft", "confirmed", "done")
        )
        if self.partner_id:
            matched = contracts.filtered(
                lambda contract: not contract.partner_id
                or contract.partner_id == self.partner_id
            )
            if matched:
                return matched[:1]
        return contracts[:1]

    def _sync_contract_from_purchase_request(self):
        for order in self:
            if order.contract_id:
                continue
            contract = (
                order._get_contract_from_purchase_request()
                or order._get_contract_from_requisition()
            )
            if contract:
                order.contract_id = contract

    def action_view_source_purchase_requests(self):
        self.ensure_one()
        requests = self.source_request_ids
        if not requests and "purchase_request_ids" in self._fields:
            requests = self.purchase_request_ids
        action = {
            "name": _("ใบขอซื้อ"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "view_mode": "list,form",
            "domain": [("id", "in", requests.ids)],
            "context": {"create": False},
        }
        if len(requests) == 1:
            action["view_mode"] = "form"
            action["res_id"] = requests.id
        return action

    def action_view_source_requisition(self):
        self.ensure_one()
        requisition = self.source_requisition_id or self.requisition_id
        if not requisition:
            return False
        return {
            "name": _("เอกสารกระบวนการ e-GP"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.requisition",
            "view_mode": "form",
            "res_id": requisition.id,
            "context": {"create": False},
        }

    def action_view_source_contract(self):
        self.ensure_one()
        if not self.contract_id:
            return False
        return {
            "name": _("สัญญา"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.contract",
            "view_mode": "form",
            "res_id": self.contract_id.id,
            "context": {"create": False},
        }

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

    @api.onchange("order_line", "requisition_id", "partner_id")
    def _onchange_order_line_sync_contract(self):
        if not self.contract_id:
            contract = (
                self._get_contract_from_purchase_request()
                or self._get_contract_from_requisition()
            )
            if contract:
                self.contract_id = contract

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._sync_contract_from_purchase_request()
        return orders
