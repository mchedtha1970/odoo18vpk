# -*- coding: utf-8 -*-
import base64
import io
import re
from pathlib import Path

from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_path

_REPORT_FONT_CSS = None

THAI_MONTHS = (
    "",
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
)


class GfmisDocument(models.Model):
    _name = "gfmis.document"
    _description = "เอกสารกระบวนการ GFMIS"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "document_date desc, id desc"
    _check_company_auto = True

    _VPK_WHT_RATE = 0.01
    _VPK_WHT_NOTE = "หักภาษี ณ ที่จ่าย 1%"

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
            ("recorded", "รอส่งอนุมัติขอเบิก"),
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
    dika_number = fields.Char(string="ฎีกาที่", tracking=True, index=True)
    transfer_date = fields.Date(string="วันที่โอน", tracking=True, index=True)
    wht_cert_number = fields.Char(
        string="เลขที่หนังสือรับรองหักภาษี",
        copy=False,
        tracking=True,
        help="เลขที่ใบรับรองการหักภาษี ณ ที่จ่าย (แบบ 4235) เช่น 7240/2567",
    )
    wht_income_type = fields.Char(
        string="ประเภทเงินได้ที่จ่าย",
        help="ระบุในใบหักภาษี ณ ที่จ่าย เช่น ค่ายา / ค่าบริการ",
        default="ค่าสินค้า/บริการ",
    )

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

    @api.depends(
        "line_ids.amount",
        "line_ids.include_in_payment",
        "wht_ids.wht_amount",
        "wht_ids.penalty_amount",
    )
    def _compute_amounts(self):
        for rec in self:
            rec.amount_untaxed = rec._vpk_selected_amount()
            rec.amount_wht = sum(rec.wht_ids.mapped("wht_amount"))
            rec.amount_penalty = sum(rec.wht_ids.mapped("penalty_amount"))
            rec.amount_net = rec.amount_untaxed - rec.amount_wht - rec.amount_penalty

    def _vpk_selected_lines(self):
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.include_in_payment)

    def _vpk_selected_amount(self):
        self.ensure_one()
        return sum(self._vpk_selected_lines().mapped("amount"))

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

    @api.model
    def _vpk_wht_person_type(self, partner):
        if partner and not partner.is_company:
            return "individual"
        return "company"

    @api.model
    def _prepare_wht_commands(self, base_amount, partner=None, currency=None):
        base = base_amount or 0.0
        if base <= 0:
            return []
        currency = currency or self.env.company.currency_id
        return [
            (
                0,
                0,
                {
                    "person_type": self._vpk_wht_person_type(partner),
                    "wht_base": base,
                    "wht_amount": currency.round(base * self._VPK_WHT_RATE),
                    "note": self._VPK_WHT_NOTE,
                },
            )
        ]

    def _vpk_apply_default_wht_onchange(self):
        self.ensure_one()
        auto = self.wht_ids.filtered(lambda rec: (rec.note or "") == self._VPK_WHT_NOTE)
        others = self.wht_ids - auto
        if others.filtered(lambda rec: rec.wht_amount or rec.wht_base) and not auto:
            return
        commands = self._prepare_wht_commands(
            self._vpk_selected_amount(),
            self.partner_id,
            self.currency_id,
        )
        keep = [
            (
                0,
                0,
                {
                    "person_type": line.person_type,
                    "wht_base": line.wht_base,
                    "wht_amount": line.wht_amount,
                    "penalty_type": line.penalty_type,
                    "penalty_base": line.penalty_base,
                    "penalty_amount": line.penalty_amount,
                    "note": line.note,
                },
            )
            for line in others
        ]
        self.wht_ids = commands + keep

    def _vpk_sync_default_wht(self):
        """ปรับหักภาษี ณ ที่จ่าย 1% ตามยอดบรรทัดที่เลือกเบิก."""
        for rec in self:
            if rec.doc_class != "request" or rec.state != "draft":
                continue
            auto = rec.wht_ids.filtered(lambda item: (item.note or "") == rec._VPK_WHT_NOTE)
            custom = (rec.wht_ids - auto).filtered(lambda item: item.wht_amount or item.wht_base)
            if custom and not auto:
                continue
            commands = rec._prepare_wht_commands(
                rec._vpk_selected_amount(),
                rec.partner_id,
                rec.currency_id,
            )
            if auto:
                if commands:
                    auto[:1].write(commands[0][2])
                    extra = auto[1:]
                    if extra:
                        extra.unlink()
                else:
                    auto.unlink()
            elif commands:
                rec.write({"wht_ids": commands})

    def _vpk_ensure_default_wht(self):
        self._vpk_sync_default_wht()

    @api.model
    def _vpk_backfill_default_wht(self):
        docs = self.search(
            [
                ("doc_class", "=", "request"),
                ("state", "=", "draft"),
                ("wht_ids", "=", False),
            ]
        )
        docs._vpk_ensure_default_wht()

    @api.onchange("purchase_id")
    def _onchange_purchase_id(self):
        order = self.purchase_id
        if not order:
            return
        if not self.partner_id:
            self.partner_id = order.partner_id
        if not self.reference:
            self.reference = order.name
        if not self.line_ids:
            self.line_ids = self._prepare_lines_from_purchase(order)
        self._vpk_apply_default_wht_onchange()

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
            self.line_ids = self._prepare_lines_from_invoice(invoice)
        self._vpk_apply_default_wht_onchange()

    @api.model
    def _receipt_doc_number_from_invoice(self, invoice):
        """เลขที่ใบตรวจรับที่ผูกกับใบแจ้งหนี้ผู้ขาย."""
        wa = invoice.wa_id if "wa_id" in invoice._fields else invoice.env["work.acceptance"]
        if not wa and "wa_ids" in invoice.invoice_line_ids.purchase_line_id.order_id._fields:
            wa = invoice.invoice_line_ids.purchase_line_id.order_id.wa_ids.filtered(
                lambda rec: rec.state == "accept"
            )[:1]
        name = (wa.name or "").strip() if wa else ""
        if not name or name in ("New", "/"):
            return False
        return name

    @api.model
    def _prepare_lines_from_invoice(self, invoice):
        receipt_doc_number = self._receipt_doc_number_from_invoice(invoice)
        lines = []
        for line in invoice.invoice_line_ids.filtered(lambda item: item.display_type == "product"):
            lines.append(
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                        "amount": line.price_subtotal,
                        "receipt_doc_number": receipt_doc_number,
                        "bill_number": invoice.ref or invoice.name or False,
                        "invoice_line_id": line.id,
                        "purchase_line_id": line.purchase_line_id.id,
                        "include_in_payment": True,
                    },
                )
            )
        return lines

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company = self.env["res.company"].browse(vals.get("company_id") or self.env.company.id)
            vals.setdefault("agency_code", company.gfmis_agency_code)
            vals.setdefault("area_code", company.gfmis_area_code)
            vals.setdefault("disbursing_unit_code", company.gfmis_disbursing_unit_code)
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("gfmis.document") or "/"
        records = super().create(vals_list)
        records._vpk_ensure_default_wht()
        return records

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

    def _vpk_accepted_wa(self):
        self.ensure_one()
        order = self.purchase_id
        if order and "wa_ids" in order._fields:
            return order.wa_ids.filtered(lambda rec: rec.state == "accept")[:1]
        return self.env["work.acceptance"] if "work.acceptance" in self.env else False

    def _vpk_bill_expense_account(self, product=None):
        self.ensure_one()
        if product:
            accounts = product.product_tmpl_id.with_company(self.company_id)._get_product_accounts()
            if accounts.get("expense"):
                return accounts["expense"].id
        journal = self.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", self.company_id.id)],
            limit=1,
        )
        if journal.default_account_id:
            return journal.default_account_id.id
        Account = self.env["account.account"]
        domain = [("account_type", "=", "expense")]
        if "company_ids" in Account._fields:
            domain.append(("company_ids", "in", [self.company_id.id]))
        elif "company_id" in Account._fields:
            domain.append(("company_id", "=", self.company_id.id))
        account = Account.search(domain, limit=1)
        if not account:
            raise UserError(_("ไม่พบบัญชีค่าใช้จ่ายสำหรับสร้างใบแจ้งหนี้ กรุณาตรวจสอบผังบัญชี"))
        return account.id

    def _vpk_prepare_bill_line_vals(self, line):
        self.ensure_one()
        qty = line.quantity or 1.0
        price = line.price_unit
        if not price and qty:
            price = (line.amount or 0.0) / qty
        po_line = line.purchase_line_id
        if po_line:
            vals = po_line._prepare_account_move_line()
            vals.update({
                "name": line.name or vals.get("name") or "/",
                "quantity": qty,
                "price_unit": price,
            })
            return vals
        return {
            "name": line.name or "/",
            "quantity": qty,
            "price_unit": price,
            "display_type": "product",
            "account_id": self._vpk_bill_expense_account(),
        }

    def _vpk_ensure_vendor_bill(self):
        """สร้างใบแจ้งหนี้ผู้ขายจากบรรทัดที่เลือกเบิก ถ้ายังไม่มีใบแจ้งหนี้ผูกไว้"""
        self.ensure_one()
        if self.doc_class != "request":
            return self.invoice_id
        if self.invoice_id and self.invoice_id.state != "cancel":
            return self.invoice_id
        linked = self._vpk_selected_lines().mapped("invoice_line_id").move_id.filtered(
            lambda move: move.move_type in ("in_invoice", "in_refund") and move.state != "cancel"
        )
        if linked:
            self.invoice_id = linked[:1]
            return self.invoice_id
        return self._vpk_create_vendor_bill()

    def _vpk_create_vendor_bill(self):
        self.ensure_one()
        selected = self._vpk_selected_lines()
        if not selected:
            raise UserError(_("กรุณาเลือกบรรทัดที่จะเบิกอย่างน้อย 1 รายการ"))
        wa = self._vpk_accepted_wa()
        prepare_doc = self.with_context(wa_id=wa.id) if wa else self
        vals = {
            "move_type": "in_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": self.document_date,
            "date": self.posting_date or self.document_date,
            "ref": self.reference or self.name,
            "invoice_origin": " / ".join(part for part in (self.purchase_id.name, self.name) if part),
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "narration": self.description or False,
            "invoice_line_ids": [
                Command.create(prepare_doc._vpk_prepare_bill_line_vals(line)) for line in selected
            ],
        }
        if self.partner_bank_id:
            vals["partner_bank_id"] = self.partner_bank_id.id
        if wa and "wa_id" in self.env["account.move"]._fields:
            vals["wa_id"] = wa.id
            if wa.name:
                vals["ref"] = "%s / %s" % (vals["ref"], wa.name) if vals.get("ref") else wa.name
        try:
            move = self.env["account.move"].with_company(self.company_id).with_context(
                default_move_type="in_invoice",
                wa_id=wa.id if wa else False,
            ).create(vals)
        except (UserError, ValidationError):
            raise
        except Exception as err:
            raise UserError(_("ไม่สามารถสร้างใบแจ้งหนี้ได้: %s") % err) from err
        bill_lines = move.invoice_line_ids.filtered(lambda aml: aml.display_type == "product")
        for gf_line, bill_line in zip(selected, bill_lines):
            gf_line.write({
                "invoice_line_id": bill_line.id,
                "bill_number": gf_line.bill_number or move.ref or move.name,
            })
        self.invoice_id = move
        return move

    def action_record_gfmis(self):
        """สร้างใบแจ้งหนี้ฉบับร่าง (ยังไม่ post) แล้วส่งรออนุมัติขอเบิก"""
        self._ensure_draftish(("draft", "recorded"))
        for rec in self:
            if rec.doc_class == "request" and not rec._vpk_selected_lines():
                raise UserError(_("กรุณาเลือกบรรทัดที่จะเบิกอย่างน้อย 1 รายการ"))
            bill = rec._vpk_ensure_vendor_bill()
            if bill and bill.state == "posted":
                raise UserError(
                    _("ใบแจ้งหนี้ %s ลงรายการแล้ว กรุณาใช้ใบแจ้งหนี้ฉบับร่าง")
                    % (bill.name or bill.display_name)
                )
            rec.state = "wait_approve_request"
            if bill:
                rec.message_post(
                    body=_(
                        "สร้างใบแจ้งหนี้ฉบับร่าง %s แล้ว ส่งรออนุมัติขอเบิก (อม.01)"
                    )
                    % (bill.name or bill.ref or bill.display_name)
                )
            else:
                rec.message_post(body=_("ส่งรออนุมัติขอเบิก (อม.01)"))

    def action_submit_approve(self):
        """รองรับเอกสารเก่าที่ค้างสถานะบันทึก — ไปรออนุมัติขอเบิก"""
        return self.action_record_gfmis()

    def action_approve_request(self):
        """อม.01 อนุมัติเอกสารขอเบิก และ post ใบแจ้งหนี้"""
        self._ensure_draftish(("wait_approve_request",))
        for rec in self:
            bill = rec.invoice_id
            if not bill or bill.state == "cancel":
                bill = rec._vpk_ensure_vendor_bill()
            if bill and bill.state == "draft":
                try:
                    bill.action_post()
                except (UserError, ValidationError):
                    raise
                except Exception as err:
                    raise UserError(_("ไม่สามารถลงรายการใบแจ้งหนี้ได้: %s") % err) from err
            rec.state = "wait_approve_pay"
            if bill:
                rec.message_post(
                    body=_("อนุมัติขอเบิก (อม.01) แล้ว และลงรายการใบแจ้งหนี้ %s")
                    % (bill.name or bill.display_name)
                )
            else:
                rec.message_post(body=_("อนุมัติขอเบิก (อม.01) แล้ว"))

    def action_approve_pay(self):
        """อม.02 อนุมัติเอกสารเพื่อสั่งจ่าย"""
        self._ensure_draftish(("wait_approve_pay",))
        self.write({"state": "sent_treasury"})
        self.message_post(body=_("อนุมัติสั่งจ่าย (อม.02) แล้ว ส่งกรมบัญชีกลาง/คลังจังหวัด"))

    def action_reject_approval(self, reason, from_state=None):
        """ไม่อนุมัติ อม.01 / อม.02 พร้อมเหตุผล"""
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("กรุณาระบุเหตุผลไม่อนุมัติ"))
        for rec in self:
            state = from_state or rec.state
            if state == "wait_approve_request":
                rec._ensure_draftish(("wait_approve_request",))
                had_bill = bool(rec.invoice_id)
                rec._vpk_unlink_draft_bill()
                rec.state = "draft"
                body = _("ไม่อนุมัติขอเบิก (อม.01): %s") % reason
                if had_bill:
                    body = _("%s และลบใบแจ้งหนี้ฉบับร่าง") % body
                rec.message_post(body=body)
            elif state == "wait_approve_pay":
                rec._ensure_draftish(("wait_approve_pay",))
                rec.state = "wait_approve_request"
                rec.message_post(body=_("ไม่อนุมัติสั่งจ่าย (อม.02): %s") % reason)
            else:
                raise UserError(
                    _("ไม่อนุมัติได้เฉพาะรายการที่รออนุมัติขอเบิก (อม.01) หรือรออนุมัติสั่งจ่าย (อม.02)")
                )

    def action_open_approve_wizard(self):
        docs = self or self.browse(self.env.context.get("active_ids") or [])
        if not docs:
            raise UserError(_("กรุณาเลือกรายการใบเบิกเงินอย่างน้อย 1 รายการ"))
        self.env["gfmis.document.approve.wizard"]._vpk_check_same_approvable_state(docs)
        return {
            "type": "ir.actions.act_window",
            "name": _("อนุมัติ / ไม่อนุมัติ"),
            "res_model": "gfmis.document.approve.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_ids": docs.ids,
                "active_id": docs[:1].id,
                "default_document_ids": [(6, 0, docs.ids)],
            },
        }

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

    def _vpk_unlink_draft_bill(self):
        """ตัดลิงก์และลบใบแจ้งหนี้ฉบับร่างที่สร้างจากใบเบิก"""
        for rec in self:
            bill = rec.invoice_id
            rec.line_ids.write({"invoice_line_id": False, "bill_number": False})
            if not bill:
                continue
            rec.invoice_id = False
            if bill.state == "posted":
                continue
            if bill.state not in ("draft", "cancel"):
                bill.button_cancel()
            if bill.state in ("draft", "cancel"):
                bill.with_context(force_delete=True).unlink()

    def action_draft(self):
        self._ensure_draftish(("cancelled", "recorded", "wait_approve_request"))
        had_bill = bool(self.filtered("invoice_id"))
        self._vpk_unlink_draft_bill()
        self.write({"state": "draft"})
        if had_bill:
            self.message_post(body=_("ถอยเป็นร่างแล้ว และลบใบแจ้งหนี้ฉบับร่างที่สร้างจากใบเบิก"))
        else:
            self.message_post(body=_("ถอยเป็นร่างแล้ว"))

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
    def _vpk_vat_digit_list(self, vat):
        digits = [c for c in (vat or "") if c.isdigit()]
        digits = (digits + [""] * 13)[:13]
        return digits

    @api.model
    def _vpk_split_baht_satang(self, amount):
        value = abs(amount or 0.0)
        baht = int(value)
        satang = int(round((value - baht) * 100))
        if satang >= 100:
            baht += satang // 100
            satang = satang % 100
        return baht, satang

    def _vpk_partner_address_text(self, partner):
        partner = partner.sudo()
        parts = [
            partner.street or "",
            partner.street2 or "",
            partner.city or "",
            partner.state_id.name if partner.state_id else "",
            partner.zip or "",
        ]
        return " ".join(part for part in parts if part).strip()

    def _vpk_amount_to_thai_text(self, amount):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        try:
            text = currency.with_context(lang="th_TH").amount_to_text(amount or 0.0)
        except Exception:
            text = currency.amount_to_text(amount or 0.0)
        return (text or "").strip()

    def _vpk_ensure_wht_cert_number(self):
        today = fields.Date.context_today(self)
        year_be = today.year + 543
        for rec in self:
            if rec.wht_cert_number:
                continue
            seq = self.env["ir.sequence"].next_by_code("gfmis.wht.cert") or str(rec.id)
            rec.wht_cert_number = "%s/%s" % (seq, year_be)

    def action_print_wht_cert(self):
        docs = self.filtered(lambda rec: rec.doc_class == "request")
        if not docs:
            raise UserError(_("พิมพ์ใบหักภาษี ณ ที่จ่ายได้เฉพาะเอกสารขอเบิกเงิน"))
        if docs.filtered(lambda rec: not rec.wht_ids and not rec.amount_wht):
            raise UserError(_("ไม่พบยอดภาษีหัก ณ ที่จ่ายในเอกสารที่เลือก"))
        docs._vpk_ensure_wht_cert_number()
        return self.env.ref("vpk_gfmis.action_report_gfmis_wht_cert").report_action(docs)

    @api.model
    def _vpk_report_font_css(self):
        """TH Sarabun New แบบ data-URI ให้ wkhtmltopdf ฝังฟอนต์ราชการได้โดยไม่ต้องโหลดผ่านเครือข่าย"""
        global _REPORT_FONT_CSS
        if _REPORT_FONT_CSS is None:
            module_path = get_module_path("vpk_tier_validation")
            path = Path(module_path) / "static/src/scss/thai_fonts_embedded.scss" if module_path else None
            css = path.read_text(encoding="utf-8") if path and path.is_file() else ""
            # ไฟล์ตัวหนาทำให้สระ/วรรณยุกต์เยื้องในโปรแกรมเปิด PDF บางตัว ใช้เฉพาะตัวปกติ
            css = re.sub(
                r'@font-face\s*\{[^}]*"THSarabunNew-Bold"[^}]*\}',
                "",
                css,
            )
            _REPORT_FONT_CSS = Markup(css)
        return _REPORT_FONT_CSS

    @api.model
    def _vpk_wht_cert_garuda_src(self):
        module_path = get_module_path("vpk_gfmis")
        if not module_path:
            return ""
        image_path = Path(module_path) / "static" / "src" / "img" / "garuda.jpeg"
        if not image_path.is_file():
            return ""
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return "data:image/jpeg;base64,%s" % encoded

    def _vpk_wht_cert_report_values(self):
        """ข้อมูลสำหรับรายงานใบรับรองการหักภาษี ณ ที่จ่าย (แบบ 4235)"""
        self.ensure_one()
        if not self.wht_cert_number:
            self._vpk_ensure_wht_cert_number()
        company = self.company_id
        company_partner = company.partner_id
        pay_date = self.transfer_date or self.posting_date or self.document_date
        company_wht = self.wht_ids.filtered(lambda line: line.person_type == "company")
        individual_wht = self.wht_ids.filtered(lambda line: line.person_type == "individual")
        if not company_wht and not individual_wht and self.amount_wht:
            # fallback จากยอดรวมเมื่อยังไม่มีบรรทัดย่อย
            if self._vpk_wht_person_type(self.partner_id) == "individual":
                individual_wht_base = self.amount_untaxed
                individual_wht_tax = self.amount_wht
                company_wht_base = company_wht_tax = 0.0
            else:
                company_wht_base = self.amount_untaxed
                company_wht_tax = self.amount_wht
                individual_wht_base = individual_wht_tax = 0.0
        else:
            company_wht_base = sum(company_wht.mapped("wht_base"))
            company_wht_tax = sum(company_wht.mapped("wht_amount"))
            individual_wht_base = sum(individual_wht.mapped("wht_base"))
            individual_wht_tax = sum(individual_wht.mapped("wht_amount"))
        penalty_base = sum(self.wht_ids.mapped("penalty_base")) or 0.0
        penalty_amount = self.amount_penalty or sum(self.wht_ids.mapped("penalty_amount"))
        total_tax = company_wht_tax + individual_wht_tax + penalty_amount
        company_base_b, company_base_s = self._vpk_split_baht_satang(company_wht_base)
        company_tax_b, company_tax_s = self._vpk_split_baht_satang(company_wht_tax)
        ind_base_b, ind_base_s = self._vpk_split_baht_satang(individual_wht_base)
        ind_tax_b, ind_tax_s = self._vpk_split_baht_satang(individual_wht_tax)
        pen_base_b, pen_base_s = self._vpk_split_baht_satang(penalty_base)
        pen_tax_b, pen_tax_s = self._vpk_split_baht_satang(penalty_amount)
        total_base = company_wht_base + individual_wht_base + penalty_base
        total_base_b, total_base_s = self._vpk_split_baht_satang(total_base)
        total_tax_b, total_tax_s = self._vpk_split_baht_satang(total_tax)
        income_type = (self.wht_income_type or self.description or "ค่าสินค้า/บริการ").strip()
        disbursement_no = self.gfmis_doc_number or self.dika_number or self.name or ""
        doc_date = self.document_date
        purchase = self.purchase_id.sudo()
        contract_date = purchase.date_approve or purchase.date_order if purchase else False
        is_individual = self._vpk_wht_person_type(self.partner_id) == "individual"
        partner_vat = self._vpk_vat_digit_list(self.partner_id.vat)
        empty_digits = [""] * 13
        return {
            "garuda_src": self._vpk_wht_cert_garuda_src(),
            "company_name": company.name or "",
            "company_vat_digits": self._vpk_vat_digit_list(company_partner.vat or company.vat),
            "company_address": self._vpk_partner_address_text(company_partner),
            "partner_name": self.partner_id.name or "",
            "partner_vat_digits": empty_digits if is_individual else partner_vat,
            "partner_citizen_digits": partner_vat if is_individual else empty_digits,
            "partner_address": self._vpk_partner_address_text(self.partner_id),
            "cert_number": self.wht_cert_number or "",
            "disbursement_number": disbursement_no,
            "doc_day": doc_date.day if doc_date else "",
            "doc_month": THAI_MONTHS[doc_date.month] if doc_date else "",
            "doc_year_be": (doc_date.year + 543) if doc_date else "",
            "contract_number": purchase.name if purchase else "",
            "contract_day": contract_date.day if contract_date else "",
            "contract_month": THAI_MONTHS[contract_date.month] if contract_date else "",
            "contract_year_be": (contract_date.year + 543) if contract_date else "",
            "pay_date_text": (
                "%d/%d/%d" % (pay_date.day, pay_date.month, pay_date.year + 543) if pay_date else ""
            ),
            "income_type": income_type,
            "company_base_baht": "{:,}".format(company_base_b) if company_wht_base else "",
            "company_base_satang": "%02d" % company_base_s if company_wht_base else "",
            "company_tax_baht": "{:,}".format(company_tax_b) if company_wht_tax else "",
            "company_tax_satang": "%02d" % company_tax_s if company_wht_tax else "",
            "individual_base_baht": "{:,}".format(ind_base_b) if individual_wht_base else "",
            "individual_base_satang": "%02d" % ind_base_s if individual_wht_base else "",
            "individual_tax_baht": "{:,}".format(ind_tax_b) if individual_wht_tax else "",
            "individual_tax_satang": "%02d" % ind_tax_s if individual_wht_tax else "",
            "penalty_base_baht": "{:,}".format(pen_base_b) if penalty_amount or penalty_base else "",
            "penalty_base_satang": "%02d" % pen_base_s if penalty_amount or penalty_base else "",
            "penalty_tax_baht": "{:,}".format(pen_tax_b) if penalty_amount else "",
            "penalty_tax_satang": "%02d" % pen_tax_s if penalty_amount else "",
            "total_base_baht": "{:,}".format(total_base_b) if total_base else "",
            "total_base_satang": "%02d" % total_base_s if total_base else "",
            "total_tax_baht": "{:,}".format(total_tax_b) if total_tax else "",
            "total_tax_satang": "%02d" % total_tax_s if total_tax else "",
            "tax_amount_text": self._vpk_amount_to_thai_text(total_tax),
            "signer_name": company.gfmis_wht_signer_name or "",
            "signer_position": company.gfmis_wht_signer_position or "",
        }

    @api.model
    def _prepare_lines_from_purchase(self, order):
        wa = False
        if "wa_ids" in order._fields:
            wa = order.wa_ids.filtered(lambda rec: rec.state == "accept")[:1]
        receipt = (wa.name or "").strip() if wa else ""
        if receipt in ("New", "/"):
            receipt = ""
        lines = []
        for line in order.order_line.filtered(lambda item: not item.display_type):
            lines.append(
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "quantity": line.product_qty,
                        "price_unit": line.price_unit,
                        "amount": line.price_subtotal,
                        "receipt_doc_number": receipt or False,
                        "purchase_line_id": line.id,
                        "include_in_payment": True,
                    },
                )
            )
        return lines

    @api.model
    def action_create_from_purchase(self, order):
        order.ensure_one()
        form = self.env["gfmis.form.type"].search([("code", "=", "ขบ.01")], limit=1)
        if not form:
            form = self.env["gfmis.form.type"].search(
                [("doc_class", "=", "request"), ("requires_po", "=", True)],
                limit=1,
            )
        if not form:
            form = self.env["gfmis.form.type"].search([("doc_class", "=", "request")], limit=1)
        if not form:
            raise UserError(_("ไม่พบแบบฟอร์มขอเบิกเงิน"))
        return self.create(
            {
                "doc_class": "request",
                "form_type_id": form.id,
                "partner_id": order.partner_id.id,
                "purchase_id": order.id,
                "reference": order.name,
                "description": (order.name or "")[:99],
                "line_ids": self._prepare_lines_from_purchase(order),
                "payment_method": "direct",
                "fund_type": "budget",
            }
        )

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
        lines = self._prepare_lines_from_invoice(invoice)
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


    def action_export_gf_excel(self):
        if not self.line_ids:
            raise UserError(_("ยังไม่มีรายการสำหรับออกรายงาน GF"))
        return self.line_ids.action_export_gf_excel()


