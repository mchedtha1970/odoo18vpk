from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProcurementGuarantee(models.Model):
    _name = "procurement.guarantee"
    _description = "Procurement Guarantee Register"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "coverage_end_date asc, id desc"

    name = fields.Char(
        string="เลขทะเบียนหลักประกัน",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
        index=True,
    )
    guarantee_type = fields.Selection(
        selection=[
            ("contract", "หลักประกันสัญญา"),
            ("performance", "หลักประกันผลงาน"),
            ("goods", "หลักประกันของ"),
            ("advance_payment", "หลักประกันการจ่ายเงินล่วงหน้า"),
        ],
        string="ประเภทหลักประกัน",
        required=True,
        default="contract",
        tracking=True,
        index=True,
    )
    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="สัญญา",
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ/สั่งจ้าง",
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="คู่สัญญา/ผู้วางหลักประกัน",
        compute="_compute_document_information",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_document_information",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_document_information",
        store=True,
        readonly=True,
    )
    instrument_type = fields.Selection(
        selection=[
            ("bank_guarantee", "หนังสือค้ำประกันธนาคาร"),
            ("cash", "เงินสด"),
            ("cheque", "เช็คธนาคาร"),
            ("government_bond", "พันธบัตรรัฐบาล"),
            ("other", "อื่น ๆ"),
        ],
        string="รูปแบบหลักประกัน",
        required=True,
        default="bank_guarantee",
        tracking=True,
    )
    issuer_id = fields.Many2one(
        comodel_name="res.bank",
        string="ธนาคาร/ผู้ออกหลักประกัน",
        tracking=True,
    )
    reference = fields.Char(
        string="เลขที่หนังสือค้ำประกัน/เลขอ้างอิง",
        required=True,
        tracking=True,
    )
    issue_date = fields.Date(string="วันที่ออกหลักประกัน", tracking=True)
    base_amount = fields.Monetary(
        string="มูลค่าฐาน",
        tracking=True,
    )
    guarantee_percent = fields.Float(
        string="อัตราหลักประกัน (%)",
        digits=(16, 4),
        tracking=True,
    )
    amount = fields.Monetary(
        string="มูลค่าหลักประกัน",
        required=True,
        tracking=True,
    )
    coverage_start_date = fields.Date(
        string="วันเริ่มคุ้มครอง",
        required=True,
        tracking=True,
    )
    coverage_end_date = fields.Date(
        string="วันสิ้นสุดความคุ้มครอง",
        required=True,
        tracking=True,
        index=True,
    )
    coverage_days = fields.Integer(
        string="ระยะเวลาคุ้มครอง (วัน)",
        compute="_compute_coverage_days",
        store=True,
    )
    days_to_expiry = fields.Integer(
        string="คงเหลือก่อนหมดอายุ (วัน)",
        compute="_compute_expiry_information",
    )
    expiry_status = fields.Selection(
        selection=[
            ("normal", "อยู่ในระยะคุ้มครอง"),
            ("expiring", "ใกล้หมดอายุ"),
            ("expired", "หมดอายุ"),
            ("returned", "ส่งคืนแล้ว"),
        ],
        string="สถานะอายุหลักประกัน",
        compute="_compute_expiry_information",
    )
    obligation_completed = fields.Boolean(
        string="คู่สัญญาปฏิบัติครบถ้วนแล้ว",
        tracking=True,
    )
    obligation_completed_date = fields.Date(
        string="วันที่ครบพันธะสัญญา",
        tracking=True,
    )
    obligation_note = fields.Text(string="รายละเอียดการครบพันธะ")
    return_date = fields.Date(
        string="วันที่ส่งคืนหลักประกัน",
        readonly=True,
        copy=False,
        tracking=True,
    )
    returned_by_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้บันทึกการส่งคืน",
        readonly=True,
        copy=False,
    )
    return_reference = fields.Char(
        string="เลขที่หนังสือส่งคืน",
        copy=False,
    )
    return_note = fields.Text(string="หมายเหตุการส่งคืน", copy=False)
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="procurement_guarantee_ir_attachment_rel",
        column1="guarantee_id",
        column2="attachment_id",
        string="เอกสารหลักประกัน",
        copy=False,
    )
    state = fields.Selection(
        selection=[
            ("draft", "แบบร่าง"),
            ("active", "ถือหลักประกัน"),
            ("eligible_return", "พร้อมส่งคืน"),
            ("returned", "ส่งคืนแล้ว"),
            ("claimed", "เรียกหลักประกัน"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        required=True,
        default="draft",
        tracking=True,
        copy=False,
        index=True,
    )

    @api.depends(
        "contract_id",
        "contract_id.partner_id",
        "contract_id.company_id",
        "contract_id.currency_id",
        "purchase_order_id",
        "purchase_order_id.partner_id",
        "purchase_order_id.company_id",
        "purchase_order_id.currency_id",
    )
    def _compute_document_information(self):
        for guarantee in self:
            document = guarantee.contract_id or guarantee.purchase_order_id
            guarantee.partner_id = document.partner_id
            guarantee.company_id = document.company_id or self.env.company
            guarantee.currency_id = (
                document.currency_id or self.env.company.currency_id
            )

    @api.depends("coverage_start_date", "coverage_end_date")
    def _compute_coverage_days(self):
        for guarantee in self:
            guarantee.coverage_days = (
                (guarantee.coverage_end_date - guarantee.coverage_start_date).days
                + 1
                if guarantee.coverage_start_date
                and guarantee.coverage_end_date
                else 0
            )

    @api.depends("coverage_end_date", "state")
    def _compute_expiry_information(self):
        today = fields.Date.context_today(self)
        for guarantee in self:
            days = (
                (guarantee.coverage_end_date - today).days
                if guarantee.coverage_end_date
                else 0
            )
            guarantee.days_to_expiry = days
            if guarantee.state == "returned":
                status = "returned"
            elif days < 0:
                status = "expired"
            elif days <= 30:
                status = "expiring"
            else:
                status = "normal"
            guarantee.expiry_status = status

    @api.onchange("contract_id", "purchase_order_id")
    def _onchange_documents(self):
        document = self.contract_id or self.purchase_order_id
        if document:
            self.base_amount = document.amount_total
            if self.guarantee_percent:
                self.amount = (
                    self.base_amount * self.guarantee_percent / 100.0
                )
        if self.contract_id:
            self.coverage_start_date = self.contract_id.date_start
            self.coverage_end_date = self.contract_id.date_end

    @api.onchange("base_amount", "guarantee_percent")
    def _onchange_guarantee_amount(self):
        if self.base_amount and self.guarantee_percent:
            self.amount = self.base_amount * self.guarantee_percent / 100.0

    @api.constrains(
        "contract_id",
        "purchase_order_id",
        "coverage_start_date",
        "coverage_end_date",
        "amount",
    )
    def _check_guarantee_data(self):
        for guarantee in self:
            if not guarantee.contract_id and not guarantee.purchase_order_id:
                raise ValidationError(
                    _("กรุณาระบุสัญญาหรือใบสั่งซื้อ/สั่งจ้าง")
                )
            if (
                guarantee.coverage_start_date
                and guarantee.coverage_end_date
                and guarantee.coverage_end_date
                < guarantee.coverage_start_date
            ):
                raise ValidationError(
                    _("วันสิ้นสุดคุ้มครองต้องไม่ก่อนวันเริ่มคุ้มครอง")
                )
            if guarantee.amount < 0:
                raise ValidationError(_("มูลค่าหลักประกันต้องไม่ติดลบ"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) in (_("New"), "New", False):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "procurement.guarantee"
                    )
                    or _("New")
                )
        return super().create(vals_list)

    def action_activate(self):
        self.write({"state": "active"})

    def action_mark_obligation_completed(self):
        for guarantee in self:
            if not guarantee.obligation_completed:
                guarantee.write({
                    "obligation_completed": True,
                    "obligation_completed_date": fields.Date.context_today(
                        guarantee
                    ),
                })
            guarantee.state = "eligible_return"

    def action_return(self):
        for guarantee in self:
            if not guarantee.obligation_completed:
                raise UserError(
                    _("ต้องยืนยันว่าคู่สัญญาปฏิบัติครบถ้วนก่อนส่งคืน")
                )
            guarantee.write({
                "state": "returned",
                "return_date": fields.Date.context_today(guarantee),
                "returned_by_id": self.env.user.id,
            })
            guarantee.message_post(
                body=_("บันทึกการส่งคืนหลักประกันเรียบร้อยแล้ว")
            )

    def action_claim(self):
        self.write({"state": "claimed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({"state": "draft"})


class PurchaseContract(models.Model):
    _inherit = "purchase.contract"

    guarantee_ids = fields.One2many(
        comodel_name="procurement.guarantee",
        inverse_name="contract_id",
        string="หลักประกัน",
    )
    guarantee_count = fields.Integer(
        compute="_compute_guarantee_summary",
        string="จำนวนหลักประกัน",
    )
    active_guarantee_amount = fields.Monetary(
        compute="_compute_guarantee_summary",
        string="มูลค่าหลักประกันที่ถืออยู่",
        currency_field="currency_id",
    )

    @api.depends("guarantee_ids.state", "guarantee_ids.amount")
    def _compute_guarantee_summary(self):
        for contract in self:
            contract.guarantee_count = len(contract.guarantee_ids)
            contract.active_guarantee_amount = sum(
                contract.guarantee_ids.filtered(
                    lambda guarantee: guarantee.state
                    in ("active", "eligible_return")
                ).mapped("amount")
            )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    guarantee_ids = fields.One2many(
        comodel_name="procurement.guarantee",
        inverse_name="purchase_order_id",
        string="หลักประกัน",
    )
    guarantee_count = fields.Integer(
        compute="_compute_guarantee_summary",
        string="จำนวนหลักประกัน",
    )

    @api.depends("guarantee_ids")
    def _compute_guarantee_summary(self):
        for order in self:
            order.guarantee_count = len(order.guarantee_ids)
