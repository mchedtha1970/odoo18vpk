# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import re
from pathlib import Path

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PAYMENT_VOUCHER_DOC_TYPE_CODES = ("payment_voucher", "ใบสำคัญจ่าย")

THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")


def _load_memo_inline_css():
    """Reuse Garuda memo fonts/layout from vpk_tier_validation when available."""
    try:
        tv_static = (
            Path(__file__).resolve().parents[2]
            / "vpk_tier_validation"
            / "static"
            / "src"
        )
        fonts = (tv_static / "scss" / "thai_fonts_embedded.scss").read_text(
            encoding="utf-8"
        )
        layout = (tv_static / "css" / "official_memo_report_layout.css").read_text(
            encoding="utf-8"
        )
        voucher_css = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "src"
            / "css"
            / "payment_voucher_report.css"
        ).read_text(encoding="utf-8")
        return f"{fonts}\n{layout}\n{voucher_css}"
    except OSError:
        return ""


class VpkPaymentVoucher(models.Model):
    _name = "vpk.payment.voucher"
    _description = "ใบสำคัญจ่าย (กลุ่มงานการเงิน)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="เลขที่ใบสำคัญจ่าย",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("to_approve", "รออนุมัติ"),
            ("approved", "อนุมัติแล้ว"),
            ("cancel", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=True,
    )
    date = fields.Date(
        string="วันที่",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    memo_agency = fields.Char(
        string="ส่วนราชการ",
        default="กลุ่มงานการเงิน โรงพยาบาลวชิระภูเก็ต",
    )
    memo_phone = fields.Char(
        string="โทรศัพท์",
        default=lambda self: getattr(self.env.company, "vpk_memo_phone", None)
        or "๐ ๗๖๓๖ ๑๒๓๔ ต่อ ๖๕๑๒ - ๖๕๑๕",
    )
    memo_ref_prefix = fields.Char(
        string="คำนำหน้าเลขที่หนังสือ",
        default="ภก ๐๐๓๓.๒๐๑.๕/",
    )
    memo_ref = fields.Char(string="เลขที่หนังสือ (ต่อท้าย)")
    memo_subject = fields.Char(
        string="เรื่อง",
        required=True,
        default=lambda self: self._default_memo_subject(),
    )
    memo_to = fields.Char(
        string="เรียน",
        default=lambda self: self._default_memo_to(),
    )
    intro_text = fields.Text(
        string="ข้อความนำ",
        default=lambda self: self._default_intro_text(),
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="แหล่งเงิน / ชื่อกองทุน",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        check_company=True,
        tracking=True,
        help="เลือกสมุดบัญชีธนาคาร (Bank Journal) ที่เป็นแหล่งเงิน",
    )
    fund_name = fields.Char(
        string="ชื่อแหล่งเงิน",
        related="journal_id.name",
        store=True,
        readonly=True,
    )
    available_bank_account_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        compute="_compute_available_bank_account_ids",
        string="บัญชีที่เลือกได้",
    )
    bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="บัญชีธนาคารที่ตัดจ่าย",
        domain="[('id', 'in', available_bank_account_ids)]",
        check_company=False,
    )
    company_partner_id = fields.Many2one(
        related="company_id.partner_id",
    )
    bank_display = fields.Char(
        string="ข้อความบัญชีธนาคาร",
        compute="_compute_bank_display",
        store=True,
        readonly=False,
    )
    purpose_text = fields.Text(
        string="ข้อความสรุปวัตถุประสงค์",
        default=lambda self: self._default_purpose_text(),
    )
    line_ids = fields.One2many(
        comodel_name="vpk.payment.voucher.line",
        inverse_name="voucher_id",
        string="รายการ",
        copy=True,
    )
    bill_ids = fields.Many2many(
        comodel_name="account.move",
        relation="vpk_payment_voucher_bill_rel",
        column1="voucher_id",
        column2="move_id",
        string="ใบเรียกเก็บอ้างอิง",
        domain="[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]",
    )
    amount_total = fields.Monetary(
        string="รวมเป็นเงิน",
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )
    amount_total_text = fields.Char(
        string="จำนวนเงิน (ตัวอักษร)",
        compute="_compute_amount_total_text",
    )
    attachment_count = fields.Integer(
        string="จำนวนฉบับแนบ",
        compute="_compute_attachment_count",
    )
    proposer_name = fields.Char(
        string="ผู้เสนอ (ชื่อ)",
    )
    proposer_position = fields.Char(
        string="ผู้เสนอ (ตำแหน่ง)",
    )
    approver_name = fields.Char(
        string="ผู้อนุมัติ (ชื่อ)",
    )
    approver_position = fields.Char(
        string="ผู้อนุมัติ (ตำแหน่ง)",
    )
    approval_text = fields.Char(
        string="ข้อความอนุมัติ",
    )
    note = fields.Text(string="หมายเหตุ")
    studio_document_ids = fields.One2many(
        comodel_name="vpk.document.studio.document",
        inverse_name="payment_voucher_id",
        string="เอกสารใบสำคัญจ่าย",
    )
    studio_document_count = fields.Integer(
        string="จำนวนเอกสารใบสำคัญจ่าย",
        compute="_compute_studio_document_count",
    )
    disbursement_type = fields.Selection(
        selection=[
            ("gfmis", "ผ่าน GFMIS"),
            ("non_gfmis", "จ่ายจากโรงพยาบาลเอง (ไม่ผ่าน GFMIS)"),
        ],
        string="วิธีการเบิกจ่าย",
        compute="_compute_disbursement_type",
    )
    cheque_leaf_ids = fields.One2many(
        comodel_name="vpk.bank.cheque.leaf",
        inverse_name="payment_voucher_id",
        string="เช็คสั่งจ่าย",
    )
    cheque_leaf_count = fields.Integer(
        string="จำนวนเช็ค",
        compute="_compute_cheque_leaf_info",
    )
    cheque_numbers = fields.Char(
        string="เลขที่เช็ค",
        compute="_compute_cheque_leaf_info",
    )

    @api.depends("bill_ids")
    def _compute_disbursement_type(self):
        for voucher in self:
            dtype = "non_gfmis"
            for bill in voucher.bill_ids:
                po = self.env["purchase.order"]
                if "payment_request_id" in bill._fields and bill.payment_request_id:
                    po = bill.payment_request_id.purchase_id
                if not po and bill.invoice_line_ids:
                    po = bill.invoice_line_ids.purchase_line_id.order_id[:1]
                if po and "egp_disbursement_type" in po._fields and po.egp_disbursement_type:
                    dtype = po.egp_disbursement_type
                    break
            voucher.disbursement_type = dtype

    @api.depends("cheque_leaf_ids", "cheque_leaf_ids.state", "cheque_leaf_ids.cheque_number")
    def _compute_cheque_leaf_info(self):
        for voucher in self:
            active_leaves = voucher.cheque_leaf_ids.filtered(
                lambda l: l.state != "cancelled"
            )
            voucher.cheque_leaf_count = len(active_leaves)
            voucher.cheque_numbers = ", ".join(
                str(l.cheque_number) for l in active_leaves
            )

    @api.depends("studio_document_ids")
    def _compute_studio_document_count(self):
        Document = self.env["vpk.document.studio.document"].sudo()
        counts = {
            row["payment_voucher_id"][0]: row["payment_voucher_id_count"]
            for row in Document.read_group(
                [("payment_voucher_id", "in", self.ids)],
                ["payment_voucher_id"],
                ["payment_voucher_id"],
            )
            if row.get("payment_voucher_id")
        }
        for voucher in self:
            voucher.studio_document_count = counts.get(voucher.id, 0)

    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for voucher in self:
            voucher.amount_total = sum(voucher.line_ids.mapped("amount"))

    @api.depends("amount_total", "currency_id")
    def _compute_amount_total_text(self):
        for voucher in self:
            voucher.amount_total_text = voucher._baht_text(voucher.amount_total)

    @api.depends("line_ids")
    def _compute_attachment_count(self):
        for voucher in self:
            voucher.attachment_count = len(voucher.line_ids)

    def _banks_linked_to_journal(self, journal):
        """บัญชีธนาคารที่ผูกกับ Bank Journal ที่เลือก."""
        self.ensure_one()
        if not journal:
            return self.env["res.partner.bank"]
        company = self.company_id or journal.company_id
        PartnerBank = self.env["res.partner.bank"]
        banks = journal.bank_account_id
        banks |= PartnerBank.search(
            [
                ("journal_id", "=", journal.id),
                ("partner_id", "=", company.partner_id.id),
            ]
        )
        return banks.filtered(lambda bank: bool(bank))

    @api.depends("journal_id", "journal_id.bank_account_id", "company_id")
    def _compute_available_bank_account_ids(self):
        for voucher in self:
            voucher.available_bank_account_ids = voucher._banks_linked_to_journal(
                voucher.journal_id
            )

    @api.depends(
        "bank_account_id",
        "bank_account_id.acc_number",
        "bank_account_id.bank_id",
    )
    def _compute_bank_display(self):
        for voucher in self:
            bank = voucher.bank_account_id
            if not bank:
                voucher.bank_display = False
                continue
            bank_name = bank.bank_id.name or "ธนาคาร"
            acc = bank.acc_number or ""
            voucher.bank_display = (
                f"{bank_name} สาขาภูเก็ต เลขบัญชี {acc}".strip()
                if acc
                else bank.display_name
            )

    @api.model
    def _default_memo_subject(self):
        return "ขออนุมัติเบิกจ่ายเงิน"

    @api.model
    def _default_memo_to(self):
        return "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต"

    @api.model
    def _default_intro_text(self):
        return "ขอส่งใบสำคัญค่าใช้จ่ายประจำวัน เพื่อเบิกเงิน"

    @api.model
    def _default_purpose_text(self):
        # Placeholders are filled by Document Studio when printing.
        return (
            "สำหรับใช้ในกิจการปฏิบัติการของโรงพยาบาลวชิระภูเก็ต โดยใช้เงิน "
            "{{journal_id}} {{bank_display}} "
            "พร้อมบันทึกได้แนบใบสำคัญเพื่อเบิกเงินจำนวน {{attachment_count}} ฉบับ"
        )

    def _purpose_placeholder_mapping(self):
        self.ensure_one()
        return {
            "journal_id": self.fund_name or self.journal_id.display_name or "",
            "bank_display": self.bank_display or "",
            "attachment_count": str(self.attachment_count or 0),
        }

    def _filled_purpose_text(self):
        """Resolve {{journal_id}} / {{bank_display}} / {{attachment_count}} for display/print."""
        self.ensure_one()
        text = self.purpose_text or ""
        if "{{" not in text:
            return text
        mapping = self._purpose_placeholder_mapping()

        def replacer(match):
            code = match.group(1)
            if code in mapping:
                return mapping[code]
            return match.group(0)

        return re.sub(
            r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}",
            replacer,
            text,
        )

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        banks = self._banks_linked_to_journal(self.journal_id)
        self.available_bank_account_ids = banks
        preferred = self.journal_id.bank_account_id if self.journal_id else False
        if preferred and preferred in banks:
            self.bank_account_id = preferred
        elif self.bank_account_id not in banks:
            self.bank_account_id = banks[:1] if banks else False

    @api.onchange("bank_account_id")
    def _onchange_bank_account_id(self):
        bank = self.bank_account_id
        if not bank:
            return
        journal = bank.journal_id
        if not journal:
            journal = self.env["account.journal"].search(
                [
                    ("type", "=", "bank"),
                    ("bank_account_id", "=", bank.id),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
        if journal and journal != self.journal_id:
            self.journal_id = journal

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.payment.voucher")
                    or _("New")
                )
            if not vals.get("memo_ref"):
                vals["memo_ref"] = vals.get("name")
        return super().create(vals_list)

    def _thai_digits(self, value):
        if value is None:
            return ""
        return str(value).translate(THAI_DIGITS)

    def _format_amount(self, amount):
        value = self.currency_id.round(amount or 0.0)
        return self._thai_digits(f"{value:,.2f}")

    def _baht_text(self, amount):
        currency = self.currency_id or self.env.company.currency_id
        try:
            text = currency.with_context(lang="th_TH").amount_to_text(amount or 0.0)
        except Exception:
            text = currency.amount_to_text(amount or 0.0)
        if text and "บาท" not in text:
            text = "%sบาทถ้วน" % text
        return text or ""

    def _format_date_thai(self):
        self.ensure_one()
        if not self.date:
            return ""
        if "thai.utils" in self.env:
            return self.env["thai.utils"].format_thai_date(self.date)
        # fallback Buddhist year
        months = [
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
        ]
        return f"{self.date.day} {months[self.date.month]} {self.date.year + 543}"

    def _get_agency_display(self):
        self.ensure_one()
        agency = self.memo_agency or ""
        phone = (self.memo_phone or "").strip()
        if not phone or phone in agency:
            return agency
        if phone.startswith("โทร"):
            return f"{agency}  {phone}".strip()
        return f"{agency}  โทรศัพท์ {phone}".strip()

    def _get_ref_display(self):
        self.ensure_one()
        prefix = self.memo_ref_prefix or ""
        ref = self.memo_ref or self.name or ""
        return f"{prefix}{self._thai_digits(ref)}"

    @api.model
    def _get_official_memo_inline_css(self):
        return Markup(_load_memo_inline_css())

    def action_submit(self):
        for voucher in self:
            if not voucher.line_ids:
                raise UserError(_("กรุณาเพิ่มรายการในใบสำคัญจ่ายก่อนส่งอนุมัติ"))
            voucher.state = "to_approve"
        return True

    def action_approve(self):
        self.write({"state": "approved"})
        return True

    def action_draft(self):
        self.write({"state": "draft"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def _vpk_payment_voucher_template(self):
        """หาแบบฟอร์ม Document Studio ของใบสำคัญจ่ายเท่านั้น (ไม่ใช้แบบอนุมัติขอซื้อ)."""
        self.ensure_one()
        Template = self.env["vpk.document.studio.template"].sudo()
        # Prefer explicit code installed for this module
        template = Template.search(
            [
                ("active", "=", True),
                ("company_id", "in", [False, self.company_id.id]),
                ("code", "=", "vpk_payment_voucher"),
                ("source_model_id.model", "=", "vpk.payment.voucher"),
            ],
            order="company_id desc, id desc",
            limit=1,
        )
        if template:
            return template
        return Template.search(
            [
                ("active", "=", True),
                ("company_id", "in", [False, self.company_id.id]),
                ("source_model_id.model", "=", "vpk.payment.voucher"),
                ("document_type_id.code", "in", list(PAYMENT_VOUCHER_DOC_TYPE_CODES)),
                (
                    "document_type_id.code",
                    "not in",
                    ("purchase_approval_memo", "payment_request"),
                ),
            ],
            order="company_id desc, id desc",
            limit=1,
        )

    def _vpk_payment_voucher_document_type(self):
        template = self._vpk_payment_voucher_template()
        if template and template.document_type_id:
            return template.document_type_id
        Type = self.env["vpk.document.studio.document.type"].sudo()
        doc_type = Type.search(
            [("code", "in", list(PAYMENT_VOUCHER_DOC_TYPE_CODES))],
            order="id asc",
            limit=1,
        )
        if doc_type:
            return doc_type
        return Type.create(
            {
                "name": "ใบสำคัญจ่าย",
                "code": "payment_voucher",
                "sequence": 240,
                "company_id": False,
            }
        )

    def _vpk_find_studio_memo_document(self):
        self.ensure_one()
        template = self._vpk_payment_voucher_template()
        domain = [
            ("payment_voucher_id", "=", self.id),
            ("state", "not in", ("cancelled",)),
        ]
        if template:
            domain.append(("template_id", "=", template.id))
        return self.env["vpk.document.studio.document"].sudo().search(
            domain,
            order="id desc",
            limit=1,
        )

    def _vpk_reload_studio_document_from_voucher(self, document):
        """ดึงค่าจากใบสำคัญจ่ายเข้าเอกสาร Studio ก่อนพิมพ์."""
        self.ensure_one()
        document.ensure_one()
        if not document.template_id:
            return document
        values = document._values_from_record(document.template_id, self)
        document.write(
            {
                "value_json": values,
                "source_ref": "%s,%d" % (self._name, self.id),
                "payment_voucher_id": self.id,
                "body": document._filled_body_html(convert_word=True),
            }
        )
        return document

    def _ensure_studio_memo_document(self):
        """สร้าง/อัปเดตเอกสารจากแบบฟอร์ม Document Studio ใบสำคัญจ่าย."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("กรุณาเพิ่มรายการในใบสำคัญจ่ายก่อนพิมพ์"))

        Document = self.env["vpk.document.studio.document"].sudo()
        template = self._vpk_payment_voucher_template()
        if not template:
            raise UserError(
                _(
                    "ยังไม่มีแบบฟอร์ม Document Studio สำหรับใบสำคัญจ่าย "
                    "กรุณาสร้างแบบฟอร์มที่ต้นทางเป็น vpk.payment.voucher "
                    "และประเภทเอกสารใบสำคัญจ่ายก่อนพิมพ์"
                )
            )

        doc_type = template.document_type_id or self._vpk_payment_voucher_document_type()
        document = self._vpk_find_studio_memo_document()
        if not document:
            document = Document.create(
                {
                    "source_mode": "studio",
                    "template_id": template.id,
                    "document_type_id": doc_type.id,
                    "source_ref": "%s,%d" % (self._name, self.id),
                    "payment_voucher_id": self.id,
                    "company_id": self.company_id.id,
                    "note": self.memo_subject or self.name or "",
                }
            )
            self.message_post(
                body=_("สร้างเอกสารใบสำคัญจ่าย %s จากแบบฟอร์ม %s")
                % (document.display_name, template.display_name),
                subtype_xmlid="mail.mt_note",
            )
        elif document.template_id != template:
            document.write(
                {
                    "source_mode": "studio",
                    "template_id": template.id,
                    "document_type_id": doc_type.id,
                }
            )

        self._vpk_reload_studio_document_from_voucher(document)
        return document

    def action_print_voucher(self):
        """พิมพ์จากแบบฟอร์ม Document Studio ใบสำคัญจ่าย และเก็บไฟล์ในแท็บเอกสาร."""
        self.ensure_one()
        document = self._ensure_studio_memo_document()
        return document.action_generate_pdf()

    def action_view_studio_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสารใบสำคัญจ่าย"),
            "res_model": "vpk.document.studio.document",
            "view_mode": "list,form",
            "domain": [("payment_voucher_id", "=", self.id)],
            "context": {
                "default_payment_voucher_id": self.id,
                "default_source_ref": "%s,%d" % (self._name, self.id),
                "default_source_mode": "uploaded",
                "search_default_my_documents": 0,
            },
            "views": [
                (
                    self.env.ref(
                        "vpk_payment_voucher.view_document_studio_document_list_payment_voucher"
                    ).id,
                    "list",
                ),
                (False, "form"),
            ],
        }

    def action_add_bills(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เลือกใบเรียกเก็บ"),
            "res_model": "vpk.payment.voucher.create.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_voucher_id": self.id,
                "default_bill_ids": self.bill_ids.ids,
            },
        }

    def _vpk_net_cheque_amount(self):
        """คำนวณยอดเงินสุทธิสำหรับสั่งจ่ายเช็ค (ยอดรวมใบสำคัญจ่าย หักภาษี ณ ที่จ่าย ถ้ามี)."""
        self.ensure_one()
        gross = self.amount_total or 0.0
        wht_amt = 0.0
        if "wht_cert_4235_ids" in self._fields:
            certs = self.wht_cert_4235_ids.filtered(lambda c: c.state != "cancel")
            if certs:
                wht_amt = sum(certs.mapped("wht_tax_amount"))
        if not wht_amt and self.bill_ids:
            wht_lines = self.bill_ids.invoice_line_ids.filtered(
                lambda l: bool(getattr(l, "wht_tax_id", False))
            )
            if wht_lines:
                rate = getattr(wht_lines[0].wht_tax_id, "amount", 1.0) or 1.0
                raw_total = sum(wht_lines.mapped("price_subtotal"))
                base_amt = (
                    round(raw_total / 1.07, 2)
                    if not any(wht_lines.mapped("tax_ids"))
                    else round(raw_total, 2)
                )
                wht_amt = round(base_amt * rate / 100.0, 2)
        net = round(gross - wht_amt, 2)
        return net if net > 0 else gross

    def action_open_print_cheque_wizard(self):
        """เปิดหน้าต่างพิมพ์เช็คจากใบสำคัญจ่าย (กรณีจ่ายตรงจากโรงพยาบาล ไม่ผ่าน GFMIS)."""
        self.ensure_one()
        if self.disbursement_type == "gfmis":
            raise UserError(
                _(
                    "การพิมพ์เช็คใช้สำหรับกรณีจ่ายตรงจากโรงพยาบาล (ไม่ผ่าน GFMIS) เท่านั้น"
                )
            )
        Book = self.env["vpk.bank.cheque.book"].sudo()
        Leaf = self.env["vpk.bank.cheque.leaf"].sudo()
        Wizard = self.env["vpk.bank.cheque.print.wizard"]

        # หากมีเช็คที่พิมพ์ให้ใบสำคัญจ่ายนี้แล้ว ให้เปิดใบเดิมขึ้นมาพิมพ์ซ้ำ/ตรวจสอบได้
        existing_leaf = self.cheque_leaf_ids.filtered(
            lambda l: l.state == "printed"
        )[:1]
        if existing_leaf:
            return existing_leaf.action_print()

        acc_num = (
            self.bank_account_id.acc_number.strip()
            if self.bank_account_id and self.bank_account_id.acc_number
            else ""
        )
        book = False
        if acc_num:
            book = Book.search([("account_number", "=", acc_num)], limit=1)
        if not book:
            book = Book.search([], limit=1)
        if not book:
            raise UserError(_("ยังไม่มีสมุดเช็คในระบบ กรุณาสร้างสมุดเช็คก่อนพิมพ์"))

        leaf = Leaf.search(
            [
                ("book_id", "=", book.id),
                ("state", "=", "blank"),
            ],
            order="cheque_number asc",
            limit=1,
        )
        if not leaf:
            raise UserError(
                _("สมุดเช็ค %s ไม่มีใบเช็คว่างเหลืออยู่") % book.display_name
            )

        bill = self.bill_ids[:1]
        partner = (
            (bill.partner_id if bill else False)
            or (self.line_ids[:1].partner_id if self.line_ids else False)
        )
        pay_name = (
            (partner.name if partner else "")
            or (self.line_ids[:1].partner_name if self.line_ids else "")
        )
        net_amount = self._vpk_net_cheque_amount()

        wizard = Wizard.create(
            {
                "cheque_book_id": book.id,
                "cheque_leaf_id": leaf.id,
                "partner_id": partner.id if partner else False,
                "pay_name_line1": pay_name,
                "amount": net_amount,
                "currency_id": (self.currency_id or self.env.company.currency_id).id,
                "date": self.date or fields.Date.context_today(self),
                "is_ac_pay": True,
                "move_id": bill.id if bill else False,
                "payment_voucher_id": self.id,
            }
        )
        wizard._fill_amount_words()
        return {
            "type": "ir.actions.act_window",
            "name": _("พิมพ์เช็ค (จ่ายจากโรงพยาบาล)"),
            "res_model": "vpk.bank.cheque.print.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_cheque_leaves(self):
        self.ensure_one()
        leaves = self.cheque_leaf_ids.filtered(lambda l: l.state != "cancelled")
        if not leaves:
            return self.action_open_print_cheque_wizard()
        if len(leaves) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("ใบเช็ค"),
                "res_model": "vpk.bank.cheque.leaf",
                "res_id": leaves.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("เช็คสั่งจ่าย"),
            "res_model": "vpk.bank.cheque.leaf",
            "view_mode": "list,form",
            "domain": [("payment_voucher_id", "=", self.id)],
        }

    @api.model
    def create_from_bills(self, bills, extra_vals=None):
        """สร้างใบสำคัญจ่ายจากใบเรียกเก็บที่ POST แล้ว."""
        bills = bills.filtered(
            lambda move: move.move_type == "in_invoice" and move.state == "posted"
        )
        if not bills:
            raise UserError(_("เลือกใบเรียกเก็บที่ POST แล้วอย่างน้อย 1 รายการ"))
        vals = {
            "bill_ids": [(6, 0, bills.ids)],
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "sequence": index * 10,
                        "partner_id": bill.partner_id.id,
                        "partner_name": bill.partner_id.name,
                        "bill_ref": bill.name if bill.name != "/" else bill.ref or "",
                        "amount": bill.amount_residual or bill.amount_total,
                        "move_id": bill.id,
                    },
                )
                for index, bill in enumerate(bills, start=1)
            ],
            "memo_subject": _("ขออนุมัติเบิกจ่ายเงิน"),
        }
        if extra_vals:
            vals.update(extra_vals)
        return self.create(vals)


class VpkPaymentVoucherLine(models.Model):
    _name = "vpk.payment.voucher.line"
    _description = "รายการใบสำคัญจ่าย"
    _order = "sequence, id"

    voucher_id = fields.Many2one(
        comodel_name="vpk.payment.voucher",
        string="ใบสำคัญจ่าย",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="ลำดับ", default=10)
    partner_id = fields.Many2one(comodel_name="res.partner", string="บริษัท")
    partner_name = fields.Char(string="ชื่อบริษัท", required=True)
    bill_ref = fields.Char(string="บิลเลขที่", required=True)
    amount = fields.Monetary(
        string="จำนวนเงิน",
        required=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(related="voucher_id.currency_id")
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="ใบเรียกเก็บ",
        domain="[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]",
    )
    note = fields.Char(string="หมายเหตุ")

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name

    @api.onchange("move_id")
    def _onchange_move_id(self):
        if not self.move_id:
            return
        bill = self.move_id
        self.partner_id = bill.partner_id
        self.partner_name = bill.partner_id.name
        self.bill_ref = bill.name if bill.name != "/" else (bill.ref or "")
        self.amount = bill.amount_residual or bill.amount_total


class VpkBankChequeLeaf(models.Model):
    _inherit = "vpk.bank.cheque.leaf"

    payment_voucher_id = fields.Many2one(
        comodel_name="vpk.payment.voucher",
        string="ใบสำคัญจ่าย",
        ondelete="set null",
        index=True,
    )


class VpkBankChequePrintWizard(models.TransientModel):
    _inherit = "vpk.bank.cheque.print.wizard"

    payment_voucher_id = fields.Many2one(
        comodel_name="vpk.payment.voucher",
        string="ใบสำคัญจ่าย",
    )

    def _mark_printed(self):
        super()._mark_printed()
        for wizard in self:
            if wizard.payment_voucher_id and wizard.cheque_leaf_id:
                wizard.cheque_leaf_id.sudo().write(
                    {"payment_voucher_id": wizard.payment_voucher_id.id}
                )
                # ซิงค์เลขที่เช็คเข้าใบรับรองหักภาษี ณ ที่จ่าย (ถ้ามี)
                voucher = wizard.payment_voucher_id
                if "wht_cert_4235_ids" in voucher._fields and voucher.wht_cert_4235_ids:
                    voucher.wht_cert_4235_ids.filtered(
                        lambda c: c.state != "cancel"
                    ).sudo().write(
                        {"wht_cheque_no": str(wizard.cheque_leaf_id.cheque_number)}
                    )

