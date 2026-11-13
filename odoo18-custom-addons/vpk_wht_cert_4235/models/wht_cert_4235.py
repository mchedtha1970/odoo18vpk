# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

WHT_4235_DOC_TYPE_CODES = ("wht_4235", "ใบรับรองหักภาษี ณ. ที่จ่าย แบบ 4235")
WHT_4235_TEMPLATE_CODE = "wht_4235"
WHT_GENERAL_DOC_TYPE_CODES = ("wht_general", "ใบรับรองการหักภาษี ณ ที่จ่าย (ทั่วไป)")
WHT_GENERAL_TEMPLATE_CODE = "wht_general"

THAI_MONTHS_FULL = (
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
THAI_MONTHS_SHORT = (
    "",
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
)


class VpkWhtCert4235(models.Model):
    _name = "vpk.wht.cert.4235"
    _description = "ใบรับรองการหักภาษี ณ ที่จ่าย (แบบ 4235 / ทั่วไป)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="เลขที่เอกสาร",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    form_type = fields.Selection(
        selection=[
            ("4235", "แบบ 4235 (จ่ายผ่าน GFMIS ตรงให้ผู้ขาย)"),
            ("general", "แบบทั่วไป (จ่ายจากโรงพยาบาลเอง)"),
        ],
        string="แบบฟอร์มใบรับรอง",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("confirmed", "ยืนยันแล้ว"),
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
        string="วันที่ออกใบรับรอง",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    payment_voucher_id = fields.Many2one(
        comodel_name="vpk.payment.voucher",
        string="ใบสำคัญจ่าย",
        index=True,
        ondelete="set null",
        tracking=True,
    )
    bill_ids = fields.Many2many(
        comodel_name="account.move",
        relation="vpk_wht_cert_4235_bill_rel",
        column1="cert_id",
        column2="move_id",
        string="ใบเรียกเก็บอ้างอิง",
        domain="[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]",
    )

    # ------------------------------------------------------------------
    # ข้อมูลใบรับรองหักภาษี ณ ที่จ่าย (แบบ 4235 และแบบทั่วไป)
    # ------------------------------------------------------------------
    wht_cert_no = fields.Char(
        string="เลขที่รับรองหักภาษี ณ ที่จ่าย",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
        tracking=True,
    )
    wht_cheque_no = fields.Char(
        string="เช็คเลขที่ (สำหรับแบบทั่วไป)",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_disbursement_no = fields.Char(
        string="ตามเอกสารขอเบิกเงินเลขที่ (สำหรับแบบ 4235)",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_doc_date = fields.Date(
        string="ลงวันที่ (เอกสารเบิกเงิน / เช็ค)",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_doc_day = fields.Char(
        string="ลงวันที่ (วัน)",
        compute="_compute_wht_date_parts",
    )
    wht_doc_month = fields.Char(
        string="ลงวันที่ (เดือน)",
        compute="_compute_wht_date_parts",
    )
    wht_doc_year = fields.Char(
        string="ลงวันที่ (พ.ศ.)",
        compute="_compute_wht_date_parts",
    )
    wht_contract_no = fields.Char(
        string="ตามสัญญา/ใบสั่งซื้อเลขที่",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_contract_date = fields.Date(
        string="ลงวันที่ (สัญญา/ใบสั่งซื้อ)",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_contract_day = fields.Char(
        string="วัน (สัญญา)",
        compute="_compute_wht_date_parts",
    )
    wht_contract_month = fields.Char(
        string="เดือน (สัญญา)",
        compute="_compute_wht_date_parts",
    )
    wht_contract_year = fields.Char(
        string="พ.ศ. (สัญญา)",
        compute="_compute_wht_date_parts",
    )
    wht_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้ถูกหักภาษี ณ ที่จ่าย",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
        tracking=True,
    )
    wht_taxpayer_type = fields.Selection(
        selection=[
            ("corp", "นิติบุคคล"),
            ("person", "บุคคลธรรมดา"),
        ],
        string="ประเภทผู้ถูกหักภาษี",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_vendor_name = fields.Char(
        string="ชื่อผู้ถูกหักภาษี ณ ที่จ่าย",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_vendor_vat = fields.Char(
        string="เลขผู้เสียภาษี / เลขบัตรประชาชน (13 หลัก)",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_vendor_address = fields.Char(
        string="ที่อยู่ผู้ถูกหักภาษี ณ ที่จ่าย",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_transferee_name = fields.Char(
        string="โอนสิทธิเรียกร้องให้แก่",
    )
    wht_transferee_address = fields.Char(
        string="ที่อยู่ผู้รับโอนสิทธิ",
    )
    wht_income_type = fields.Char(
        string="ประเภทเงินได้ที่จ่าย",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_pay_date = fields.Date(
        string="วันเดือนปีที่จ่าย",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_rate = fields.Float(
        string="อัตราภาษีหัก ณ ที่จ่าย (%)",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_base_amount = fields.Monetary(
        string="จำนวนเงินได้ (ฐานภาษี)",
        currency_field="currency_id",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
        tracking=True,
    )
    wht_tax_amount = fields.Monetary(
        string="ภาษีที่หักไว้",
        currency_field="currency_id",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
        tracking=True,
    )
    wht_fine_income_type = fields.Char(
        string="ประเภทเงินได้ (ค่าปรับ)",
    )
    wht_fine_base_amount = fields.Monetary(
        string="จำนวนเงินได้ (ค่าปรับ)",
        currency_field="currency_id",
    )
    wht_fine_tax_amount = fields.Monetary(
        string="ค่าปรับที่หักไว้",
        currency_field="currency_id",
    )
    wht_signer_name = fields.Char(
        string="ผู้ลงนามใบรับรองหักภาษี",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    wht_signer_position = fields.Char(
        string="ตำแหน่งผู้ลงนามใบรับรองหักภาษี",
        compute="_compute_wht_defaults",
        store=True,
        readonly=False,
    )
    note = fields.Text(string="หมายเหตุ")

    # 13 หลัก เลขบัตรประชาชน (บุคคลธรรมดา — แบบ 4235)
    wht_cid_1 = fields.Char(string="เลขประชาชน หลัก 1", compute="_compute_wht_tax_id_digits")
    wht_cid_2 = fields.Char(string="เลขประชาชน หลัก 2", compute="_compute_wht_tax_id_digits")
    wht_cid_3 = fields.Char(string="เลขประชาชน หลัก 3", compute="_compute_wht_tax_id_digits")
    wht_cid_4 = fields.Char(string="เลขประชาชน หลัก 4", compute="_compute_wht_tax_id_digits")
    wht_cid_5 = fields.Char(string="เลขประชาชน หลัก 5", compute="_compute_wht_tax_id_digits")
    wht_cid_6 = fields.Char(string="เลขประชาชน หลัก 6", compute="_compute_wht_tax_id_digits")
    wht_cid_7 = fields.Char(string="เลขประชาชน หลัก 7", compute="_compute_wht_tax_id_digits")
    wht_cid_8 = fields.Char(string="เลขประชาชน หลัก 8", compute="_compute_wht_tax_id_digits")
    wht_cid_9 = fields.Char(string="เลขประชาชน หลัก 9", compute="_compute_wht_tax_id_digits")
    wht_cid_10 = fields.Char(string="เลขประชาชน หลัก 10", compute="_compute_wht_tax_id_digits")
    wht_cid_11 = fields.Char(string="เลขประชาชน หลัก 11", compute="_compute_wht_tax_id_digits")
    wht_cid_12 = fields.Char(string="เลขประชาชน หลัก 12", compute="_compute_wht_tax_id_digits")
    wht_cid_13 = fields.Char(string="เลขประชาชน หลัก 13", compute="_compute_wht_tax_id_digits")

    # 13 หลัก เลขประจำตัวผู้เสียภาษีอากร (นิติบุคคล — แบบ 4235)
    wht_tin_1 = fields.Char(string="เลขผู้เสียภาษี หลัก 1", compute="_compute_wht_tax_id_digits")
    wht_tin_2 = fields.Char(string="เลขผู้เสียภาษี หลัก 2", compute="_compute_wht_tax_id_digits")
    wht_tin_3 = fields.Char(string="เลขผู้เสียภาษี หลัก 3", compute="_compute_wht_tax_id_digits")
    wht_tin_4 = fields.Char(string="เลขผู้เสียภาษี หลัก 4", compute="_compute_wht_tax_id_digits")
    wht_tin_5 = fields.Char(string="เลขผู้เสียภาษี หลัก 5", compute="_compute_wht_tax_id_digits")
    wht_tin_6 = fields.Char(string="เลขผู้เสียภาษี หลัก 6", compute="_compute_wht_tax_id_digits")
    wht_tin_7 = fields.Char(string="เลขผู้เสียภาษี หลัก 7", compute="_compute_wht_tax_id_digits")
    wht_tin_8 = fields.Char(string="เลขผู้เสียภาษี หลัก 8", compute="_compute_wht_tax_id_digits")
    wht_tin_9 = fields.Char(string="เลขผู้เสียภาษี หลัก 9", compute="_compute_wht_tax_id_digits")
    wht_tin_10 = fields.Char(string="เลขผู้เสียภาษี หลัก 10", compute="_compute_wht_tax_id_digits")
    wht_tin_11 = fields.Char(string="เลขผู้เสียภาษี หลัก 11", compute="_compute_wht_tax_id_digits")
    wht_tin_12 = fields.Char(string="เลขผู้เสียภาษี หลัก 12", compute="_compute_wht_tax_id_digits")
    wht_tin_13 = fields.Char(string="เลขผู้เสียภาษี หลัก 13", compute="_compute_wht_tax_id_digits")

    # 13 หลัก เลขผู้เสียภาษีรวม (แบบทั่วไป)
    wht_vat_1 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 1", compute="_compute_wht_tax_id_digits")
    wht_vat_2 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 2", compute="_compute_wht_tax_id_digits")
    wht_vat_3 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 3", compute="_compute_wht_tax_id_digits")
    wht_vat_4 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 4", compute="_compute_wht_tax_id_digits")
    wht_vat_5 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 5", compute="_compute_wht_tax_id_digits")
    wht_vat_6 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 6", compute="_compute_wht_tax_id_digits")
    wht_vat_7 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 7", compute="_compute_wht_tax_id_digits")
    wht_vat_8 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 8", compute="_compute_wht_tax_id_digits")
    wht_vat_9 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 9", compute="_compute_wht_tax_id_digits")
    wht_vat_10 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 10", compute="_compute_wht_tax_id_digits")
    wht_vat_11 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 11", compute="_compute_wht_tax_id_digits")
    wht_vat_12 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 12", compute="_compute_wht_tax_id_digits")
    wht_vat_13 = fields.Char(string="เลขผู้เสียภาษี (ทั่วไป) หลัก 13", compute="_compute_wht_tax_id_digits")

    # ช่องตารางแบบ 4235 (แยกบาท / สตางค์) และแบบทั่วไป (ทศนิยม 2 ตำแหน่ง)
    wht_corp_income_type = fields.Char(string="ประเภทเงินได้ (นิติบุคคล)", compute="_compute_wht_table_cells")
    wht_corp_pay_date = fields.Char(string="วันเดือนปีที่จ่าย (นิติบุคคล)", compute="_compute_wht_table_cells")
    wht_corp_base_baht = fields.Char(string="เงินได้นิติบุคคล (บาท)", compute="_compute_wht_table_cells")
    wht_corp_base_satang = fields.Char(string="เงินได้นิติบุคคล (สต.)", compute="_compute_wht_table_cells")
    wht_corp_tax_baht = fields.Char(string="ภาษีนิติบุคคล (บาท)", compute="_compute_wht_table_cells")
    wht_corp_tax_satang = fields.Char(string="ภาษีนิติบุคคล (สต.)", compute="_compute_wht_table_cells")
    wht_corp_base_formatted = fields.Char(string="เงินได้นิติบุคคล (รวมทศนิยม)", compute="_compute_wht_table_cells")
    wht_corp_tax_formatted = fields.Char(string="ภาษีนิติบุคคล (รวมทศนิยม)", compute="_compute_wht_table_cells")

    wht_indiv_income_type = fields.Char(string="ประเภทเงินได้ (บุคคลธรรมดา)", compute="_compute_wht_table_cells")
    wht_indiv_pay_date = fields.Char(string="วันเดือนปีที่จ่าย (บุคคลธรรมดา)", compute="_compute_wht_table_cells")
    wht_indiv_base_baht = fields.Char(string="เงินได้บุคคลธรรมดา (บาท)", compute="_compute_wht_table_cells")
    wht_indiv_base_satang = fields.Char(string="เงินได้บุคคลธรรมดา (สต.)", compute="_compute_wht_table_cells")
    wht_indiv_tax_baht = fields.Char(string="ภาษีบุคคลธรรมดา (บาท)", compute="_compute_wht_table_cells")
    wht_indiv_tax_satang = fields.Char(string="ภาษีบุคคลธรรมดา (สต.)", compute="_compute_wht_table_cells")
    wht_indiv_base_formatted = fields.Char(string="เงินได้บุคคลธรรมดา (รวมทศนิยม)", compute="_compute_wht_table_cells")
    wht_indiv_tax_formatted = fields.Char(string="ภาษีบุคคลธรรมดา (รวมทศนิยม)", compute="_compute_wht_table_cells")

    wht_fine_pay_date = fields.Char(string="วันเดือนปีที่จ่าย (ค่าปรับ)", compute="_compute_wht_table_cells")
    wht_fine_base_baht = fields.Char(string="เงินได้ค่าปรับ (บาท)", compute="_compute_wht_table_cells")
    wht_fine_base_satang = fields.Char(string="เงินได้ค่าปรับ (สต.)", compute="_compute_wht_table_cells")
    wht_fine_tax_baht = fields.Char(string="ค่าปรับ (บาท)", compute="_compute_wht_table_cells")
    wht_fine_tax_satang = fields.Char(string="ค่าปรับ (สต.)", compute="_compute_wht_table_cells")

    wht_total_base_baht = fields.Char(string="รวมจำนวนเงินได้ (บาท)", compute="_compute_wht_table_cells")
    wht_total_base_satang = fields.Char(string="รวมจำนวนเงินได้ (สต.)", compute="_compute_wht_table_cells")
    wht_total_tax_baht = fields.Char(string="รวมภาษี (บาท)", compute="_compute_wht_table_cells")
    wht_total_tax_satang = fields.Char(string="รวมภาษี (สต.)", compute="_compute_wht_table_cells")
    wht_total_base_formatted = fields.Char(string="รวมจำนวนเงินได้ (รวมทศนิยม)", compute="_compute_wht_table_cells")
    wht_total_tax_formatted = fields.Char(string="รวมภาษี (รวมทศนิยม)", compute="_compute_wht_table_cells")
    wht_total_tax_text = fields.Char(string="รวมเงินภาษี (ตัวอักษร)", compute="_compute_wht_table_cells")

    # เอกสารที่พิมพ์ของตัวเอง
    studio_document_ids = fields.One2many(
        comodel_name="vpk.document.studio.document",
        inverse_name="wht_cert_4235_id",
        string="เอกสารใบรับรองหักภาษี",
    )
    studio_document_count = fields.Integer(
        string="จำนวนเอกสารใบรับรอง",
        compute="_compute_studio_document_count",
    )

    @api.depends("studio_document_ids")
    def _compute_studio_document_count(self):
        Document = self.env["vpk.document.studio.document"].sudo()
        counts = {
            row["wht_cert_4235_id"][0]: row["wht_cert_4235_id_count"]
            for row in Document.read_group(
                [("wht_cert_4235_id", "in", self.ids)],
                ["wht_cert_4235_id"],
                ["wht_cert_4235_id"],
            )
            if row.get("wht_cert_4235_id")
        }
        for rec in self:
            rec.studio_document_count = counts.get(rec.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.wht.cert.4235")
                    or _("New")
                )
        records = super().create(vals_list)
        records._compute_wht_defaults()
        return records

    def _baht_text(self, amount):
        currency = self.currency_id or self.env.company.currency_id
        try:
            text = currency.with_context(lang="th_TH").amount_to_text(amount or 0.0)
        except Exception:
            text = currency.amount_to_text(amount or 0.0)
        if text and "บาท" not in text:
            text = "%sบาทถ้วน" % text
        return text or ""

    def _vpk_format_partner_address(self, partner):
        if not partner:
            return ""
        parts = [
            partner.street,
            partner.street2,
            partner.city,
            partner.state_id.name if partner.state_id else "",
            partner.zip,
        ]
        return " ".join(p.strip() for p in parts if p and p.strip())

    def _vpk_split_baht_satang(self, amount):
        val = round(float(amount or 0.0), 2)
        if val <= 0:
            return "", ""
        total_satang = int(round(val * 100))
        baht = total_satang // 100
        satang = total_satang % 100
        return f"{baht:,}", f"{satang:02d}"

    def _vpk_format_decimal(self, amount):
        val = round(float(amount or 0.0), 2)
        if val <= 0:
            return ""
        return f"{val:,.2f}"

    def _vpk_short_thai_date(self, d):
        if not d:
            return ""
        return f"{d.day} {THAI_MONTHS_SHORT[d.month]} {d.year + 543}"

    @api.model
    def _vpk_detect_form_type(self, voucher=False, bills=False):
        """ตรวจเงื่อนไขแบบฟอร์ม:
        - จ่ายผ่าน GFMIS ตรงให้ผู้ขาย -> '4235'
        - จ่ายจากโรงพยาบาลเอง (ไม่ผ่าน GFMIS) -> 'general'
        """
        bills = bills or (voucher.bill_ids if voucher else self.env["account.move"])
        bill = bills[:1] if bills else self.env["account.move"]

        po = self.env["purchase.order"]
        if bill and "payment_request_id" in bill._fields and bill.payment_request_id:
            po = bill.payment_request_id.purchase_id
        if not po and bill and bill.invoice_line_ids:
            po = bill.invoice_line_ids.purchase_line_id.order_id[:1]

        if po and "egp_disbursement_type" in po._fields:
            if po.egp_disbursement_type == "gfmis":
                return "4235"
            if po.egp_disbursement_type == "non_gfmis":
                return "general"

        if "vpk.disbursement.form" in self.env and bills:
            form = (
                self.env["vpk.disbursement.form"]
                .sudo()
                .search(
                    [
                        ("invoice_id", "in", bills.ids),
                        ("state", "!=", "cancel"),
                    ],
                    order="id desc",
                    limit=1,
                )
            )
            if form:
                return "4235"

        return "4235"

    @api.depends(
        "name",
        "date",
        "payment_voucher_id",
        "payment_voucher_id.name",
        "payment_voucher_id.date",
        "payment_voucher_id.bill_ids",
        "payment_voucher_id.line_ids.partner_id",
        "payment_voucher_id.line_ids.amount",
        "payment_voucher_id.amount_total",
        "payment_voucher_id.proposer_name",
        "payment_voucher_id.proposer_position",
        "bill_ids",
    )
    def _compute_wht_defaults(self):
        HasDisbursement = "vpk.disbursement.form" in self.env
        for rec in self:
            voucher = rec.payment_voucher_id
            bills = rec.bill_ids or (voucher.bill_ids if voucher else self.env["account.move"])
            if not rec.bill_ids and voucher and voucher.bill_ids:
                rec.bill_ids = voucher.bill_ids
            bill = bills[:1]
            partner = (
                rec.wht_partner_id
                or (bill.partner_id if bill else False)
                or (voucher.line_ids[:1].partner_id if (voucher and voucher.line_ids) else False)
            )

            detected_type = self._vpk_detect_form_type(voucher=voucher, bills=bills)
            rec.form_type = rec.form_type or detected_type

            form = False
            if HasDisbursement and bills:
                form = (
                    self.env["vpk.disbursement.form"]
                    .sudo()
                    .search(
                        [
                            ("invoice_id", "in", bills.ids),
                            ("state", "!=", "cancel"),
                        ],
                        order="id desc",
                        limit=1,
                    )
                )

            po = self.env["purchase.order"]
            if bill and "payment_request_id" in bill._fields and bill.payment_request_id:
                po = bill.payment_request_id.purchase_id
            if not po and form and form.purchase_id:
                po = form.purchase_id
            if not po and bill and bill.invoice_line_ids:
                po = bill.invoice_line_ids.purchase_line_id.order_id[:1]

            contract = (
                po.contract_id
                if (po and "contract_id" in po._fields and po.contract_id)
                else False
            )
            contract_no = ""
            contract_date = False
            if contract:
                contract_no = (
                    getattr(contract, "contract_number", False)
                    or contract.name
                    or ""
                )
                contract_date = (
                    getattr(contract, "sign_date", False)
                    or getattr(contract, "date_start", False)
                    or False
                )
            elif po:
                contract_no = po.name or ""
                if po.date_approve:
                    contract_date = po.date_approve.date()
                elif po.date_order:
                    contract_date = po.date_order.date()
            elif bill:
                contract_no = bill.invoice_origin or bill.ref or ""
                contract_date = bill.invoice_date

            disb_no = ""
            doc_date = (
                (voucher.date if voucher else False)
                or rec.date
                or fields.Date.context_today(rec)
            )
            if form:
                disb_no = (
                    form.gfmis_doc_number
                    or form.gfmis_po_number
                    or (form.name if form.name != "/" else "")
                    or ""
                )
                if form.document_date:
                    doc_date = form.document_date

            # เช็คเลขที่ (ดึงจากเช็คที่สั่งพิมพ์ในใบสำคัญจ่าย หรือจาก account.payment)
            cheque_no = rec.wht_cheque_no or ""
            if not cheque_no and voucher and "cheque_leaf_ids" in voucher._fields:
                printed_leaves = voucher.cheque_leaf_ids.filtered(
                    lambda l: l.state != "cancelled"
                )
                if printed_leaves:
                    cheque_no = str(printed_leaves[:1].cheque_number)
            if not cheque_no and bills:
                Payment = self.env["account.payment"].sudo()
                domain = [("payment_type", "=", "outbound")]
                if "vpk_source_bill_ids" in Payment._fields:
                    pay = Payment.search(
                        domain + [("vpk_source_bill_ids", "in", bills.ids)],
                        order="id desc",
                        limit=1,
                    )
                    if pay:
                        cheque_no = (
                            getattr(pay, "cheque_reference", False)
                            or getattr(pay, "bank_reference", False)
                            or ""
                        )

            taxpayer_type = "corp"
            if form and form.tax_type in ("corp", "person"):
                taxpayer_type = form.tax_type
            elif partner and not partner.is_company and partner.company_type == "person":
                taxpayer_type = "person"

            rate = rec.wht_rate or 1.0
            base_amt = 0.0
            tax_amt = 0.0
            if form and form.wht_amount:
                rate = form.wht_rate or 1.0
                base_amt = form.wht_base or 0.0
                tax_amt = form.wht_amount or 0.0
            elif bills:
                wht_lines = bills.invoice_line_ids.filtered(
                    lambda l: bool(getattr(l, "wht_tax_id", False))
                )
                if wht_lines:
                    wht_tax = wht_lines[0].wht_tax_id
                    rate = getattr(wht_tax, "amount", 1.0) or 1.0
                    raw_total = sum(wht_lines.mapped("price_subtotal"))
                    if not any(wht_lines.mapped("tax_ids")):
                        base_amt = round(raw_total / 1.07, 2)
                    else:
                        base_amt = round(raw_total, 2)
                    tax_amt = round(base_amt * rate / 100.0, 2)
                else:
                    raw_total = (
                        (voucher.amount_total if voucher else 0.0)
                        or sum(bills.mapped("amount_total"))
                    )
                    base_amt = round(raw_total / 1.07, 2) if raw_total else 0.0
                    tax_amt = round(base_amt * rate / 100.0, 2)
            elif voucher and voucher.amount_total:
                base_amt = round(voucher.amount_total / 1.07, 2)
                tax_amt = round(base_amt * rate / 100.0, 2)

            income_type = rec.wht_income_type
            if not income_type:
                if bill and bill.invoice_line_ids:
                    first_line = bill.invoice_line_ids[0]
                    prod_name = (
                        first_line.product_id.categ_id.name
                        if first_line.product_id and first_line.product_id.categ_id
                        else ""
                    )
                    income_type = prod_name or "ค่าวัสดุ"
                else:
                    income_type = "ค่าวัสดุ"

            default_cert_no = (
                (voucher.name if (voucher and voucher.name and voucher.name != _("New")) else "")
                or (rec.name if rec.name and rec.name != _("New") else "")
            )
            rec.wht_cert_no = rec.wht_cert_no or default_cert_no
            rec.wht_cheque_no = cheque_no
            rec.wht_disbursement_no = rec.wht_disbursement_no or disb_no
            rec.wht_doc_date = rec.wht_doc_date or doc_date
            rec.wht_contract_no = rec.wht_contract_no or contract_no
            rec.wht_contract_date = rec.wht_contract_date or contract_date
            rec.wht_partner_id = partner
            rec.wht_taxpayer_type = rec.wht_taxpayer_type or taxpayer_type
            rec.wht_vendor_name = (
                rec.wht_vendor_name or (partner.name if partner else "")
            )
            rec.wht_vendor_vat = (
                rec.wht_vendor_vat or (partner.vat if partner and partner.vat else "")
            )
            rec.wht_vendor_address = (
                rec.wht_vendor_address or rec._vpk_format_partner_address(partner)
            )
            rec.wht_income_type = income_type
            rec.wht_pay_date = (
                rec.wht_pay_date
                or (voucher.date if voucher else False)
                or rec.date
                or doc_date
            )
            rec.wht_rate = rate
            if not rec.wht_base_amount:
                rec.wht_base_amount = base_amt
            if not rec.wht_tax_amount:
                rec.wht_tax_amount = tax_amt
            raw_signer = (
                rec.wht_signer_name
                or (voucher.proposer_name if voucher else "")
                or "นางสาวชนากานต์  แย้มเกื้อ"
            )
            rec.wht_signer_name = raw_signer.strip().strip("()").strip()
            rec.wht_signer_position = (
                rec.wht_signer_position
                or (voucher.proposer_position if voucher else "")
                or "นักวิชาการเงินและบัญชีปฏิบัติการ"
            )

    @api.onchange("payment_voucher_id")
    def _onchange_payment_voucher_id(self):
        voucher = self.payment_voucher_id
        if not voucher:
            return
        self.bill_ids = voucher.bill_ids
        self.form_type = self._vpk_detect_form_type(voucher=voucher, bills=voucher.bill_ids)
        self.wht_cert_no = False
        self.wht_disbursement_no = False
        self.wht_contract_no = False
        self.wht_partner_id = False
        self.wht_vendor_name = False
        self.wht_vendor_vat = False
        self.wht_vendor_address = False
        self.wht_base_amount = 0.0
        self.wht_tax_amount = 0.0
        self._compute_wht_defaults()

    @api.onchange("wht_partner_id")
    def _onchange_wht_partner_id(self):
        partner = self.wht_partner_id
        if not partner:
            return
        self.wht_vendor_name = partner.name or ""
        self.wht_vendor_vat = partner.vat or ""
        self.wht_vendor_address = self._vpk_format_partner_address(partner)
        self.wht_taxpayer_type = (
            "person"
            if (not partner.is_company and partner.company_type == "person")
            else "corp"
        )

    @api.onchange("wht_base_amount", "wht_rate")
    def _onchange_wht_base_rate(self):
        if self.wht_base_amount and self.wht_rate:
            self.wht_tax_amount = round(
                self.wht_base_amount * self.wht_rate / 100.0, 2
            )

    @api.depends("wht_doc_date", "wht_contract_date")
    def _compute_wht_date_parts(self):
        for rec in self:
            if rec.wht_doc_date:
                d = rec.wht_doc_date
                rec.wht_doc_day = str(d.day)
                rec.wht_doc_month = THAI_MONTHS_FULL[d.month]
                rec.wht_doc_year = str(d.year + 543)
            else:
                rec.wht_doc_day = ""
                rec.wht_doc_month = ""
                rec.wht_doc_year = ""

            if rec.wht_contract_date:
                cd = rec.wht_contract_date
                rec.wht_contract_day = str(cd.day)
                rec.wht_contract_month = THAI_MONTHS_FULL[cd.month]
                rec.wht_contract_year = str(cd.year + 543)
            else:
                rec.wht_contract_day = ""
                rec.wht_contract_month = ""
                rec.wht_contract_year = ""

    @api.depends("wht_vendor_vat", "wht_taxpayer_type")
    def _compute_wht_tax_id_digits(self):
        for rec in self:
            digits = re.sub(r"\D", "", rec.wht_vendor_vat or "")
            is_person = rec.wht_taxpayer_type == "person"
            for i in range(1, 14):
                ch = digits[i - 1] if i <= len(digits) else ""
                setattr(rec, f"wht_cid_{i}", ch if is_person else "")
                setattr(rec, f"wht_tin_{i}", "" if is_person else ch)
                setattr(rec, f"wht_vat_{i}", ch)

    @api.depends(
        "wht_taxpayer_type",
        "wht_income_type",
        "wht_pay_date",
        "wht_base_amount",
        "wht_tax_amount",
        "wht_fine_income_type",
        "wht_fine_base_amount",
        "wht_fine_tax_amount",
    )
    def _compute_wht_table_cells(self):
        for rec in self:
            pay_date_str = rec._vpk_short_thai_date(rec.wht_pay_date)
            base_b, base_s = rec._vpk_split_baht_satang(rec.wht_base_amount)
            tax_b, tax_s = rec._vpk_split_baht_satang(rec.wht_tax_amount)
            base_fmt = rec._vpk_format_decimal(rec.wht_base_amount)
            tax_fmt = rec._vpk_format_decimal(rec.wht_tax_amount)

            if rec.wht_taxpayer_type == "person":
                rec.wht_corp_income_type = ""
                rec.wht_corp_pay_date = ""
                rec.wht_corp_base_baht = ""
                rec.wht_corp_base_satang = ""
                rec.wht_corp_tax_baht = ""
                rec.wht_corp_tax_satang = ""
                rec.wht_corp_base_formatted = ""
                rec.wht_corp_tax_formatted = ""

                rec.wht_indiv_income_type = rec.wht_income_type or ""
                rec.wht_indiv_pay_date = pay_date_str
                rec.wht_indiv_base_baht = base_b
                rec.wht_indiv_base_satang = base_s
                rec.wht_indiv_tax_baht = tax_b
                rec.wht_indiv_tax_satang = tax_s
                rec.wht_indiv_base_formatted = base_fmt
                rec.wht_indiv_tax_formatted = tax_fmt
            else:
                rec.wht_corp_income_type = rec.wht_income_type or ""
                rec.wht_corp_pay_date = pay_date_str
                rec.wht_corp_base_baht = base_b
                rec.wht_corp_base_satang = base_s
                rec.wht_corp_tax_baht = tax_b
                rec.wht_corp_tax_satang = tax_s
                rec.wht_corp_base_formatted = base_fmt
                rec.wht_corp_tax_formatted = tax_fmt

                rec.wht_indiv_income_type = ""
                rec.wht_indiv_pay_date = ""
                rec.wht_indiv_base_baht = ""
                rec.wht_indiv_base_satang = ""
                rec.wht_indiv_tax_baht = ""
                rec.wht_indiv_tax_satang = ""
                rec.wht_indiv_base_formatted = ""
                rec.wht_indiv_tax_formatted = ""

            fine_b, fine_s = rec._vpk_split_baht_satang(rec.wht_fine_base_amount)
            fine_tb, fine_ts = rec._vpk_split_baht_satang(rec.wht_fine_tax_amount)
            rec.wht_fine_pay_date = (
                pay_date_str
                if (rec.wht_fine_base_amount or rec.wht_fine_tax_amount)
                else ""
            )
            rec.wht_fine_base_baht = fine_b
            rec.wht_fine_base_satang = fine_s
            rec.wht_fine_tax_baht = fine_tb
            rec.wht_fine_tax_satang = fine_ts

            total_base = (rec.wht_base_amount or 0.0) + (
                rec.wht_fine_base_amount or 0.0
            )
            total_tax = (rec.wht_tax_amount or 0.0) + (
                rec.wht_fine_tax_amount or 0.0
            )
            tb_b, tb_s = rec._vpk_split_baht_satang(total_base)
            tt_b, tt_s = rec._vpk_split_baht_satang(total_tax)
            rec.wht_total_base_baht = tb_b
            rec.wht_total_base_satang = tb_s
            rec.wht_total_tax_baht = tt_b
            rec.wht_total_tax_satang = tt_s
            rec.wht_total_base_formatted = rec._vpk_format_decimal(total_base)
            rec.wht_total_tax_formatted = rec._vpk_format_decimal(total_tax)
            rec.wht_total_tax_text = (
                rec._baht_text(total_tax) if total_tax > 0 else ""
            )

    def action_confirm(self):
        self.write({"state": "confirmed"})
        return True

    def action_draft(self):
        self.write({"state": "draft"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def _vpk_get_template_for_form_type(self, form_type=None):
        """หาแบบฟอร์ม Document Studio ตาม form_type ('4235' หรือ 'general')."""
        self.ensure_one()
        target_type = form_type or self.form_type or "4235"
        Template = self.env["vpk.document.studio.template"].sudo()
        code = (
            WHT_GENERAL_TEMPLATE_CODE
            if target_type == "general"
            else WHT_4235_TEMPLATE_CODE
        )
        template = Template.search(
            [
                ("active", "=", True),
                ("company_id", "in", [False, self.company_id.id]),
                ("code", "=", code),
                ("source_model_id.model", "=", "vpk.wht.cert.4235"),
            ],
            order="company_id desc, id desc",
            limit=1,
        )
        if not template or not template.field_ids:
            if target_type == "general":
                Template._vpk_install_wht_general_template()
            else:
                Template._vpk_install_wht_4235_template()
            template = Template.search(
                [
                    ("active", "=", True),
                    ("company_id", "in", [False, self.company_id.id]),
                    ("code", "=", code),
                ],
                order="company_id desc, id desc",
                limit=1,
            )
        return template

    def _vpk_reload_studio_document(self, document):
        """ดึงค่าจากใบรับรองหักภาษี (vpk.wht.cert.4235) เข้าเอกสาร Studio ก่อนพิมพ์."""
        self.ensure_one()
        document.ensure_one()
        if not document.template_id:
            return document
        values = document._values_from_record(document.template_id, self)
        vals = {
            "value_json": values,
            "source_ref": "%s,%d" % (self._name, self.id),
            "wht_cert_4235_id": self.id,
            "payment_voucher_id": False,
            "body": document._filled_body_html(convert_word=True),
        }
        document.write(vals)
        return document

    def _ensure_studio_wht_document(self, form_type=None):
        """สร้าง/อัปเดตเอกสารใบรับรองหักภาษี ณ ที่จ่าย ตามแบบฟอร์ม ('4235' หรือ 'general')."""
        self.ensure_one()
        target_type = form_type or self.form_type or "4235"
        if self.form_type != target_type:
            self.form_type = target_type
        template = self._vpk_get_template_for_form_type(target_type)
        if not template:
            raise UserError(
                _("ไม่พบแบบฟอร์มใบรับรองหักภาษี ณ ที่จ่าย (%s)") % target_type
            )

        Document = self.env["vpk.document.studio.document"].sudo()
        doc_type = template.document_type_id
        document = Document.search(
            [
                ("wht_cert_4235_id", "=", self.id),
                ("template_id", "=", template.id),
                ("state", "not in", ("cancelled",)),
            ],
            order="id desc",
            limit=1,
        )
        if not document and self.payment_voucher_id:
            document = Document.search(
                [
                    ("payment_voucher_id", "=", self.payment_voucher_id.id),
                    ("template_id", "=", template.id),
                    ("state", "not in", ("cancelled",)),
                ],
                order="id desc",
                limit=1,
            )
            if document:
                document.write(
                    {
                        "wht_cert_4235_id": self.id,
                        "payment_voucher_id": False,
                    }
                )
        if not document:
            vals = {
                "source_mode": "studio",
                "template_id": template.id,
                "document_type_id": doc_type.id if doc_type else False,
                "source_ref": "%s,%d" % (self._name, self.id),
                "wht_cert_4235_id": self.id,
                "company_id": self.company_id.id,
                "note": "%s (%s)"
                % (template.display_name, self.wht_cert_no or self.name or ""),
            }
            document = Document.create(vals)
            self.message_post(
                body=_("สร้างเอกสาร %s จากแบบฟอร์ม %s")
                % (document.display_name, template.display_name),
                subtype_xmlid="mail.mt_note",
            )
        self._vpk_reload_studio_document(document)
        return document

    def action_print_wht_cert(self):
        """พิมพ์ใบรับรองหักภาษี ณ ที่จ่าย ตามแบบฟอร์มที่เลือก (4235 หรือ ทั่วไป)."""
        self.ensure_one()
        document = self._ensure_studio_wht_document(self.form_type)
        if self.state == "draft":
            self.state = "confirmed"
        return document.action_generate_pdf()

    def action_print_wht_cert_4235(self):
        """พิมพ์ใบรับรองหักภาษี ณ ที่จ่าย แบบ 4235 (จ่ายผ่าน GFMIS ตรงให้ผู้ขาย)."""
        self.ensure_one()
        document = self._ensure_studio_wht_document("4235")
        if self.state == "draft":
            self.state = "confirmed"
        return document.action_generate_pdf()

    def action_print_wht_cert_general(self):
        """พิมพ์ใบรับรองหักภาษี ณ ที่จ่าย แบบทั่วไป (จ่ายจากโรงพยาบาลเอง)."""
        self.ensure_one()
        document = self._ensure_studio_wht_document("general")
        if self.state == "draft":
            self.state = "confirmed"
        return document.action_generate_pdf()

    def action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบรับรองการหักภาษี ณ ที่จ่าย"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_studio_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสารใบรับรองหักภาษี"),
            "res_model": "vpk.document.studio.document",
            "view_mode": "list,form",
            "domain": [("wht_cert_4235_id", "=", self.id)],
            "context": {
                "default_wht_cert_4235_id": self.id,
                "default_source_ref": "%s,%d" % (self._name, self.id),
                "default_source_mode": "uploaded",
                "search_default_my_documents": 0,
            },
            "views": [
                (
                    self.env.ref(
                        "vpk_wht_cert_4235.view_document_studio_document_list_wht_cert"
                    ).id,
                    "list",
                ),
                (False, "form"),
            ],
        }


class VpkPaymentVoucherWht(models.Model):
    _inherit = "vpk.payment.voucher"

    wht_cert_4235_ids = fields.One2many(
        comodel_name="vpk.wht.cert.4235",
        inverse_name="payment_voucher_id",
        string="ใบรับรองหักภาษี",
    )
    wht_cert_4235_count = fields.Integer(
        string="จำนวนใบรับรองหักภาษี",
        compute="_compute_wht_cert_4235_count",
    )
    wht_recommended_form_type = fields.Selection(
        selection=[
            ("4235", "แบบ 4235 (จ่ายผ่าน GFMIS ตรงให้ผู้ขาย)"),
            ("general", "แบบทั่วไป (จ่ายจากโรงพยาบาลเอง)"),
        ],
        string="แบบฟอร์มตามเงื่อนไขการเบิกจ่าย",
        compute="_compute_wht_recommended_form_type",
    )

    @api.depends("wht_cert_4235_ids")
    def _compute_wht_cert_4235_count(self):
        for voucher in self:
            voucher.wht_cert_4235_count = len(voucher.wht_cert_4235_ids)

    @api.depends("bill_ids")
    def _compute_wht_recommended_form_type(self):
        Cert = self.env["vpk.wht.cert.4235"]
        for voucher in self:
            voucher.wht_recommended_form_type = Cert._vpk_detect_form_type(
                voucher=voucher, bills=voucher.bill_ids
            )

    def _ensure_wht_cert_4235(self, form_type=None):
        """หาหรือสร้างเรคคอร์ด vpk.wht.cert.4235 จากใบสำคัญจ่ายนี้."""
        self.ensure_one()
        Cert = self.env["vpk.wht.cert.4235"].sudo()
        cert = Cert.search(
            [
                ("payment_voucher_id", "=", self.id),
                ("state", "!=", "cancel"),
            ],
            order="id desc",
            limit=1,
        )
        target_type = form_type or self.wht_recommended_form_type or "4235"
        if not cert:
            cert = Cert.create(
                {
                    "payment_voucher_id": self.id,
                    "form_type": target_type,
                    "company_id": self.company_id.id,
                    "date": self.date or fields.Date.context_today(self),
                    "bill_ids": [(6, 0, self.bill_ids.ids)],
                }
            )
        elif form_type and cert.form_type != form_type:
            cert.form_type = form_type
        return cert

    def action_print_wht_cert(self):
        """พิมพ์ใบหักภาษีตามเงื่อนไขของใบสำคัญจ่าย (GFMIS -> แบบ 4235 / รพ.จ่ายเอง -> แบบทั่วไป)."""
        self.ensure_one()
        cert = self._ensure_wht_cert_4235()
        return cert.action_print_wht_cert()

    def action_print_wht_cert_4235(self):
        """เลือกพิมพ์ใบรับรองหักภาษี แบบ 4235 (จ่ายผ่าน GFMIS ตรงให้ผู้ขาย)."""
        self.ensure_one()
        cert = self._ensure_wht_cert_4235(form_type="4235")
        return cert.action_print_wht_cert_4235()

    def action_print_wht_cert_general(self):
        """เลือกพิมพ์ใบรับรองหักภาษี แบบทั่วไป (จ่ายจากโรงพยาบาลเอง)."""
        self.ensure_one()
        cert = self._ensure_wht_cert_4235(form_type="general")
        return cert.action_print_wht_cert_general()

    def action_view_wht_cert_4235(self):
        """เปิดรายการหรือฟอร์มใบรับรองหักภาษีของใบสำคัญจ่ายนี้."""
        self.ensure_one()
        certs = self.wht_cert_4235_ids.filtered(lambda c: c.state != "cancel")
        if not certs:
            certs = self._ensure_wht_cert_4235()
        if len(certs) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("ใบรับรองการหักภาษี ณ ที่จ่าย"),
                "res_model": "vpk.wht.cert.4235",
                "res_id": certs.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบรับรองการหักภาษี ณ ที่จ่าย"),
            "res_model": "vpk.wht.cert.4235",
            "view_mode": "list,form",
            "domain": [("payment_voucher_id", "=", self.id)],
            "context": {
                "default_payment_voucher_id": self.id,
                "default_bill_ids": self.bill_ids.ids,
                "default_form_type": self.wht_recommended_form_type,
            },
        }
