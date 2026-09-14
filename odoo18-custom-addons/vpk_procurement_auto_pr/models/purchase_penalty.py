from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProcurementPurchasePenalty(models.Model):
    _name = "procurement.purchase.penalty"
    _description = "Purchase Non-compliance Penalty"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="รายการค่าปรับ",
        required=True,
        default=lambda self: _("ค่าปรับการจัดซื้อจัดจ้าง"),
        tracking=True,
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ/สั่งจ้าง/สั่งซ่อม",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        related="purchase_order_id.partner_id",
        string="ผู้จำหน่าย/ผู้รับจ้าง",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="purchase_order_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="purchase_order_id.currency_id",
        store=True,
        readonly=True,
    )
    penalty_type = fields.Selection(
        selection=[
            ("late_delivery", "ส่งมอบพัสดุล่าช้า"),
            ("late_service", "ส่งมอบงานจ้างล่าช้า"),
            ("repair_delay", "งานซ่อมล่าช้า"),
            ("specification", "พัสดุ/งานไม่ตรงข้อกำหนด"),
            ("repair_noncompliance", "งานซ่อมไม่เป็นไปตามข้อกำหนด"),
            ("other", "อื่น ๆ"),
        ],
        string="ประเภทความผิด",
        required=True,
        default="late_delivery",
        tracking=True,
    )
    calculation_method = fields.Selection(
        selection=[
            ("daily_percent", "ร้อยละต่อวัน"),
            ("percent", "ร้อยละของฐานค่าปรับ"),
            ("fixed", "ค่าปรับเหมาจ่าย"),
        ],
        string="วิธีคำนวณ",
        required=True,
        default="daily_percent",
        tracking=True,
    )
    due_date = fields.Date(string="วันที่ครบกำหนด", tracking=True)
    actual_date = fields.Date(string="วันที่ส่งมอบ/แก้ไขจริง", tracking=True)
    late_days = fields.Integer(
        string="จำนวนวันล่าช้า",
        compute="_compute_late_days",
        store=True,
    )
    base_amount = fields.Monetary(
        string="ฐานคำนวณค่าปรับ",
        required=True,
        tracking=True,
    )
    penalty_rate = fields.Float(
        string="อัตราค่าปรับ (%)",
        digits=(16, 4),
        tracking=True,
    )
    fixed_amount = fields.Monetary(
        string="ค่าปรับเหมาจ่าย",
        tracking=True,
    )
    penalty_amount = fields.Monetary(
        string="จำนวนเงินค่าปรับ",
        compute="_compute_penalty_amount",
        store=True,
        tracking=True,
    )
    noncompliance_detail = fields.Text(
        string="รายละเอียดการไม่เป็นไปตามข้อกำหนด",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "แบบร่าง"),
            ("confirmed", "ยืนยันค่าปรับ"),
            ("deducted", "หักค่าปรับแล้ว"),
            ("waived", "ยกเว้นค่าปรับ"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    @api.depends("due_date", "actual_date")
    def _compute_late_days(self):
        for penalty in self:
            penalty.late_days = (
                max((penalty.actual_date - penalty.due_date).days, 0)
                if penalty.due_date and penalty.actual_date
                else 0
            )

    @api.depends(
        "calculation_method",
        "base_amount",
        "penalty_rate",
        "fixed_amount",
        "late_days",
    )
    def _compute_penalty_amount(self):
        for penalty in self:
            if penalty.calculation_method == "daily_percent":
                amount = (
                    penalty.base_amount
                    * penalty.penalty_rate
                    / 100.0
                    * penalty.late_days
                )
            elif penalty.calculation_method == "percent":
                amount = (
                    penalty.base_amount * penalty.penalty_rate / 100.0
                )
            else:
                amount = penalty.fixed_amount
            penalty.penalty_amount = max(amount, 0.0)

    @api.onchange("purchase_order_id")
    def _onchange_purchase_order_id(self):
        if self.purchase_order_id:
            self.base_amount = self.purchase_order_id.amount_untaxed
            self.due_date = self.purchase_order_id.procurement_due_date

    @api.constrains("base_amount", "penalty_rate", "fixed_amount")
    def _check_non_negative_amounts(self):
        for penalty in self:
            if (
                penalty.base_amount < 0
                or penalty.penalty_rate < 0
                or penalty.fixed_amount < 0
            ):
                raise ValidationError(
                    _("ฐานคำนวณ อัตรา และค่าปรับต้องไม่ติดลบ")
                )

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_mark_deducted(self):
        self.write({"state": "deducted"})

    def action_waive(self):
        self.write({"state": "waived"})

    def action_draft(self):
        self.write({"state": "draft"})


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    penalty_ids = fields.One2many(
        comodel_name="procurement.purchase.penalty",
        inverse_name="purchase_order_id",
        string="รายการค่าปรับ",
        copy=False,
    )
    penalty_count = fields.Integer(
        string="จำนวนรายการค่าปรับ",
        compute="_compute_purchase_penalties",
    )
    total_penalty_amount = fields.Monetary(
        string="ค่าปรับรวม",
        compute="_compute_purchase_penalties",
        store=True,
        currency_field="currency_id",
    )
    net_amount_after_penalty = fields.Monetary(
        string="ยอดสุทธิหลังหักค่าปรับ",
        compute="_compute_purchase_penalties",
        store=True,
        currency_field="currency_id",
    )

    @api.depends(
        "penalty_ids.state",
        "penalty_ids.penalty_amount",
        "amount_total",
    )
    def _compute_purchase_penalties(self):
        for order in self:
            active_penalties = order.penalty_ids.filtered(
                lambda penalty: penalty.state in ("confirmed", "deducted")
            )
            order.penalty_count = len(order.penalty_ids)
            order.total_penalty_amount = sum(
                active_penalties.mapped("penalty_amount")
            )
            order.net_amount_after_penalty = max(
                order.amount_total - order.total_penalty_amount,
                0.0,
            )