class GfmisDocumentLine(models.Model):
    _name = "gfmis.document.line"
    _description = "บรรทัดรายการขอเบิก GFMIS"
    _order = "transfer_date, dika_number, id"

    document_id = fields.Many2one(
        "gfmis.document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="document_id.company_id", store=True)
    currency_id = fields.Many2one(related="document_id.currency_id")
    name = fields.Char(string="รายการ", required=True)
    delivery_date = fields.Date(string="วันที่ส่งมอบ")
    receipt_doc_number = fields.Char(string="เลขที่เอกสารตรวจรับ")
    gpsc_code = fields.Char(string="รหัส GPSC")
    bill_number = fields.Char(string="เลขที่บิล")
    tax_amount = fields.Monetary(string="ภาษี", currency_field="currency_id")
    note = fields.Char(string="หมายเหตุ")
    transfer_date = fields.Date(
        related="document_id.transfer_date",
        store=True,
        index=True,
    )
    partner_id = fields.Many2one(
        related="document_id.partner_id",
        store=True,
        index=True,
    )
    form_code = fields.Char(related="document_id.form_code", store=True)
    dika_number = fields.Char(related="document_id.dika_number", store=True, index=True)
    quantity = fields.Float(string="จำนวน", default=1.0)
    price_unit = fields.Monetary(string="ราคาต่อหน่วย", currency_field="currency_id")
    amount = fields.Monetary(string="จำนวนเงิน", currency_field="currency_id")
    fund_source_code = fields.Char(string="รหัสแหล่งของเงิน")
    activity_code = fields.Char(string="รหัสกิจกรรมหลัก")
    budget_code = fields.Char(string="รหัสงบประมาณ")
    purchase_line_id = fields.Many2one("purchase.order.line", string="บรรทัด PO")
    invoice_line_id = fields.Many2one("account.move.line", string="บรรทัดใบแจ้งหนี้")
    include_in_payment = fields.Boolean(
        string="เบิก",
        default=True,
        help="เลือกบรรทัดที่จะรวมในใบเบิกเงินรอบนี้ หากส่งมอบยังไม่ครบให้ติ๊กเฉพาะรายการที่เบิกได้",
    )

    group_amount = fields.Monetary(
        string="เป็นเงิน",
        compute="_compute_group_amount",
        currency_field="currency_id",
    )
    penalty_amount = fields.Monetary(
        related="document_id.amount_penalty",
        string="ค่าปรับ",
    )

    @api.depends("document_id.line_ids.amount", "document_id.line_ids.include_in_payment")
    def _compute_group_amount(self):
        for line in self:
            document = line.document_id
            line.group_amount = document._vpk_selected_amount() if document else 0.0

    @api.onchange("quantity", "price_unit")
    def _onchange_amount(self):
        self.amount = (self.quantity or 0.0) * (self.price_unit or 0.0)
        if self.document_id:
            self.document_id._vpk_apply_default_wht_onchange()

    @api.onchange("include_in_payment", "amount")
    def _onchange_include_in_payment(self):
        if self.document_id:
            self.document_id._vpk_apply_default_wht_onchange()

    def write(self, vals):
        res = super().write(vals)
        if {"include_in_payment", "amount", "quantity", "price_unit"} & set(vals):
            self.mapped("document_id")._vpk_sync_default_wht()
        return res

    def unlink(self):
        documents = self.mapped("document_id")
        res = super().unlink()
        documents._vpk_sync_default_wht()
        return res

    def action_export_gf_excel(self):
        if self:
            lines = self.search([("document_id", "in", self.document_id.ids)])
        else:
            lines = self.search([])
        if not lines:
            raise UserError(_("ยังไม่มีรายการสำหรับออกรายงาน GF"))
        content = lines._gf_register_xlsx()
        attachment = self.env["ir.attachment"].create({
            "name": "รายงาน-GF.xlsx",
            "datas": base64.b64encode(content),
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "res_model": "gfmis.document.line",
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def _gf_register_xlsx(self):
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter

        months = [
            "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
            "ก.ค.", "ส.ค.", "กย.", "ต.ค.", "พ.ย.", "ธ.ค.",
        ]

        def thai_short(value):
            if not value:
                return ""
            return "%s %s%s" % (value.day, months[value.month], str(value.year + 543)[-2:])

        lines = self.sorted(
            key=lambda line: (
                line.transfer_date or fields.Date.from_string("1900-01-01"),
                line.dika_number or "",
                line.document_id.id,
                line.id,
            )
        )
        groups = []
        bucket = []
        current = None
        for line in lines:
            if current != line.document_id:
                if bucket:
                    groups.append(bucket)
                bucket = [line]
                current = line.document_id
            else:
                bucket.append(line)
        if bucket:
            groups.append(bucket)

        headers = [
            "ลำดับที่", "วันที่ โอน", "ชื่อบริษัท", "ขบ.", "ฎีกาที่",
            "เลขที่บิล", "จำนวนเงิน", "ภาษี", "เป็นเงิน", "ค่าปรับ", "หมายเหตุ",
        ]
        book = Workbook()
        sheet = book.active
        sheet.title = "รายงาน GF"
        thin = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )
        header_fill = PatternFill("solid", fgColor="D6E3F0")
        header_font = Font(name="Arial", bold=True, size=11, color="1F4E79")
        title_font = Font(name="Arial", bold=True, size=16, color="1F4E79")
        body_font = Font(name="Arial", size=11)
        money = '#,##0.00'
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left = Alignment(horizontal="left", vertical="center")
        right = Alignment(horizontal="right", vertical="center")

        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        title = sheet.cell(1, 1, "รายงาน GF")
        title.font = title_font
        title.alignment = Alignment(horizontal="center", vertical="center")
        sheet.row_dimensions[1].height = 28
        for col, label in enumerate(headers, start=1):
            cell = sheet.cell(2, col, label)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = thin
        sheet.row_dimensions[2].height = 32
        sheet.auto_filter.ref = "A2:K2"
        sheet.freeze_panes = "A3"
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.fitToPage = True
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.page_setup.paperSize = 9
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.horizontalCentered = True
        sheet.oddHeader.center.text = "รายงาน GF"
        sheet.print_title_rows = "1:2"
        sheet.page_setup.horizontalDpi = 300
        sheet.page_setup.verticalDpi = 300
        sheet.sheet_view.showGridLines = False
        sheet.sheet_view.zoomScale = 110
        sheet.sheet_view.view = "normal"
        sheet.oddFooter.left.text = "กระบวนการ GFMIS"
        sheet.oddFooter.right.text = "หน้า &P / &N"

        row = 3
        for index, group in enumerate(groups, start=1):
            start = row
            document = group[0].document_id
            line_tax = sum(line.tax_amount or 0.0 for line in group)
            tax_value = line_tax or document.amount_wht or 0.0
            penalty_value = document.amount_penalty or 0.0
            for offset, line in enumerate(group):
                first = offset == 0
                last = offset == len(group) - 1
                remark = line.note or ""
                values = [
                    index if first else "..",
                    thai_short(line.transfer_date) if first else "..",
                    (line.partner_id.name or "") if first else "..",
                    (line.form_code or "") if first else "..",
                    (line.dika_number or "") if first else "..",
                    line.bill_number or "",
                    line.amount or 0.0,
                    tax_value if last and tax_value else None,
                    None,
                    penalty_value if last and penalty_value else None,
                    remark,
                ]
                for col, value in enumerate(values, start=1):
                    cell = sheet.cell(row, col, value)
                    cell.font = body_font
                    cell.border = thin
                    cell.alignment = center if col in (1, 2, 4, 5) else left
                    if col in (7, 8, 9, 10) and isinstance(value, (int, float)):
                        cell.number_format = money
                        cell.alignment = right
                end = row
                row += 1
            total_cell = sheet.cell(end, 9, "=SUM(G%s:G%s)" % (start, end))
            total_cell.font = Font(name="Arial", size=11, bold=True)
            total_cell.number_format = money
            total_cell.alignment = right
            total_cell.border = thin

        if groups:
            total_row = row
            label = sheet.cell(total_row, 6, "รวม")
            label.font = Font(name="Arial", size=11, bold=True)
            label.alignment = right
            for col, letter in ((7, "G"), (8, "H"), (9, "I"), (10, "J")):
                cell = sheet.cell(total_row, col, "=SUM(%s3:%s%s)" % (letter, letter, total_row - 1))
                cell.font = Font(name="Arial", size=11, bold=True)
                cell.number_format = money
                cell.alignment = right
                cell.border = Border(top=Side(style="thin", color="1F4E79"), bottom=Side(style="double", color="1F4E79"))
            label.border = Border(top=Side(style="thin", color="1F4E79"), bottom=Side(style="double", color="1F4E79"))
            sheet.auto_filter.ref = "A2:K%s" % (total_row - 1)

        widths = [12, 14, 28, 12, 16, 28, 16, 14, 16, 14, 24]
        for col, width in enumerate(widths, start=1):
            sheet.column_dimensions[get_column_letter(col)].width = width
        sheet.row_dimensions[2].height = 32
        sheet.page_margins.left = 0.5
        sheet.page_margins.right = 0.5
        sheet.page_margins.top = 0.6
        sheet.page_margins.bottom = 0.6
        buffer = io.BytesIO()
        book.save(buffer)
        return buffer.getvalue()


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
