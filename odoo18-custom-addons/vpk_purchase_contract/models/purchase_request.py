# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="รหัสสัญญาอ้างอิง",
        tracking=True,
        index=True,
        copy=False,
        domain="[('state', '=', 'confirmed'), ('company_id', 'in', [company_id, False])]",
        help="เลือกสัญญาหลักเพื่อเชื่อมโยงการเบิกงวดและตรวจวงเงินคงเหลือก่อนเช็คงบประมาณ",
    )
    contract_partner_id = fields.Many2one(
        related="contract_id.partner_id",
        string="คู่ค้าตามสัญญา",
        readonly=True,
    )
    contract_amount_total = fields.Monetary(
        related="contract_id.amount_total",
        string="มูลค่ารวมสัญญา",
        readonly=True,
        currency_field="currency_id",
    )
    contract_amount_remaining = fields.Monetary(
        related="contract_id.amount_remaining",
        string="มูลค่าคงเหลือสัญญา",
        readonly=True,
        currency_field="currency_id",
    )

    def _get_contract_amount(self):
        self.ensure_one()
        return sum(
            line.estimated_cost or 0.0
            for line in self.line_ids.filtered(lambda line: not line.cancelled)
        )

    def _get_contract_covered_by_po_amount(self):
        """มูลค่า PO ที่ยืนยันแล้วซึ่งเชื่อมกับ PR นี้ภายใต้สัญญาเดียวกัน."""
        self.ensure_one()
        if not self.contract_id:
            return 0.0
        orders = self.line_ids.mapped("purchase_lines.order_id").filtered(
            lambda order: order.contract_id == self.contract_id
            and order.state in ("purchase", "done")
        )
        return sum(orders.mapped("amount_untaxed"))

    def _check_contract_balance(self):
        """ขั้นตอนที่ 4-5: Hard Block ก่อนส่งไปตรวจงบประมาณ."""
        for request in self:
            if not request.contract_id:
                continue
            required = request._get_contract_amount()
            if required <= 0:
                raise UserError(
                    _("กรุณาระบุมูลค่ารายการใน PR ก่อนตรวจยอดคงเหลือสัญญา")
                )
            request.contract_id._check_amount_available(
                required_amount=required,
                exclude_requests=request,
            )

    @api.depends("state", "budget_check_state", "contract_id")
    def _compute_hide_reviews(self):
        super()._compute_hide_reviews()
        for request in self:
            if request.contract_id and request.state == "draft":
                request.hide_reviews = False

    def _has_contract_bypass_budget(self):
        """PR ที่มีสัญญาจะตรวจวงเงินจากสัญญาแทน ไม่จองงบประมาณแผ่นดิน."""
        self.ensure_one()
        return bool(self.contract_id)

    def action_check_budget_status(self):
        contract_prs = self.filtered(lambda pr: pr._has_contract_bypass_budget())
        normal_prs = self - contract_prs
        contract_prs._check_contract_balance()
        for request in contract_prs:
            request.with_context(skip_budget_check_reset=True).write(
                {
                    "budget_check_state": "enough",
                    "budget_check_date": fields.Datetime.now(),
                    "budget_check_message": _(
                        "ตรวจวงเงินผ่านสัญญา %(contract)s แทนงบประมาณแผ่นดิน\n"
                        "ยอดคงเหลือสัญญา: %(remaining)s"
                    )
                    % {
                        "contract": request.contract_id.display_name,
                        "remaining": "{:,.2f}".format(
                            request.contract_id.amount_remaining or 0.0
                        ),
                    },
                }
            )
        if contract_prs and not normal_prs:
            request = contract_prs[:1]
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("ตรวจวงเงินสัญญา: ผ่าน"),
                    "message": _(
                        "PR นี้ตรวจวงเงินจากสัญญา %(contract)s แทนงบประมาณแผ่นดิน"
                    )
                    % {"contract": request.contract_id.display_name},
                    "type": "success",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": self._name,
                        "res_id": request.id,
                        "view_mode": "form",
                        "views": [(False, "form")],
                        "target": "current",
                    },
                },
            }
        return super(PurchaseRequest, normal_prs).action_check_budget_status()

    def _check_budget_available_before_submit(self):
        contract_prs = self.filtered(lambda pr: pr._has_contract_bypass_budget())
        normal_prs = self - contract_prs
        contract_prs._check_contract_balance()
        for request in contract_prs:
            request.with_context(skip_budget_check_reset=True).write(
                {
                    "budget_check_state": "enough",
                    "budget_check_date": fields.Datetime.now(),
                    "budget_check_message": _(
                        "ตรวจวงเงินผ่านสัญญา %(contract)s"
                    )
                    % {"contract": request.contract_id.display_name},
                }
            )
        if normal_prs:
            super(PurchaseRequest, normal_prs)._check_budget_available_before_submit()

    def _get_default_product_for_contract(self, contract):
        """ดึงสินค้า/บริการจาก PR ต้นทางของสัญญา (ผ่าน e-GP → PR)."""
        if contract.requisition_id and contract.requisition_id.purchase_request_id:
            source_pr = contract.requisition_id.purchase_request_id
            product = source_pr.line_ids.filtered(
                lambda line: not line.cancelled and line.product_id
            ).mapped("product_id")[:1]
            if product:
                return product
        return self.env["product.product"]

    def _prepare_installment_pr_lines(self, contract, installments):
        """เตรียมค่า PR line จากงวดงานของสัญญา."""
        default_product = self._get_default_product_for_contract(contract)
        line_vals = []
        for inst in installments:
            product = inst.product_id or default_product
            name = inst.name
            if product:
                name = "%s - %s" % (inst.name, product.display_name)
            vals = {
                "product_id": product.id if product else False,
                "name": name,
                "product_qty": 1.0,
                "estimated_cost": inst.amount or 0.0,
                "contract_installment_id": inst.id,
                "date_required": inst.date_planned or fields.Date.context_today(self),
            }
            if product:
                vals["product_uom_id"] = product.uom_id.id
            line_vals.append((0, 0, vals))
        return line_vals

    @api.onchange("contract_id")
    def _onchange_contract_id(self):
        if not self.contract_id:
            return
        contract = self.contract_id
        if not contract.installment_ids:
            if contract.partner_id:
                return {
                    "warning": {
                        "title": _("ผูกสัญญาแล้ว"),
                        "message": _(
                            "สัญญา %(contract)s คู่ค้า %(partner)s "
                            "ยอดคงเหลือ %(remaining)s\n"
                            "สัญญานี้ไม่มีงวดงาน — กรุณาเพิ่มรายการ PR เอง"
                        )
                        % {
                            "contract": contract.display_name,
                            "partner": contract.partner_id.display_name,
                            "remaining": "{:,.2f}".format(
                                contract.amount_remaining or 0.0
                            ),
                        },
                    }
                }
            return

        available = contract.installment_ids.filtered(
            lambda inst: not inst.is_used
        ).sorted("sequence")
        if not available:
            return {
                "warning": {
                    "title": _("ไม่มีงวดว่าง"),
                    "message": _(
                        "สัญญา %(contract)s ไม่มีงวดงานที่ยังไม่ถูกใช้ "
                        "กรุณาตรวจสอบงวดงานในสัญญาหรือเพิ่มรายการ PR เอง"
                    )
                    % {"contract": contract.display_name},
                }
            }

        existing_installment_ids = set(
            self.line_ids.mapped("contract_installment_id").ids
        )
        next_installment = available.filtered(
            lambda inst: inst.id not in existing_installment_ids
        )[:1]
        if not next_installment:
            return

        new_lines = self._prepare_installment_pr_lines(contract, next_installment)
        self.update({"line_ids": new_lines})

        return {
            "warning": {
                "title": _("ดึงงวดงานแล้ว"),
                "message": _(
                    "ดึง \"%(installment)s\" จากสัญญา %(contract)s\n"
                    "มูลค่างวด: %(amount)s\n"
                    "คู่ค้า: %(partner)s / ยอดคงเหลือสัญญา: %(remaining)s"
                )
                % {
                    "installment": next_installment.name,
                    "contract": contract.display_name,
                    "amount": "{:,.2f}".format(next_installment.amount or 0.0),
                    "partner": (contract.partner_id.display_name or "-"),
                    "remaining": "{:,.2f}".format(
                        contract.amount_remaining or 0.0
                    ),
                },
            }
        }


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    contract_installment_id = fields.Many2one(
        comodel_name="purchase.contract.installment",
        string="งวดงานสัญญา",
        index=True,
        copy=False,
        help="อ้างอิงงวดงานจากสัญญาหลักที่ PR นี้เบิก",
    )
    contract_installment_name = fields.Char(
        related="contract_installment_id.name",
        string="ชื่องวด",
        readonly=True,
    )
