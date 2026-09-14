# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseContract(models.Model):
    """ทะเบียนสัญญาหลัก (Master Contract Record)."""

    _name = "purchase.contract"
    _description = "Master Purchase Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="รหัสสัญญา",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="คู่ค้า",
        tracking=True,
        domain="[('supplier_rank', '>', 0)]",
        context={"res_partner_search_mode": "supplier"},
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="สกุลเงิน",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    amount_total = fields.Monetary(
        string="มูลค่ารวมสัญญา",
        required=True,
        currency_field="currency_id",
        tracking=True,
        help="วงเงินสัญญารวมทั้งหมดที่ใช้เป็นฐานตรวจยอดคงเหลือ",
    )
    date_start = fields.Date(
        string="วันเริ่มสัญญา",
        default=fields.Date.context_today,
        tracking=True,
    )
    date_end = fields.Date(string="วันสิ้นสุดสัญญา", tracking=True)
    description = fields.Text(string="เงื่อนไขข้อตกลง")
    payment_term_note = fields.Text(
        string="เงื่อนไขแบ่งงวดจ่ายเงิน",
        help="สรุปเงื่อนไขการแบ่งงวดจ่ายเงินตามสัญญา",
    )
    contract_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="purchase_contract_ir_attachment_rel",
        column1="contract_id",
        column2="attachment_id",
        string="เอกสารสัญญา",
        copy=False,
        help="แนบสัญญาที่ลงนามแล้ว TOR หลักประกัน และเอกสารประกอบสัญญา",
    )
    contract_attachment_count = fields.Integer(
        string="จำนวนเอกสารสัญญา",
        compute="_compute_contract_attachment_count",
    )
    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="เอกสาร e-GP อ้างอิง",
        tracking=True,
        index=True,
        copy=False,
        domain="[('requisition_type', '=', 'egp_procurement')]",
    )
    egp_reference = fields.Char(
        string="เลขที่โครงการ (e-GP)",
        related="requisition_id.egp_reference",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "แบบร่าง"),
            ("confirmed", "มีผลบังคับใช้"),
            ("done", "ปิดสัญญา"),
            ("cancel", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    installment_ids = fields.One2many(
        comodel_name="purchase.contract.installment",
        inverse_name="contract_id",
        string="งวดจ่ายเงิน",
        copy=True,
    )
    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="contract_id",
        string="ใบขอซื้อ",
    )
    purchase_order_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="contract_id",
        string="ใบสั่งซื้อ",
    )
    vendor_bill_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="contract_id",
        string="ใบแจ้งหนี้",
    )
    amount_pr_reserved = fields.Monetary(
        string="ยอดจองจาก PR",
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    amount_po_confirmed = fields.Monetary(
        string="ยอดตัดจาก PO",
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )

    @api.depends("contract_attachment_ids")
    def _compute_contract_attachment_count(self):
        for contract in self:
            contract.contract_attachment_count = len(
                contract.contract_attachment_ids
            )

    def action_view_contract_attachments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสารสัญญา - %s") % self.display_name,
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.contract_attachment_ids.ids)],
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }
    amount_consumed = fields.Monetary(
        string="ยอดใช้ไปแล้ว",
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    amount_remaining = fields.Monetary(
        string="มูลค่าคงเหลือของสัญญา",
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    purchase_request_count = fields.Integer(compute="_compute_document_counts")
    purchase_order_count = fields.Integer(compute="_compute_document_counts")
    vendor_bill_count = fields.Integer(compute="_compute_document_counts")

    _sql_constraints = [
        (
            "name_company_uniq",
            "unique(name, company_id)",
            "รหัสสัญญาต้องไม่ซ้ำในบริษัทเดียวกัน",
        ),
    ]

    @api.depends(
        "amount_total",
        "purchase_request_ids.state",
        "purchase_request_ids.estimated_cost",
        "purchase_request_ids.line_ids.cancelled",
        "purchase_request_ids.line_ids.estimated_cost",
        "purchase_request_ids.line_ids.purchase_lines",
        "purchase_request_ids.line_ids.purchase_lines.state",
        "purchase_request_ids.line_ids.purchase_lines.order_id.state",
        "purchase_request_ids.line_ids.purchase_lines.order_id.amount_untaxed",
        "purchase_order_ids.state",
        "purchase_order_ids.amount_untaxed",
    )
    def _compute_amounts(self):
        for contract in self:
            consumed = contract._get_consumed_amount()
            contract.amount_po_confirmed = contract._get_po_confirmed_amount()
            contract.amount_pr_reserved = max(
                0.0, consumed - contract.amount_po_confirmed
            )
            contract.amount_consumed = consumed
            contract.amount_remaining = (contract.amount_total or 0.0) - consumed

    def _compute_document_counts(self):
        for contract in self:
            contract.purchase_request_count = len(contract.purchase_request_ids)
            contract.purchase_order_count = len(
                contract.purchase_order_ids.filtered(
                    lambda order: order.state != "cancel"
                )
            )
            contract.vendor_bill_count = len(
                contract.vendor_bill_ids.filtered(
                    lambda move: move.move_type in ("in_invoice", "in_refund")
                    and move.state != "cancel"
                )
            )

    def _get_po_line_contract_amount(self, order):
        """มูลค่า PO ที่ใช้ตัดสัญญา — ใช้ยอดยังไม่รวมภาษีให้สอดคล้องกับ estimated_cost ของ PR."""
        return order.amount_untaxed

    def _get_po_confirmed_amount(self, exclude_orders=None):
        """มูลค่า PO ที่ยืนยันแล้ว (ตัดลดวงเงินสัญญา)."""
        self.ensure_one()
        exclude_ids = exclude_orders.ids if exclude_orders else []
        orders = self.purchase_order_ids.filtered(
            lambda order: order.state in ("purchase", "done")
            and order.id not in exclude_ids
        )
        return sum(self._get_po_line_contract_amount(order) for order in orders)

    def _get_pr_reserved_amount(self, exclude_requests=None):
        """ยอด PR ที่ยังจองวงเงินสัญญา (ยังไม่ถูกครอบด้วย PO ที่ยืนยันแล้ว)."""
        self.ensure_one()
        exclude_ids = exclude_requests.ids if exclude_requests else []
        amount = 0.0
        for request in self.purchase_request_ids.filtered(
            lambda pr: pr.state in ("to_approve", "approved", "in_progress")
            and pr.id not in exclude_ids
        ):
            pr_amount = request._get_contract_amount()
            covered = request._get_contract_covered_by_po_amount()
            amount += max(0.0, pr_amount - covered)
        return amount

    def _get_consumed_amount(self, exclude_requests=None, exclude_orders=None):
        """
        มูลค่าที่ใช้ไปแล้ว = มูลค่า PO ที่ยืนยัน + ยอด PR ที่จองค้างอยู่
        (ไม่นับซ้ำเมื่อ PR ถูกแปลงเป็น PO แล้ว)
        """
        self.ensure_one()
        return self._get_po_confirmed_amount(
            exclude_orders=exclude_orders
        ) + self._get_pr_reserved_amount(exclude_requests=exclude_requests)

    def get_remaining_amount(self, exclude_requests=None, exclude_orders=None):
        self.ensure_one()
        return (self.amount_total or 0.0) - self._get_consumed_amount(
            exclude_requests=exclude_requests,
            exclude_orders=exclude_orders,
        )

    def _format_amount(self, amount):
        self.ensure_one()
        return "{:,.2f}".format(amount or 0.0)

    def _check_amount_available(self, required_amount, exclude_requests=None, exclude_orders=None):
        """Hard Block ถ้ามูลค่างวดปัจจุบันเกินยอดคงเหลือสัญญา."""
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(
                _(
                    "สัญญา %(contract)s ยังไม่มีผลบังคับใช้ (สถานะ: %(state)s)"
                )
                % {
                    "contract": self.display_name,
                    "state": dict(self._fields["state"].selection).get(self.state),
                }
            )
        remaining = self.get_remaining_amount(
            exclude_requests=exclude_requests,
            exclude_orders=exclude_orders,
        )
        if required_amount - remaining > 1e-6:
            raise UserError(
                _(
                    "มูลค่าเอกสารเกินวงเงินคงเหลือของสัญญา (Hard Block)\n\n"
                    "สัญญา: %(contract)s\n"
                    "มูลค่ารวมสัญญา: %(total)s\n"
                    "ยอดคงเหลือ: %(remaining)s\n"
                    "มูลค่าเอกสารงวดนี้: %(required)s\n"
                    "ส่วนเกิน: %(over)s"
                )
                % {
                    "contract": self.display_name,
                    "total": self._format_amount(self.amount_total),
                    "remaining": self._format_amount(remaining),
                    "required": self._format_amount(required_amount),
                    "over": self._format_amount(required_amount - remaining),
                }
            )
        return remaining

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) in (_("New"), "New", False):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("purchase.contract") or _("New")
                )
        return super().create(vals_list)

    @api.constrains("amount_total")
    def _check_amount_total(self):
        for contract in self:
            if contract.amount_total < 0:
                raise ValidationError(_("มูลค่ารวมสัญญาต้องไม่ติดลบ"))

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for contract in self:
            if (
                contract.date_start
                and contract.date_end
                and contract.date_end < contract.date_start
            ):
                raise ValidationError(_("วันสิ้นสุดสัญญาต้องไม่ก่อนวันเริ่มสัญญา"))

    def action_confirm(self):
        for contract in self:
            if not contract.partner_id:
                raise UserError(_("กรุณาระบุคู่ค้าก่อนยืนยันสัญญา"))
            if not contract.amount_total:
                raise UserError(_("กรุณาระบุมูลค่ารวมสัญญาก่อนยืนยัน"))
            if contract.installment_ids:
                installment_total = sum(contract.installment_ids.mapped("amount"))
                if abs(installment_total - contract.amount_total) > 0.01:
                    raise UserError(
                        _(
                            "ผลรวมงวดจ่ายเงิน (%(installments)s) ไม่เท่ากับมูลค่ารวมสัญญา (%(total)s)"
                        )
                        % {
                            "installments": contract._format_amount(installment_total),
                            "total": contract._format_amount(contract.amount_total),
                        }
                    )
        self.write({"state": "confirmed"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        linked_active = self.filtered(
            lambda contract: contract.purchase_request_ids.filtered(
                lambda pr: pr.state not in ("rejected", "done")
            )
            or contract.purchase_order_ids.filtered(
                lambda po: po.state in ("purchase", "done")
            )
        )
        if linked_active:
            raise UserError(
                _(
                    "ไม่สามารถยกเลิกสัญญาที่มี PR/PO ที่ยังใช้งานอยู่: %s"
                )
                % ", ".join(linked_active.mapped("display_name"))
            )
        self.write({"state": "cancel"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_view_purchase_requests(self):
        self.ensure_one()
        return {
            "name": _("ใบขอซื้อของสัญญา"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {"default_contract_id": self.id},
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            "name": _("ใบสั่งซื้อของสัญญา"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {"default_contract_id": self.id},
        }

    def action_view_vendor_bills(self):
        self.ensure_one()
        return {
            "name": _("ใบแจ้งหนี้ของสัญญา"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("contract_id", "=", self.id),
                ("move_type", "in", ("in_invoice", "in_refund")),
            ],
            "context": {
                "default_contract_id": self.id,
                "default_move_type": "in_invoice",
            },
        }

    def action_open_generate_installments(self):
        """เปิด wizard สร้างรายการงวดงาน."""
        self.ensure_one()
        return {
            "name": _("สร้างรายการงวดงาน"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.contract.generate.installments",
            "view_mode": "form",
            "target": "new",
            "context": {"default_contract_id": self.id},
        }

    def action_open_tracking_report(self):
        """Contract Tracking Report — รวมเอกสารที่อ้างอิงสัญญานี้."""
        self.ensure_one()
        return {
            "name": _("ติดตามสัญญา: %s") % self.display_name,
            "type": "ir.actions.act_window",
            "res_model": "purchase.contract",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }


class PurchaseContractInstallment(models.Model):
    _name = "purchase.contract.installment"
    _description = "Contract Payment Installment"
    _order = "sequence, id"

    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="สัญญา",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="ชื่องวด", required=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า/บริการ",
        domain="[('purchase_ok', '=', True)]",
        help="สินค้าหรือบริการที่เบิกในงวดนี้ — จะถูกดึงไปสร้างรายการ PR อัตโนมัติ",
    )
    amount = fields.Monetary(
        string="มูลค่างวด",
        required=True,
        currency_field="currency_id",
    )
    percent = fields.Float(
        string="% ของสัญญา",
        compute="_compute_percent",
        store=True,
        digits=(16, 2),
    )
    date_planned = fields.Date(string="กำหนดจ่าย/เบิก")
    note = fields.Char(string="หมายเหตุ")
    currency_id = fields.Many2one(
        related="contract_id.currency_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="contract_id.company_id",
        store=True,
        readonly=True,
    )
    purchase_request_line_ids = fields.One2many(
        comodel_name="purchase.request.line",
        inverse_name="contract_installment_id",
        string="PR Lines",
    )
    is_used = fields.Boolean(
        string="ใช้แล้ว",
        compute="_compute_is_used",
        store=True,
        help="งวดนี้ถูกอ้างอิงใน PR แล้ว",
    )

    @api.depends(
        "purchase_request_line_ids",
        "purchase_request_line_ids.request_id.state",
        "purchase_request_line_ids.cancelled",
    )
    def _compute_is_used(self):
        for line in self:
            line.is_used = bool(
                line.purchase_request_line_ids.filtered(
                    lambda prl: prl.request_id.state not in ("rejected",)
                    and not prl.cancelled
                )
            )

    @api.depends("amount", "contract_id.amount_total")
    def _compute_percent(self):
        for line in self:
            total = line.contract_id.amount_total or 0.0
            line.percent = (line.amount / total * 100.0) if total else 0.0
