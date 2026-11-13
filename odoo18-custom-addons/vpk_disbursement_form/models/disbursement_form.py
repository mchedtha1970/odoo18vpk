# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import base64
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round

from ..tools.xls_template import XlsTemplate

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
_DIGITS = ("ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า")
_POSITIONS = ("", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน")
_EXCEL_EPOCH = date(1899, 12, 30)

BUDGET_TYPES = [
    ("1", "ขอเบิกเงินในงบประมาณ"),
    ("2", "ขอเบิกเงินนอกงบประมาณที่ฝากคลัง"),
    ("3", "ขอเบิกเงินนอกงบประมาณที่ฝากที่ธนาคารพาณิชย์"),
    ("4", "ขอเบิกเงินทดรองโครงการเงินกู้"),
    ("5", "ขอเบิกเงินจากกรมบัญชีกลางโดยใช้แหล่งเงินกู้"),
]
# ตารางเดียวกับสูตรในชีต Interface ของ template (DOC_TYPE / PYMT_METH)
DOC_TYPE_BY_BUDGET = {"2": "KG", "3": "KJ", "4": "KT", "5": "KR"}
PAYMENT_CODE_BY_BUDGET = {"1": "1", "2": "3", "3": "5", "4": "6", "5": "3"}

FORM_TYPES = [
    ("kb01", "ขบ.01 ใบขอเบิกเงินงบประมาณที่ต้องอ้างใบสั่งซื้อฯ"),
    ("kb11", "ขบ.11 ใบขอเบิกเงินนอกงบประมาณที่ต้องอ้างใบสั่งซื้อฯ"),
]

def thai_baht_text(amount):
    """จำนวนเงินเป็นตัวอักษรไทย เช่น 267476.64 -> สองแสนหกหมื่นเจ็ดพัน...บาทหกสิบสี่สตางค์"""
    amount = round(float(amount or 0.0) + 1e-9, 2)
    baht = int(amount)
    satang = int(round((amount - baht) * 100))

    def read_group(number, higher):
        digits = str(number)
        size = len(digits)
        out = []
        for index, ch in enumerate(digits):
            digit = int(ch)
            pos = size - index - 1
            if digit == 0:
                continue
            if pos == 1:
                out.append("สิบ" if digit == 1 else "ยี่สิบ" if digit == 2 else _DIGITS[digit] + "สิบ")
            elif pos == 0:
                if digit == 1 and (size > 1 or higher):
                    out.append("เอ็ด")
                else:
                    out.append(_DIGITS[digit])
            else:
                out.append(_DIGITS[digit] + _POSITIONS[pos])
        return "".join(out)

    def read_number(number):
        if number == 0:
            return ""
        parts = []
        while number:
            parts.append(number % 1000000)
            number //= 1000000
        text = ""
        for idx in range(len(parts) - 1, -1, -1):
            group = parts[idx]
            if group:
                text += read_group(group, any(parts[idx + 1:]))
            if idx:
                text += "ล้าน"
        return text

    result = (read_number(baht) or _DIGITS[0]) + "บาท"
    if satang:
        result += read_number(satang) + "สตางค์"
    else:
        result += "ถ้วน"
    return result


def thai_date_text(value):
    if not value:
        return ""
    return "%s %s %s" % (value.day, THAI_MONTHS[value.month], value.year + 543)


def excel_serial_be(value):
    """ค่าวันที่ในเซลล์ template: ปี พ.ศ. ใส่เป็นปีของปฏิทินสากล (เช่น 2569 -> 244604)"""
    be_year = value.year + 543
    try:
        target = date(be_year, value.month, value.day)
    except ValueError:  # 29 ก.พ. ที่ไม่มีในปี พ.ศ. นั้น
        target = date(be_year, 3, 1)
    return float((target - _EXCEL_EPOCH).days)


def yyyymmdd_be(value):
    return "%04d%02d%02d" % (value.year + 543, value.month, value.day)


class DisbursementForm(models.Model):
    _name = "vpk.disbursement.form"
    _description = "ใบขอเบิกเงิน"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "document_date desc, id desc"

    name = fields.Char(
        string="เลขที่เอกสาร", required=True, copy=False, default="/", tracking=True
    )
    form_type = fields.Selection(
        FORM_TYPES, string="แบบฟอร์ม", required=True, default="kb01", tracking=True
    )
    state = fields.Selection(
        [
            ("draft", "ร่าง"),
            ("confirmed", "ยืนยันข้อมูลแล้ว"),
            ("uploaded", "อัปโหลดกรมบัญชีกลางแล้ว"),
            ("cancel", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id")

    # --- หน่วยงาน -------------------------------------------------------
    agency_code = fields.Char(string="รหัสหน่วยงาน")
    agency_name = fields.Char(string="ชื่อหน่วยงาน")
    province_code = fields.Char(string="รหัสจังหวัด")
    province_name = fields.Char(string="ชื่อจังหวัด")
    unit_code = fields.Char(string="รหัสหน่วยเบิกจ่าย")
    unit_name = fields.Char(string="ชื่อหน่วยเบิกจ่าย")

    # --- ประเภทรายการขอเบิก / รายละเอียด -------------------------------------
    budget_type = fields.Selection(
        BUDGET_TYPES,
        string="ประเภทรายการขอเบิก",
        required=True,
        default="2",
        tracking=True,
    )
    gfmis_po_number = fields.Char(
        string="เลขที่ใบสั่งซื้อฯ จากระบบ GFMIS",
        help="เลขที่ใบสั่งซื้อ/สั่งจ้าง ที่ออกจากระบบ GFMIS เช่น 4102887681",
        tracking=True,
    )
    earmark = fields.Boolean(string="กันเงินไว้เบิก")
    reservation_number = fields.Char(string="เลขที่เอกสารสำรองเงิน")
    payment_method = fields.Selection(
        [("direct", "จ่ายตรงเข้าบัญชีเงินฝากธนาคารของผู้ขาย/คู่สัญญา")],
        string="วิธีการจ่ายชำระเงิน",
        default="direct",
        required=True,
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
    )
    reference = fields.Char(
        string="การอ้างอิง",
        help="เลขที่อ้างอิง เช่น เลขที่ใบขอซื้อ/ใบสั่งซื้อ P690008971",
        tracking=True,
    )

    # --- เอกสารต้นทาง (ใบเรียกเก็บที่ส่งการเงินแล้ว) -----------------------
    invoice_id = fields.Many2one(
        "account.move",
        string="ใบเรียกเก็บ",
        domain="[('move_type', 'in', ('in_invoice', 'in_refund')), ('state', '=', 'posted')]",
        index=True,
        copy=False,
        tracking=True,
        ondelete="restrict",
    )
    purchase_id = fields.Many2one(
        "purchase.order",
        string="ใบสั่งซื้อ",
        copy=False,
        index=True,
        ondelete="set null",
    )
    payment_request_id = fields.Many2one(
        "vpk.document.studio.document",
        string="ใบขออนุมัติเบิกจ่าย",
        copy=False,
        index=True,
        ondelete="set null",
        readonly=True,
    )

    # --- ผู้ขาย / จำนวนเงิน -----------------------------------------------
    partner_id = fields.Many2one("res.partner", string="ผู้ขาย/คู่สัญญา", tracking=True)
    description = fields.Text(
        string="คำอธิบายรายการ",
        help="เช่น ค่ายา บริษัท ... จำกัด เป็นเงิน 270,500 บาท",
    )
    amount_request = fields.Monetary(
        string="จำนวนเงินขอเบิก", currency_field="currency_id", tracking=True
    )
    vat_rate = fields.Float(
        string="ภาษีมูลค่าเพิ่ม (%)",
        default=7.0,
        help="ใช้คำนวณฐานภาษีหัก ณ ที่จ่าย = จำนวนเงินขอเบิก / (1 + VAT) ถ้าไม่มี VAT ให้ใส่ 0",
    )
    tax_type = fields.Selection(
        [
            ("none", "ไม่มีภาษีเงินได้หัก ณ ที่จ่าย"),
            ("person", "บุคคลธรรมดา"),
            ("corp", "นิติบุคคล"),
        ],
        string="ภาษีเงินได้ (ผู้รับเงิน)",
        default="corp",
        required=True,
    )
    wht_rate = fields.Float(string="อัตราภาษีหัก ณ ที่จ่าย (%)", default=1.0)
    wht_base = fields.Monetary(
        string="ฐานการคำนวณภาษี",
        currency_field="currency_id",
        compute="_compute_wht_base",
        store=True,
        readonly=False,
    )
    wht_amount = fields.Monetary(
        string="ภาษีที่หักไว้",
        currency_field="currency_id",
        compute="_compute_wht_amount",
        store=True,
        readonly=False,
    )
    penalty_type = fields.Selection(
        [
            ("none", "ไม่มีค่าปรับ"),
            ("state", "ค่าปรับเป็นรายได้ของแผ่นดิน"),
            ("agency", "ค่าปรับเป็นรายได้ของหน่วยงาน"),
        ],
        string="ค่าปรับ",
        default="none",
        required=True,
    )
    penalty_base = fields.Monetary(string="ฐานการคำนวณค่าปรับ", currency_field="currency_id")
    penalty_amount = fields.Monetary(string="ค่าปรับที่หักไว้", currency_field="currency_id")
    amount_net = fields.Monetary(
        string="จำนวนเงินขอรับ",
        currency_field="currency_id",
        compute="_compute_amount_net",
        store=True,
    )
    amount_text = fields.Char(string="จำนวนเงิน (ตัวอักษร)", compute="_compute_amount_net")

    # --- ผู้ตรวจสอบ / ผู้อนุมัติ -------------------------------------------
    checker_name = fields.Char(string="ชื่อผู้ตรวจสอบ")
    checker_position = fields.Char(string="ตำแหน่ง (ผู้ตรวจสอบ)")
    checker_date = fields.Date(string="วันที่ (ผู้ตรวจสอบ)")
    approver_name = fields.Char(string="ชื่อผู้อนุมัติ")
    approver_position = fields.Char(string="ตำแหน่ง (ผู้อนุมัติ)")
    approver_date = fields.Date(string="วันที่ (ผู้อนุมัติ)")

    # --- เลขที่จากระบบ GFMIS / การอัปโหลด ----------------------------------
    gfmis_doc_number = fields.Char(
        string="เลขที่เอกสารจากระบบ GFMIS",
        help="กรอกหลังอัปโหลดเข้าระบบกรมบัญชีกลาง",
        tracking=True,
    )
    uploaded_on = fields.Datetime(string="อัปโหลดเมื่อ", readonly=True, copy=False)
    uploaded_by = fields.Many2one("res.users", string="อัปโหลดโดย", readonly=True, copy=False)

    # --- ไฟล์ -----------------------------------------------------------
    file_ids = fields.One2many("vpk.disbursement.form.file", "form_id", string="ไฟล์แนบ")
    file_count = fields.Integer(compute="_compute_file_count")
    last_generated_on = fields.Datetime(string="สร้างไฟล์ล่าสุดเมื่อ", readonly=True, copy=False)
    note = fields.Text(string="หมายเหตุ")

    # ------------------------------------------------------------------
    # compute / onchange / constraints
    # ------------------------------------------------------------------
    @api.depends("file_ids")
    def _compute_file_count(self):
        for rec in self:
            rec.file_count = len(rec.file_ids)

    @api.depends("amount_request", "vat_rate", "tax_type")
    def _compute_wht_base(self):
        for rec in self:
            if rec.tax_type == "none":
                rec.wht_base = 0.0
                continue
            divisor = 1.0 + (rec.vat_rate or 0.0) / 100.0
            rec.wht_base = float_round((rec.amount_request or 0.0) / divisor, precision_digits=2)

    @api.depends("wht_base", "wht_rate", "tax_type")
    def _compute_wht_amount(self):
        for rec in self:
            if rec.tax_type == "none":
                rec.wht_amount = 0.0
                continue
            rec.wht_amount = float_round(
                (rec.wht_base or 0.0) * (rec.wht_rate or 0.0) / 100.0, precision_digits=2
            )

    @api.depends("amount_request", "wht_amount", "penalty_amount", "tax_type", "penalty_type")
    def _compute_amount_net(self):
        for rec in self:
            wht = rec.wht_amount if rec.tax_type != "none" else 0.0
            penalty = rec.penalty_amount if rec.penalty_type != "none" else 0.0
            net = (rec.amount_request or 0.0) - (wht or 0.0) - (penalty or 0.0)
            rec.amount_net = float_round(net, precision_digits=2)
            rec.amount_text = thai_baht_text(net) if rec.amount_request else ""

    @api.constrains("amount_request", "wht_amount", "penalty_amount")
    def _check_amounts(self):
        for rec in self:
            if rec.amount_request < 0 or rec.wht_amount < 0 or rec.penalty_amount < 0:
                raise ValidationError(_("จำนวนเงินต้องไม่ติดลบ"))
            if rec.amount_net < 0:
                raise ValidationError(_("ภาษีและค่าปรับที่หักไว้ต้องไม่เกินจำนวนเงินขอเบิก"))

    @api.onchange("company_id")
    def _onchange_company_id(self):
        self._apply_company_defaults()

    @api.onchange("partner_id", "amount_request")
    def _onchange_partner_description(self):
        if self.partner_id and not self.description and self.amount_request:
            self.description = _("จ่ายให้ %(partner)s เป็นเงิน %(amount)s บาท") % {
                "partner": self.partner_id.name,
                "amount": "{:,.2f}".format(self.amount_request),
            }

    def _apply_company_defaults(self):
        for rec in self:
            company = rec.company_id
            rec.agency_code = company.vpk_dr_agency_code
            rec.agency_name = company.vpk_dr_agency_name
            rec.province_code = company.vpk_dr_province_code
            rec.province_name = company.vpk_dr_province_name
            rec.unit_code = company.vpk_dr_unit_code
            rec.unit_name = company.vpk_dr_unit_name

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company
        for fname, cname in (
            ("agency_code", "vpk_dr_agency_code"),
            ("agency_name", "vpk_dr_agency_name"),
            ("province_code", "vpk_dr_province_code"),
            ("province_name", "vpk_dr_province_name"),
            ("unit_code", "vpk_dr_unit_code"),
            ("unit_name", "vpk_dr_unit_name"),
        ):
            if fname in fields_list and fname not in res:
                res[fname] = company[cname]
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("vpk.disbursement.form") or "/"
        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(default or {}, name="/", file_ids=[])
        return super().copy_data(default)

    def unlink(self):
        if any(rec.state not in ("draft", "cancel") for rec in self):
            raise UserError(_("ลบได้เฉพาะใบขอเบิกเงินที่เป็นร่างหรือยกเลิกแล้ว"))
        return super().unlink()

    # ------------------------------------------------------------------
    # สร้างจากใบเรียกเก็บที่ส่งการเงินแล้ว
    # ------------------------------------------------------------------
    @api.model
    def action_create_from_invoice(self, invoice):
        """สร้างหรือเปิดใบขอเบิกเงินจากใบเรียกเก็บที่ส่งหน่วยงานการเงินแล้ว."""
        invoice.ensure_one()
        if invoice.move_type not in ("in_invoice", "in_refund"):
            raise UserError(_("สร้างใบขอเบิกเงินได้เฉพาะใบเรียกเก็บ / ใบลดหนี้ผู้ขาย"))
        if invoice.state != "posted":
            raise UserError(_("ต้องลงรายการใบเรียกเก็บแล้วก่อนสร้างใบขอเบิกเงิน"))
        payment_request = invoice.payment_request_id
        if not payment_request or not payment_request.payment_finance_sent_on:
            raise UserError(
                _("สร้างใบขอเบิกเงินได้เมื่อเจ้าหนี้ส่งรายการนี้ให้การเงินแล้วเท่านั้น")
            )
        existing = self.search(
            [("invoice_id", "=", invoice.id), ("state", "!=", "cancel")],
            limit=1,
        )
        if existing:
            return existing

        purchase = invoice.invoice_line_ids.purchase_line_id.order_id[:1]
        amount = abs(invoice.amount_total)
        partner = invoice.partner_id
        reference = (
            payment_request.name
            or invoice.ref
            or invoice.name
            or (purchase.name if purchase else "")
        )
        description = invoice.payment_reference or invoice.ref or invoice.name or ""
        if partner:
            description = description or _(
                "จ่ายให้ %(partner)s เป็นเงิน %(amount)s บาท"
            ) % {
                "partner": partner.display_name,
                "amount": "{:,.2f}".format(amount),
            }
        # หน่วยงานราชการ: ไม่ตั้งภาษีซื้อ → ค่าเริ่ม VAT = 0 บนแบบฟอร์มขอเบิก
        vals = {
            "invoice_id": invoice.id,
            "purchase_id": purchase.id if purchase else False,
            "payment_request_id": payment_request.id,
            "partner_id": partner.id,
            "reference": reference,
            "description": (description or "")[:500],
            "amount_request": amount,
            "vat_rate": 0.0,
            "document_date": invoice.invoice_date or fields.Date.context_today(self),
            "posting_date": invoice.date or fields.Date.context_today(self),
            "company_id": invoice.company_id.id,
            "form_type": "kb01",
            "budget_type": "2",
        }
        if purchase:
            vals["gfmis_po_number"] = purchase.name
        form = self.create(vals)
        form.message_post(
            body=_(
                "สร้างจากใบเรียกเก็บ %(bill)s (ส่งการเงินแล้ว จากใบขออนุมัติเบิกจ่าย %(doc)s)",
                bill=invoice.display_name,
                doc=payment_request.display_name,
            ),
            subtype_xmlid="mail.mt_note",
        )
        return form

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("ยังไม่ผูกใบเรียกเก็บ"))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # ตรวจข้อมูลก่อนยืนยัน / สร้างไฟล์
    # ------------------------------------------------------------------
    def _check_ready(self):
        """ตรวจข้อมูลที่ template ต้องใช้ แล้วแจ้งทุกข้อที่ขาด"""
        self.ensure_one()
        missing = []
        required = [
            ("agency_code", _("รหัสหน่วยงาน")),
            ("province_code", _("รหัสจังหวัด")),
            ("unit_code", _("รหัสหน่วยเบิกจ่าย")),
            ("gfmis_po_number", _("เลขที่ใบสั่งซื้อฯ จากระบบ GFMIS")),
            ("reference", _("การอ้างอิง")),
            ("description", _("คำอธิบายรายการ")),
        ]
        for fname, label in required:
            if not self[fname]:
                missing.append(label)
        if not self.amount_request or self.amount_request <= 0:
            missing.append(_("จำนวนเงินขอเบิก"))
        if self.tax_type != "none" and not self.wht_base:
            missing.append(_("ฐานการคำนวณภาษี"))
        if self.penalty_type != "none" and not self.penalty_amount:
            missing.append(_("ค่าปรับที่หักไว้"))
        if missing:
            raise UserError(
                _("กรุณากรอกข้อมูลให้ครบก่อนดำเนินการ:\n- %s") % "\n- ".join(missing)
            )

    # ------------------------------------------------------------------
    # ปุ่มสถานะ
    # ------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            rec._check_ready()
            rec.state = "confirmed"
        return True

    def action_draft(self):
        for rec in self:
            if rec.state == "uploaded":
                raise UserError(_("เอกสารที่อัปโหลดแล้วต้องยกเลิกก่อนจึงจะแก้ไขได้"))
            rec.state = "draft"
        return True

    def action_mark_uploaded(self):
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(_("ต้องยืนยันข้อมูลก่อนบันทึกว่าอัปโหลดแล้ว"))
            if not rec.file_ids.filtered(lambda f: f.kind == "generated"):
                raise UserError(_("ยังไม่มีไฟล์ที่สร้างจาก template กรุณากด \"บันทึกข้อมูลเข้า template Excel\" ก่อน"))
            rec.write(
                {
                    "state": "uploaded",
                    "uploaded_on": fields.Datetime.now(),
                    "uploaded_by": self.env.user.id,
                }
            )
            rec.message_post(
                body=_("บันทึกว่าอัปโหลดเข้าระบบกรมบัญชีกลางแล้ว (เลขที่เอกสาร GFMIS: %s)")
                % (rec.gfmis_doc_number or "-")
            )
        return True

    def action_cancel(self):
        for rec in self:
            rec.state = "cancel"
        return True

    # ------------------------------------------------------------------
    # สร้างไฟล์จาก template
    # ------------------------------------------------------------------
    def action_generate_excel(self):
        """ปุ่ม บันทึกข้อมูลเข้า template Excel: สร้างไฟล์ .xls และแนบเก็บไว้ในเอกสาร"""
        self.ensure_one()
        if self.state == "cancel":
            raise UserError(_("เอกสารที่ยกเลิกแล้วสร้างไฟล์ไม่ได้"))
        self._check_ready()
        content = self._build_excel()
        version = (
            max(self.file_ids.filtered(lambda f: f.kind == "generated").mapped("version") or [0])
            + 1
        )
        safe_ref = "".join(ch for ch in (self.reference or self.name) if ch.isalnum() or ch in "-_") or "form"
        filename = "%s_%s_v%s.xls" % (self.form_type.upper(), safe_ref, version)
        self.env["vpk.disbursement.form.file"].create(
            {
                "form_id": self.id,
                "kind": "generated",
                "version": version,
                "name": _("ไฟล์ %(form)s สร้างจาก template (ครั้งที่ %(v)s)")
                % {"form": dict(FORM_TYPES)[self.form_type].split(" ")[0], "v": version},
                "file": base64.b64encode(content),
                "filename": filename,
                "sequence": 5,
            }
        )
        self.last_generated_on = fields.Datetime.now()
        self.message_post(
            body=_("บันทึกข้อมูลเข้า template Excel แล้ว: %(file)s (ยอดขอรับ %(net)s บาท)")
            % {"file": filename, "net": "{:,.2f}".format(self.amount_net)}
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("สร้างไฟล์ Excel แล้ว"),
                "message": _("แนบไว้ในแท็บ \"ไฟล์แนบ\": %s") % filename,
                "type": "success",
                "sticky": False,
            },
        }

    def action_download_latest(self):
        self.ensure_one()
        latest = self.file_ids.filtered(lambda f: f.kind == "generated").sorted("version", reverse=True)[:1]
        if not latest:
            raise UserError(_("ยังไม่มีไฟล์ที่สร้างจาก template"))
        return latest.action_download()

    def _build_excel(self):
        self.ensure_one()
        builder = getattr(self, "_build_excel_%s" % self.form_type, None)
        if not builder:
            raise UserError(_("ยังไม่รองรับแบบฟอร์ม %s") % self.form_type)
        raw = self.company_id._vpk_get_disbursement_template_bytes(self.form_type)
        template = XlsTemplate(raw)
        builder(template)
        return template.to_bytes()

    # ------------------------------------------------------------------
    # แมปข้อมูลลง template ขบ.01 / ขบ.11 (ชีต Input + Interface)
    # ------------------------------------------------------------------
    def _build_excel_kb11(self, tpl):
        """ขบ.11 ใช้โครงสร้าง template เดียวกับขบ.01."""
        return self._build_excel_kb01(tpl)

    def _build_excel_kb01(self, tpl):
        self.ensure_one()
        inp, itf = "Input", "Interface"
        has_tax = self.tax_type != "none"
        has_penalty = self.penalty_type != "none" and bool(self.penalty_amount)
        budget = self.budget_type
        tax_radio = 1 if self.tax_type == "person" else 2
        penalty_radio = 1 if self.penalty_type == "state" else 2
        wht = self.wht_amount if has_tax else 0.0
        wht_base = self.wht_base if has_tax else 0.0

        # --- ชีต Input: ส่วนหัวหน่วยงาน
        tpl.set(inp, "B4", self.agency_code)
        tpl.set(inp, "E4", self.agency_name)
        tpl.set(inp, "B5", self.province_code)
        tpl.set(inp, "E5", self.province_name)
        tpl.set(inp, "B6", self.unit_code)
        tpl.set(inp, "E6", self.unit_name)

        # --- ประเภทรายการขอเบิก (ตัวเลือกที่เลือก = ●) ; M8/M9/M13 = เซลล์เชื่อมโยงของปุ่มเลือก
        for index, (key, label) in enumerate(BUDGET_TYPES):
            tpl.set(inp, "B%s" % (8 + index), ("● " if key == budget else "○ ") + label)
        tpl.set(inp, "M8", float(budget))
        tpl.set(inp, "I8", self.gfmis_po_number)
        tpl.set(inp, "H9", ("☑ " if self.earmark else "☐ ") + "กันเงินไว้เบิก")
        tpl.set(inp, "M9", bool(self.earmark))
        tpl.set(inp, "I10", self.reservation_number)
        tpl.set(inp, "H13", "● " + dict(self._fields["payment_method"].selection)[self.payment_method])
        tpl.set(inp, "M13", 1.0)

        # --- วันที่ / อ้างอิง / คำอธิบาย / จำนวนเงิน
        tpl.set(inp, "B13", excel_serial_be(self.document_date))
        tpl.set(inp, "F13", excel_serial_be(self.posting_date))
        tpl.set(inp, "B14", self.reference)
        tpl.set(inp, "A17", self.description)
        tpl.set(inp, "K15", self.amount_request)

        # --- ภาษีเงินได้หัก ณ ที่จ่าย
        tpl.set(inp, "H17", ("● " if has_tax and tax_radio == 1 else "○ ") + "บุคคลธรรมดา")
        tpl.set(inp, "H18", ("● " if has_tax and tax_radio == 2 else "○ ") + "นิติบุคคล")
        tpl.set(inp, "M17", float(tax_radio))
        tpl.set(inp, "J17", wht_base if has_tax and tax_radio == 1 else None)
        tpl.set(inp, "K17", wht if has_tax and tax_radio == 1 else None)
        tpl.set(inp, "J18", wht_base if has_tax and tax_radio == 2 else None)
        tpl.set(inp, "K18", wht if has_tax and tax_radio == 2 else None)

        # --- ค่าปรับ
        tpl.set(inp, "H19", ("● " if has_penalty and penalty_radio == 1 else "○ ") + "รายได้ของแผ่นดิน")
        tpl.set(inp, "H20", ("● " if has_penalty and penalty_radio == 2 else "○ ") + "รายได้ของหน่วยงาน")
        tpl.set(inp, "L19", float(penalty_radio))
        tpl.set(inp, "M19", float(penalty_radio) if has_penalty else None)
        tpl.set(inp, "J19", self.penalty_base if has_penalty and penalty_radio == 1 else None)
        tpl.set(inp, "K19", self.penalty_amount if has_penalty and penalty_radio == 1 else None)
        tpl.set(inp, "J20", self.penalty_base if has_penalty and penalty_radio == 2 else None)
        tpl.set(inp, "K20", self.penalty_amount if has_penalty and penalty_radio == 2 else None)

        # --- ยอดสุทธิ / ตัวอักษร / ผู้ตรวจสอบ / ผู้อนุมัติ / เลขที่ GFMIS
        tpl.set(inp, "K21", self.amount_net)
        tpl.set(inp, "B22", thai_baht_text(self.amount_net))
        tpl.set(inp, "B25", self.checker_name)
        tpl.set(inp, "B26", self.checker_position)
        tpl.set(inp, "B27", thai_date_text(self.checker_date))
        tpl.set(inp, "H25", self.approver_name)
        tpl.set(inp, "H26", self.approver_position)
        tpl.set(inp, "H27", thai_date_text(self.approver_date))
        tpl.set(inp, "C28", self.gfmis_doc_number)

        # --- ชีต Interface (ค่าเดียวกับที่สูตรใน template คำนวณจากชีต Input)
        doc_type = (
            ("KB" if self.earmark else "KA") if budget == "1" else DOC_TYPE_BY_BUDGET.get(budget, "")
        )
        tpl.set(itf, "C2", self.agency_code)
        tpl.set(itf, "C5", self.agency_code)
        tpl.set(itf, "D5", self.gfmis_po_number)
        tpl.set(itf, "E5", doc_type)
        tpl.set(itf, "F5", yyyymmdd_be(self.document_date))
        tpl.set(itf, "G5", yyyymmdd_be(self.posting_date))
        tpl.set(itf, "H5", PAYMENT_CODE_BY_BUDGET.get(budget, ""))
        tpl.set(itf, "I5", self.reference)
        tpl.set(itf, "J5", self.amount_request)
        tpl.set(itf, "K5", ("11" if tax_radio == 1 else "10") if has_tax else None)
        tpl.set(itf, "L5", ("A2" if tax_radio == 1 else "A1") if has_tax else None)
        tpl.set(itf, "M5", wht_base if has_tax else None)
        tpl.set(itf, "N5", wht if has_tax else None)
        tpl.set(itf, "O5", ("01" if penalty_radio == 1 else "02") if has_penalty else None)
        tpl.set(itf, "P5", ("B1" if penalty_radio == 1 else "B2") if has_penalty else None)
        tpl.set(itf, "Q5", self.penalty_base if has_penalty else None)
        tpl.set(itf, "R5", self.penalty_amount if has_penalty else None)
        tpl.set(itf, "S5", self.unit_code)
