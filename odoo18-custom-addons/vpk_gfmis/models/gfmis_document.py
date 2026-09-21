# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class GfmisDocument(models.Model):
    _name = "gfmis.document"
    _description = "เอกสารกระบวนการ GFMIS"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "document_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="เลขที่ ERP",
        required=True,
        copy=False,
        default="/",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    company_partner_id = fields.Many2one(
        related="company_id.partner_id",
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=True,
    )
    doc_class = fields.Selection(
        [
            ("request", "ขอเบิกเงิน"),
            ("agency_pay", "ขอจ่ายโดยส่วนราชการ"),
            ("return", "เบิกเกินส่งคืน"),
        ],
        string="ประเภทเอกสาร",
        required=True,
        default="request",
        tracking=True,
        index=True,
    )
    form_type_id = fields.Many2one(
        "gfmis.form.type",
        string="แบบฟอร์ม GFMIS",
        required=True,
        ondelete="restrict",
        tracking=True,
        domain="[('doc_class', '=', doc_class), ('active', '=', True)]",
    )
    form_code = fields.Char(related="form_type_id.code", store=True)
    requires_po = fields.Boolean(related="form_type_id.requires_po")

    state = fields.Selection(
        [
            ("draft", "ร่าง"),
            ("recorded", "บันทึกใน GFMIS"),
            ("wait_approve_request", "รออนุมัติขอเบิก (อม.01)"),
            ("wait_approve_pay", "รออนุมัติสั่งจ่าย (อม.02)"),
            ("sent_treasury", "ส่งกรมบัญชีกลาง/คลังจังหวัด"),
            ("paid", "จ่ายตรงแล้ว"),
            ("wait_agency_pay", "รอจ่ายผู้มีสิทธิ (จ่ายผ่าน)"),
            ("agency_paid", "จ่ายให้ผู้มีสิทธิแล้ว"),
            ("returned", "เบิกเกินส่งคืน"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
        index=True,
        copy=False,
    )

    # Header — คู่มือบทที่ 3 ข้อมูลส่วนหัว
    agency_code = fields.Char(string="รหัสหน่วยงาน", size=5)
    area_code = fields.Char(string="รหัสพื้นที่", size=4)
    disbursing_unit_code = fields.Char(string="รหัสหน่วยเบิกจ่าย", size=10)
    reference = fields.Char(
        string="การอ้างอิง",
        help="เลขที่ใบแจ้งหนี้ หรือเอกสารหลักฐานการขอเบิก",
        tracking=True,
    )
    document_date = fields.Date(
        string="วันที่เอกสาร",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    posting_date = fields.Date(
        string="วันที่ผ่านรายการ",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    period = fields.Char(string="งวด", compute="_compute_period", store=True)
    gfmis_po_number = fields.Char(
        string="เลขที่ใบสั่งซื้อสั่งจ้างระบบ GFMIS",
        help="เลขที่ PO ใน New GFMIS Thai เช่น 4001004668",
        tracking=True,
    )
    gfmis_doc_number = fields.Char(
        string="เลขที่เอกสาร GFMIS",
        copy=False,
        tracking=True,
        help="เลขที่เอกสารที่ระบบ GFMIS ออกให้หลังบันทึก เช่น 31XXXXXXXX",
        index=True,
    )

    # ข้อมูลทั่วไป
    fund_type = fields.Selection(
        [
            ("budget", "เงินงบประมาณ"),
            ("reserved", "เงินกันไว้เบิกเหลื่อมปี"),
            ("extra", "เงินนอกงบประมาณ"),
            ("loan", "เงินกู้"),
            ("allocated", "เงินรายได้จัดสรร"),
        ],
        string="ประเภทรายการขอเบิก / แหล่งเงิน",
        default="budget",
        required=True,
        tracking=True,
    )
    payment_method = fields.Selection(
        [
            ("direct", "จ่ายตรงผู้ขาย"),
            ("through", "จ่ายผ่านส่วนราชการ"),
        ],
        string="วิธีการชำระเงิน",
        default="direct",
        required=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="เจ้าหนี้ / ผู้มีสิทธิรับเงิน",
        required=True,
        tracking=True,
        check_company=True,
    )
    vat = fields.Char(related="partner_id.vat", string="เลขประจำตัวผู้เสียภาษี")
    partner_bank_id = fields.Many2one(
        "res.partner.bank",
        string="บัญชีเงินฝากธนาคารผู้รับเงิน",
        domain="[('partner_id', '=', partner_id)]",
        check_company=True,
    )
    company_bank_id = fields.Many2one(
        "res.partner.bank",
        string="บัญชีธนาคารโรงพยาบาล",
        help="ใช้เมื่อจ่ายผ่านส่วนราชการ เงินเข้าบัญชีของหน่วยงานก่อนจ่ายต่อ",
        domain="[('partner_id', '=', company_partner_id)]",
        check_company=True,
    )
    description = fields.Char(string="คำอธิบายเอกสาร", size=99)

    # ERP links
    purchase_id = fields.Many2one(
        "purchase.order",
        string="ใบสั่งซื้อ ERP",
        check_company=True,
        tracking=True,
    )
    invoice_id = fields.Many2one(
        "account.move",
        string="ใบแจ้งหนี้ผู้ขาย ERP",
        domain="[('move_type', 'in', ('in_invoice', 'in_refund')), ('partner_id', '=', partner_id)]",
        check_company=True,
        tracking=True,
        index=True,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="การจ่ายชำระ ERP",
        check_company=True,
        tracking=True,
    )
    source_document_id = fields.Many2one(
        "gfmis.document",
        string="เอกสาร GFMIS อ้างอิง",
        help="ใช้กับใบลดหนี้ ขจ.05 หรือเบิกเกินส่งคืน ที่อ้างเอกสารขอเบิกเดิม",
        index=True,
    )

    line_ids = fields.One2many(
        "gfmis.document.line",
        "document_id",
        string="รายการขอเบิก",
        copy=True,
    )
    wht_ids = fields.One2many(
        "gfmis.document.wht",
        "document_id",
        string="ภาษีหัก ณ ที่จ่าย / ค่าปรับ",
        copy=True,
    )

    amount_untaxed = fields.Monetary(
        string="ยอดรายการ",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    amount_wht = fields.Monetary(
        string="ภาษีหัก ณ ที่จ่าย",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    amount_penalty = fields.Monetary(
        string="ค่าปรับ",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    amount_net = fields.Monetary(
        string="ยอดสุทธิจ่าย",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )

    note = fields.Text(string="หมายเหตุ")
    gfmis_message = fields.Text(
        string="ผลการตรวจสอบ GFMIS",
        help="รหัสข้อความ / คำอธิบายจากการจำลองบันทึกใน GFMIS",
    )

    @api.depends("document_date")
    def _compute_period(self):
        for rec in self:
            rec.period = rec.document_date.strftime("%m/%Y") if rec.document_date else False

    @api.depends("line_ids.amount", "wht_ids.wht_amount", "wht_ids.penalty_amount")
    def _compute_amounts(self):
        for rec in self:
            rec.amount_untaxed = sum(rec.line_ids.mapped("amount"))
            rec.amount_wht = sum(rec.wht_ids.mapped("wht_amount"))
            rec.amount_penalty = sum(rec.wht_ids.mapped("penalty_amount"))
            rec.amount_net = rec.amount_untaxed - rec.amount_wht - rec.amount_penalty

    @api.onchange("company_id")
    def _onchange_company_id(self):
        company = self.company_id
        if company:
            self.agency_code = company.gfmis_agency_code
            self.area_code = company.gfmis_area_code
            self.disbursing_unit_code = company.gfmis_disbursing_unit_code

    @api.onchange("form_type_id")
    def _onchange_form_type_id(self):
        form = self.form_type_id
        if not form:
            return
        self.doc_class = form.doc_class
        if form.fund_type and form.fund_type != "any":
            mapping = {"budget": "budget", "extra": "extra", "loan": "loan", "allocated": "allocated"}
            self.fund_type = mapping.get(form.fund_type, self.fund_type)
        if form.payment_method == "direct":
            self.payment_method = "direct"
        elif form.payment_method == "through":
            self.payment_method = "through"

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            banks = self.partner_id.bank_ids.filtered("active")
            self.partner_bank_id = banks[:1]
        else:
            self.partner_bank_id = False

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        invoice = self.invoice_id
        if not invoice:
            return
        self.partner_id = invoice.partner_id
        self.reference = invoice.ref or invoice.name
        self.purchase_id = invoice.invoice_line_ids.purchase_line_id.order_id[:1]
        if invoice.invoice_date:
            self.document_date = invoice.invoice_date
        if not self.line_ids:
            lines = []
            for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
                lines.append(
                    (
                        0,
                        0,
                        {
                            "name": line.name,
                            "quantity": line.quantity,
                            "price_unit": line.price_unit,
                            "amount": line.price_subtotal,
                            "invoice_line_id": line.id,
                            "purchase_line_id": line.purchase_line_id.id,
                        },
                    )
                )
            self.line_ids = lines

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company = self.env["res.company"].browse(vals.get("company_id") or self.env.company.id)
            vals.setdefault("agency_code", company.gfmis_agency_code)
            vals.setdefault("area_code", company.gfmis_area_code)
            vals.setdefault("disbursing_unit_code", company.gfmis_disbursing_unit_code)
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("gfmis.document") or "/"
        return super().create(vals_list)

    @api.constrains("form_type_id", "purchase_id", "gfmis_po_number")
    def _check_requires_po(self):
        for rec in self:
            if rec.form_type_id.requires_po and rec.state != "cancelled":
                if not rec.purchase_id and not rec.gfmis_po_number:
                    raise ValidationError(
                        _("แบบฟอร์ม %s ต้องอ้างใบสั่งซื้อสั่งจ้าง (PO ใน ERP หรือเลขที่ PO ของ GFMIS)")
                        % rec.form_type_id.code
                    )

    def _ensure_draftish(self, allowed):
        for rec in self:
            if rec.state not in allowed:
                raise UserError(_("ไม่สามารถทำรายการนี้ในสถานะ %s") % rec.state)

    def action_record_gfmis(self):
        self._ensure_draftish(("draft",))
        for rec in self:
            if not rec.line_ids and rec.doc_class == "request":
                raise UserError(_("กรุณาบันทึกรายการขอเบิกอย่างน้อย 1 บรรทัด"))
            rec.state = "recorded"
            rec.message_post(
                body=_("บันทึกเอกสารในกระบวนการ GFMIS แล้ว กรอกเลขที่เอกสาร GFMIS เมื่อระบบออกเลขให้")
            )

    def action_submit_approve(self):
        self._ensure_draftish(("recorded",))
        self.write({"state": "wait_approve_request"})
        self.message_post(body=_("ส่งรออนุมัติขอเบิก (อม.01)"))

    def action_approve_request(self):
        """อม.01 อนุมัติเอกสารขอเบิก"""
        self._ensure_draftish(("wait_approve_request",))
        self.write({"state": "wait_approve_pay"})
        self.message_post(body=_("อนุมัติขอเบิก (อม.01) แล้ว"))

    def action_approve_pay(self):
        """อม.02 อนุมัติเอกสารเพื่อสั่งจ่าย"""
        self._ensure_draftish(("wait_approve_pay",))
        self.write({"state": "sent_treasury"})
        self.message_post(body=_("อนุมัติสั่งจ่าย (อม.02) แล้ว ส่งกรมบัญชีกลาง/คลังจังหวัด"))

    def action_mark_paid(self):
        self._ensure_draftish(("sent_treasury", "wait_agency_pay"))
        for rec in self:
            if rec.payment_method == "through" and rec.state == "sent_treasury":
                rec.state = "wait_agency_pay"
                rec.message_post(body=_("เงินเข้าบัญชีส่วนราชการแล้ว รอจ่ายให้ผู้มีสิทธิ (ขจ.05)"))
            elif rec.payment_method == "through":
                rec.state = "agency_paid"
                rec.message_post(body=_("จ่ายให้ผู้มีสิทธิแล้ว"))
            else:
                rec.state = "paid"
                rec.message_post(body=_("กรมบัญชีกลางประมวลผลจ่ายตรงผู้ขายแล้ว"))

    def action_mark_returned(self):
        self._ensure_draftish(("paid", "agency_paid", "wait_agency_pay", "sent_treasury"))
        self.write({"state": "returned"})
        self.message_post(body=_("บันทึกเบิกเกินส่งคืน"))

    def action_cancel(self):
        self._ensure_draftish(("draft", "recorded", "wait_approve_request", "wait_approve_pay"))
        self.write({"state": "cancelled"})

    def action_draft(self):
        self._ensure_draftish(("cancelled", "recorded"))
        self.write({"state": "draft"})

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def action_create_from_invoice(self, invoice):
        invoice.ensure_one()
        if invoice.move_type not in ("in_invoice", "in_refund"):
            raise UserError(_("สร้างเอกสาร GFMIS ได้เฉพาะใบแจ้งหนี้ / ใบลดหนี้ผู้ขาย"))
        existing = self.search([("invoice_id", "=", invoice.id)], limit=1)
        if existing:
            return existing
        form_code = "ขบ.01" if invoice.invoice_line_ids.purchase_line_id else "ขบ.02"
        if invoice.move_type == "in_refund":
            form_code = "ขบ.23" if invoice.invoice_line_ids.purchase_line_id else "ขบ.24"
        form = self.env["gfmis.form.type"].search([("code", "=", form_code)], limit=1)
        if not form:
            form = self.env["gfmis.form.type"].search([("doc_class", "=", "request")], limit=1)
        lines = []
        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
            lines.append(
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                        "amount": line.price_subtotal,
                        "invoice_line_id": line.id,
                        "purchase_line_id": line.purchase_line_id.id,
                    },
                )
            )
        return self.create(
            {
                "doc_class": "request" if invoice.move_type == "in_invoice" else "request",
                "form_type_id": form.id,
                "partner_id": invoice.partner_id.id,
                "invoice_id": invoice.id,
                "purchase_id": invoice.invoice_line_ids.purchase_line_id.order_id[:1].id,
                "reference": invoice.ref or invoice.name,
                "document_date": invoice.invoice_date or fields.Date.context_today(self),
                "posting_date": invoice.date or fields.Date.context_today(self),
                "description": (invoice.payment_reference or invoice.narration or invoice.name or "")[:99],
                "line_ids": lines,
                "payment_method": "direct",
            }
        )


class GfmisDocumentLine(models.Model):
    _name = "gfmis.document.line"
    _description = "บรรทัดรายการขอเบิก GFMIS"
    _order = "id"

    document_id = fields.Many2one(
        "gfmis.document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="document_id.company_id", store=True)
    currency_id = fields.Many2one(related="document_id.currency_id")
    name = fields.Char(string="รายการ", required=True)
    quantity = fields.Float(string="จำนวน", default=1.0)
    price_unit = fields.Monetary(string="ราคาต่อหน่วย", currency_field="currency_id")
    amount = fields.Monetary(string="จำนวนเงิน", currency_field="currency_id")
    fund_source_code = fields.Char(string="รหัสแหล่งของเงิน")
    activity_code = fields.Char(string="รหัสกิจกรรมหลัก")
    budget_code = fields.Char(string="รหัสงบประมาณ")
    purchase_line_id = fields.Many2one("purchase.order.line", string="บรรทัด PO")
    invoice_line_id = fields.Many2one("account.move.line", string="บรรทัดใบแจ้งหนี้")

    @api.onchange("quantity", "price_unit")
    def _onchange_amount(self):
        self.amount = (self.quantity or 0.0) * (self.price_unit or 0.0)


class GfmisDocumentWht(models.Model):
    _name = "gfmis.document.wht"
    _description = "ภาษีหัก ณ ที่จ่าย / ค่าปรับ GFMIS"

    document_id = fields.Many2one(
        "gfmis.document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    currency_id = fields.Many2one(related="document_id.currency_id")
    person_type = fields.Selection(
        [
            ("individual", "บุคคลธรรมดา"),
            ("company", "นิติบุคคล"),
        ],
        string="ภาษีเงินได้",
        default="company",
        required=True,
    )
    wht_base = fields.Monetary(string="ฐานคำนวณภาษี", currency_field="currency_id")
    wht_amount = fields.Monetary(string="จำนวนเงินที่หักไว้ (ภาษี)", currency_field="currency_id")
    penalty_type = fields.Selection(
        [
            ("land", "รายได้ของแผ่นดิน"),
            ("agency", "รายได้ของหน่วยงาน"),
        ],
        string="ค่าปรับ",
    )
    penalty_base = fields.Monetary(string="ฐานคำนวณค่าปรับ", currency_field="currency_id")
    penalty_amount = fields.Monetary(string="จำนวนเงินค่าปรับ", currency_field="currency_id")
    note = fields.Char(string="หมายเหตุ")
