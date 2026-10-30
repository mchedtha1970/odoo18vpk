# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import file_path

from .docx_renderer import (
    OfficialDocumentRenderError,
    render_inspection_report_docx,
    render_integrity_over_100k_docx,
    render_purchase_approval_memo_docx,
    render_spec_price_committee_docx,
    render_specific_method_approval_docx,
    render_wa_committee_order_docx,
)
from .pdf_converter import PdfConversionError, convert_docx_bytes_to_pdf, find_soffice
from .pdf_stamp import SignatureStampError, stamp_signature_on_pdf

THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
WORK_DETAIL_PLACEHOLDER = "รายละเอียดตามเอกสารแนบท้าย"

TEMPLATE_FILES = {
    "wa_committee_order": "vpk_official_document/static/src/templates/wa_committee_order.docx",
    "integrity_over_100k": "vpk_official_document/static/src/templates/integrity_over_100k.docx",
    "spec_price_committee": "vpk_official_document/static/src/templates/spec_price_committee.docx",
    "specific_method_approval": "vpk_official_document/static/src/templates/specific_method_approval.docx",
    "winner_announcement": "vpk_purchase_agreement_egp/static/src/templates/winner_announcement.docx",
    "award_approval": "vpk_official_document/static/src/templates/award_approval.docx",
    "purchase_approval_memo": "vpk_official_document/static/src/templates/purchase_approval_memo.docx",
    "inspection_report": "vpk_official_document/static/src/templates/inspection_report.docx",
}

INSPECTION_ROLE_LABELS = {
    "chairman": "ประธานกรรมการฯ",
    "committee": "กรรมการ",
    "member": "กรรมการ",
    "secretary": "กรรมการและเลขานุการ",
}

ROLE_LABELS = {
    "chairman": "ประธานกรรมการ",
    "committee": "กรรมการ",
    "member": "กรรมการ",
    "secretary": "กรรมการและเลขานุการ",
}

# Documents that appoint a committee: signed once by the director.
COMMITTEE_ORDER_TYPES = ("wa_committee_order", "spec_price_committee")


class OfficialDocument(models.Model):
    _name = "vpk.official.document"
    _description = "หนังสือราชการ"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _order = "id desc"
    _state_from = ["draft", "generated", "to_approve"]
    _state_to = ["approved"]
    _cancel_state = "cancelled"
    _tier_validation_manual_config = False

    name = fields.Char(
        string="เลขที่เอกสาร",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    saraban_book_no = fields.Char(
        string="เลขที่จากสารบรรณ",
        tracking=True,
        help="กดปุ่มขอเลขจากระบบสารบรรณที่ฟอร์มเอกสารนี้ "
        "แต่ละหนังสือราชการที่ผูกกับใบขอซื้อต้องขอเลขของตนเอง "
        "เลขนี้แสดงที่ช่อง 'ที่' ในไฟล์ที่พิมพ์",
    )
    saraban_document_id = fields.Many2one(
        comodel_name="saraban.document",
        string="งานสารบรรณ",
        copy=False,
        ondelete="set null",
        index=True,
        tracking=True,
    )
    document_type = fields.Selection(
        selection="_selection_document_type",
        string="ประเภท",
        required=True,
        default="wa_committee_order",
        tracking=True,
    )
    source_mode = fields.Selection(
        selection=[
            ("system", "สร้างจากระบบ"),
            ("studio", "Document Studio"),
            ("uploaded", "แนบไฟล์ต้นทาง"),
        ],
        string="ที่มาเอกสาร",
        default="system",
        tracking=True,
        copy=False,
    )
    studio_template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม Document Studio",
        copy=False,
    )
    studio_document_id = fields.Many2one(
        comodel_name="vpk.document.studio.document",
        string="เอกสาร Document Studio",
        copy=False,
        ondelete="set null",
    )
    template_id = fields.Many2one(
        comodel_name="vpk.official.document.template",
        string="แบบฟอร์ม",
        domain="[('document_type', '=', document_type)]",
        tracking=True,
    )
    date = fields.Date(
        string="วันที่คำสั่ง",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    order_no = fields.Char(
        string="เลขที่คำสั่ง",
        tracking=True,
        help="เลขที่แสดงหลังคำว่า 'ที่' เช่น ๑๒๓",
    )
    year_be = fields.Char(string="ปี พ.ศ.", compute="_compute_year_be", store=True)
    agency = fields.Char(
        string="หน่วยงานในหัวคำสั่ง",
        tracking=True,
        help="ข้อความต่อจากคำว่า 'คำสั่ง' เช่น โรงพยาบาลวชิระภูเก็ต",
    )
    recipient = fields.Char(
        string="เรียน",
        tracking=True,
        help="ผู้รับบันทึกข้อความ เช่น ผู้ว่าราชการจังหวัดภูเก็ต",
    )
    subject = fields.Char(string="เรื่อง", tracking=True)
    department_name = fields.Char(string="หน่วยงานผู้ขอ")
    item_summary = fields.Char(string="รายการซื้อ/จ้าง")
    procurement_method = fields.Char(string="วิธีจัดซื้อจัดจ้าง")
    body = fields.Text(string="ย่อหน้าแรก")
    body_2 = fields.Text(string="ย่อหน้าที่ 2")
    duty = fields.Text(string="อำนาจหน้าที่")
    effective = fields.Text(string="ข้อความทั้งนี้")
    signer_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ลงนาม",
        tracking=True,
        domain=[("share", "=", False)],
    )
    signer_name = fields.Char(
        string="ชื่อผู้ลงนาม",
        compute="_compute_people_from_users",
        store=True,
        readonly=False,
    )
    signer_position = fields.Char(
        string="ตำแหน่งผู้ลงนาม",
        compute="_compute_people_from_users",
        store=True,
        readonly=False,
    )
    approver_signature = fields.Image(
        string="ลายเซ็นผู้อนุมัติ",
        copy=False,
        attachment=True,
    )
    signed_on = fields.Datetime(string="ลงนามเมื่อ", copy=False, readonly=True)
    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ/จ้าง",
        index=True,
        tracking=True,
        ondelete="set null",
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ขอ",
        related="request_id.requested_by",
        store=True,
        readonly=True,
    )
    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ",
        index=True,
        ondelete="set null",
    )
    wa_id = fields.Many2one(
        comodel_name="work.acceptance",
        string="ใบตรวจรับ",
        index=True,
        ondelete="set null",
    )
    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ e-GP",
        index=True,
        ondelete="set null",
        domain=[("requisition_type", "=", "egp_procurement")],
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="หน่วยงาน",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("generated", "สร้างไฟล์แล้ว"),
            ("to_approve", "รออนุมัติ"),
            ("approved", "อนุมัติแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    vpk_secretary_screen_state = fields.Selection(
        selection=[("checked", "ตรวจสอบแล้ว")],
        string="สถานะการตรวจสอบ",
        copy=False,
        tracking=True,
    )
    signature_state = fields.Selection(
        selection=[
            ("not_sent", "ยังไม่ส่งลงนาม"),
            ("waiting", "รอลงนาม"),
            ("signed", "ลงนามแล้ว"),
        ],
        string="สถานะการลงนาม",
        compute="_compute_signature_state",
        store=True,
    )
    signer_line_ids = fields.One2many(
        comodel_name="vpk.official.document.signer",
        inverse_name="document_id",
        string="ผู้ลงนาม",
        copy=True,
    )
    line_ids = fields.One2many(
        comodel_name="vpk.official.document.line",
        inverse_name="document_id",
        string="คณะกรรมการตรวจรับ",
        copy=True,
    )
    line_count = fields.Integer(compute="_compute_line_count")
    docx_file = fields.Binary(string="ไฟล์ Word", readonly=True, copy=False, attachment=True)
    docx_filename = fields.Char(string="ชื่อไฟล์ Word", readonly=True, copy=False)
    docx_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="เอกสาร Word",
        readonly=True,
        copy=False,
    )
    pdf_file = fields.Binary(string="ไฟล์ PDF", readonly=True, copy=False, attachment=True)
    pdf_filename = fields.Char(string="ชื่อไฟล์ PDF", readonly=True, copy=False)
    pdf_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="เอกสาร PDF",
        readonly=True,
        copy=False,
    )
    has_pdf = fields.Boolean(
        string="มีไฟล์ PDF",
        compute="_compute_has_pdf",
        store=True,
    )
    generated_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="ไฟล์เอกสาร",
        compute="_compute_generated_attachment_ids",
    )
    head_officer_id = fields.Many2one(
        comodel_name="res.users",
        string="หัวหน้าเจ้าหน้าที่",
        tracking=True,
        domain=[("share", "=", False)],
    )
    head_officer_name = fields.Char(
        string="ชื่อหัวหน้าเจ้าหน้าที่",
        compute="_compute_people_from_users",
        store=True,
        readonly=False,
    )
    head_officer_position = fields.Char(
        string="ตำแหน่งหัวหน้าเจ้าหน้าที่",
        compute="_compute_people_from_users",
        store=True,
        readonly=False,
    )
    officer_id = fields.Many2one(
        comodel_name="res.users",
        string="เจ้าหน้าที่",
        tracking=True,
        domain=[("share", "=", False)],
    )
    officer_name = fields.Char(
        string="ชื่อเจ้าหน้าที่",
        compute="_compute_people_from_users",
        store=True,
        readonly=False,
    )
    officer_position = fields.Char(
        string="ตำแหน่งเจ้าหน้าที่",
        compute="_compute_people_from_users",
        store=True,
        readonly=False,
    )
    reason_text = fields.Text(string="๑. เหตุผลและความจำเป็น")
    work_detail = fields.Text(string="๒. รายละเอียดงานที่จัดซื้อ จัดจ้าง")
    request_line_ids = fields.One2many(
        related="request_id.line_ids",
        string="รายการจัดซื้อจัดจ้าง",
        readonly=True,
    )
    price_mid_text = fields.Text(string="ราคากลางของพัสดุ")
    budget_text = fields.Text(string="วงเงิน")
    delivery_text = fields.Text(
        string="กำหนดเวลาที่ต้องการใช้พัสดุนั้น หรือให้งานนั้นแล้วเสร็จ",
    )
    method_text = fields.Text(
        string="วิธีที่จะซื้อ/จ้าง/เช่า และเหตุผลที่จะซื้อ/จ้าง",
    )
    criteria_text = fields.Text(string="หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ")
    announcement_text = fields.Text(string="ร่างประกาศ และร่างเอกสารประกวดราคา")
    legal_text = fields.Text(string="ข้อระเบียบและกฎหมาย")
    other_proposal_text = fields.Text(string="ข้อเสนออื่นๆ")
    budget_source = fields.Char(string="แหล่งงบประมาณ")
    price_mid_source = fields.Char(string="ที่มาของราคากลาง")
    delivery_days = fields.Integer(string="กำหนดส่งมอบ (วัน)")
    amount_total = fields.Monetary(
        string="วงเงิน",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    approver_acting = fields.Char(string="ปฏิบัติราชการแทน")
    note = fields.Text(string="หมายเหตุ")

    @api.model
    def _selection_document_type(self):
        return self.env["vpk.official.document.type"].selection_pairs()

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends("state")
    def _compute_signature_state(self):
        for rec in self:
            if rec.state == "approved":
                rec.signature_state = "signed"
            elif rec.state == "to_approve":
                rec.signature_state = "waiting"
            else:
                rec.signature_state = "not_sent"

    @api.depends("date")
    def _compute_year_be(self):
        for rec in self:
            rec.year_be = rec._thai_digits((rec.date.year + 543) if rec.date else "")

    def _get_field_attachment(self, explicit, res_field):
        self.ensure_one()
        if explicit:
            return explicit
        if not isinstance(self.id, int):
            return self.env["ir.attachment"]
        return self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("res_field", "=", res_field),
            ],
            limit=1,
        )

    def _get_pdf_attachment(self):
        self.ensure_one()
        return self._get_field_attachment(self.pdf_attachment_id, "pdf_file")

    def _get_docx_attachment(self):
        self.ensure_one()
        return self._get_field_attachment(self.docx_attachment_id, "docx_file")

    @api.depends("pdf_filename", "pdf_attachment_id", "pdf_file")
    def _compute_has_pdf(self):
        for rec in self:
            rec.has_pdf = bool(rec.pdf_filename or rec.pdf_attachment_id)

    @api.depends(
        "pdf_file",
        "pdf_attachment_id",
        "docx_file",
        "docx_attachment_id",
    )
    def _compute_generated_attachment_ids(self):
        for rec in self:
            attachments = rec.env["ir.attachment"]
            if isinstance(rec.id, int):
                attachments |= rec._get_pdf_attachment()
                attachments |= rec._get_docx_attachment()
            rec.generated_attachment_ids = attachments

    @api.model
    def _thai_digits(self, value):
        if value is None:
            return ""
        return str(value).translate(THAI_DIGITS)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.official.document")
                    or _("New")
                )
            self._apply_defaults(vals)
        records = super().create(vals_list)
        for rec in records:
            if not rec.order_no and rec.document_type == "wa_committee_order":
                rec.order_no = rec._next_order_no()
            rec._ensure_template()
            if rec.document_type in (
                "wa_committee_order",
                "spec_price_committee",
                "specific_method_approval",
            ):
                if not rec.body:
                    rec.body = rec._default_body()
                if not rec.subject:
                    rec.subject = rec._default_subject()
                if rec.document_type == "specific_method_approval":
                    rec.write(rec._specific_section_vals(overwrite=False))
            elif rec.document_type == "integrity_over_100k" and not rec.subject:
                rec.subject = "แบบแสดงความบริสุทธิ์ใจในการจัดซื้อจัดจ้าง"
            elif rec.document_type == "inspection_report":
                if not rec.subject:
                    rec.subject = rec._default_subject()
                if rec.wa_id:
                    if not rec.line_ids:
                        rec.line_ids = rec._committee_commands_from_source()
                    rec._seed_inspection_signers()
            elif rec.document_type == "purchase_approval_memo":
                if not rec.subject:
                    rec.subject = rec._default_subject()
                if not rec.body:
                    rec.body = rec._purchase_approval_memo_values()["intro"]
                if not rec.body_2:
                    rec.body_2 = rec._default_purchase_approval_body_2()
                rec._seed_purchase_approval_signers()
        return records

    def action_refresh_text(self):
        for rec in self:
            rec._ensure_saraban_book_no()
            vals = {
                "subject": rec._default_subject(),
                "body": rec._default_body(),
            }
            if rec.document_type == "specific_method_approval":
                if not rec.reason_text:
                    vals["reason_text"] = rec._default_reason_text()
                if not rec.budget_source:
                    vals["budget_source"] = rec._spec_budget_source()
                if rec.amount_total is False or rec.amount_total is None:
                    vals["amount_total"] = rec._spec_amount()
                vals.update(rec._specific_section_vals(overwrite=False))
                vals["work_detail"] = rec._default_work_detail()
            if rec.document_type == "purchase_approval_memo":
                vals["body"] = rec._purchase_approval_memo_values(refresh_intro=True)[
                    "intro"
                ]
                vals["body_2"] = rec._default_purchase_approval_body_2()
            rec.write(vals)
        return True

    @api.model
    def _saraban_book_no_from_request(self, request):
        if not request:
            return ""
        display = ""
        if "saraban_book_no_display" in request._fields:
            display = (request.saraban_book_no_display or "").strip()
        if not display and "saraban_book_no" in request._fields and request.saraban_book_no:
            prefix = ""
            document = request.saraban_document_id if "saraban_document_id" in request._fields else False
            if document:
                prefix = (document.org_code or "").strip()
                if prefix and not prefix.endswith("/"):
                    prefix += "/"
            display = "{}{}".format(prefix, request.saraban_book_no).strip()
        if not display and "memo_ref" in request._fields and request.memo_ref:
            prefix = ""
            if "memo_ref_prefix" in request._fields:
                prefix = (request.memo_ref_prefix or "").strip()
            display = "{}{}".format(prefix, request.memo_ref).strip()
        return display

    def _uses_pr_saraban_number(self):
        """เลขสารบรรณออกที่เอกสารแต่ละฉบับ ไม่ใช้เลขร่วมจากใบขอซื้อ."""
        self.ensure_one()
        return False

    def _saraban_doc_type(self):
        self.ensure_one()
        return {
            "wa_committee_order": "internal",
            "integrity_over_100k": "other",
            "spec_price_committee": "memo",
            "specific_method_approval": "memo",
        }.get(self.document_type, "memo")

    def _saraban_org_code(self):
        self.ensure_one()
        request = self.request_id
        if request and "memo_ref_prefix" in request._fields and request.memo_ref_prefix:
            return request.memo_ref_prefix.strip().rstrip("/")
        return "ภก ๐๐๓๓.๒๐๑"

    def _ensure_saraban_book_no(self):
        for rec in self:
            if rec.saraban_book_no:
                continue
            document = rec.saraban_document_id
            if document:
                rec.saraban_book_no = document.book_no_display or document.book_no

    def _printed_document_number(self):
        self.ensure_one()
        number = (self.saraban_book_no or "").strip()
        if number:
            return self._thai_digits(number)
        return self._thai_digits(self.name or "")

    def _committee_order_no_line(self):
        self.ensure_one()
        number = (self.saraban_book_no or "").strip()
        if number:
            number = self._thai_digits(number)
            if number.startswith("ที่"):
                return number
            return "ที่  {}".format(number)
        return "ที่  {} / {}".format(self.order_no or "....", self.year_be or "")

    @api.onchange("request_id", "document_type")
    def _onchange_request_id_saraban(self):
        return

    def action_request_saraban_number(self):
        """ขอเลขสารบรรณที่ฟอร์มเอกสารที่เกี่ยวข้องแต่ละฉบับ."""
        self.ensure_one()
        if self.state == "cancelled":
            raise UserError(_("ไม่สามารถขอเลขสารบรรณจากเอกสารที่ยกเลิกแล้ว"))
        if "saraban.document" not in self.env:
            raise UserError(_("ยังไม่ได้ติดตั้งโมดูลเชื่อมระบบสารบรรณ"))
        return self._request_own_saraban_number()

    def _request_pr_approval_saraban_number(self):
        self.ensure_one()
        if not self.request_id:
            raise UserError(_("กรุณาเชื่อมใบขอซื้อก่อนขอเลขสารบรรณ"))
        request = self.request_id
        if request.saraban_status != "registered":
            request.action_request_saraban_number()
        document = request.saraban_document_id
        number = request.saraban_book_no_display or self._saraban_book_no_from_request(
            request
        )
        if not number:
            raise UserError(_("ไม่สามารถออกเลขสารบรรณจากใบขอซื้อได้"))
        self.write(
            {
                "saraban_book_no": number,
                "saraban_document_id": document.id if document else False,
            }
        )
        self.message_post(
            body=_(
                "ใช้เลขสารบรรณจากใบขอซื้อสำหรับเอกสารอนุมัติขอซื้อ<br/>"
                "เลขที่สารบรรณ: <b>%s</b>"
            )
            % number
        )
        return True

    def _request_own_saraban_number(self):
        self.ensure_one()
        existing = self.saraban_document_id
        if existing and existing.state == "registered":
            raise UserError(
                _("เอกสารนี้มีเลขสารบรรณแล้ว (%s)")
                % (existing.book_no_display or existing.book_no)
            )
        subject = self.subject or self.name or _("หนังสือราชการ")
        vals = {
            "name": subject,
            "purpose": "official_document",
            "source_ref": "vpk.official.document/%s" % self.id,
            "official_document_id": self.id,
        }
        if existing and existing.state == "draft":
            document = existing
            document.write(vals)
        else:
            create_vals = {
                "doc_type": self._saraban_doc_type(),
                "org_code": self._saraban_org_code(),
                "company_id": self.company_id.id,
                "note": _("สร้างจากหนังสือราชการ %s") % (self.name or self.id),
            }
            create_vals.update(vals)
            if self.request_id:
                create_vals["purchase_request_id"] = self.request_id.id
            document = self.env["saraban.document"].create(create_vals)
        document.action_register()
        number = document.book_no_display or document.book_no
        self.write(
            {
                "saraban_book_no": number,
                "saraban_document_id": document.id,
            }
        )
        self.message_post(
            body=_(
                "ขอเลขจากระบบสารบรรณสำเร็จ<br/>"
                "เลขที่สารบรรณ: <b>%s</b>"
            )
            % number
        )
        return True

    def action_open_saraban_document(self):
        self.ensure_one()
        if not self.saraban_document_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "saraban.document",
            "res_id": self.saraban_document_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _apply_defaults(self, vals):
        company = self.env["res.company"].browse(
            vals.get("company_id") or self.env.company.id
        )
        doc_type = vals.get("document_type") or "wa_committee_order"
        signer_user = self._person_user_from_company(
            company, "official_doc_signer_id", "official_doc_signer_name"
        )
        if signer_user:
            vals.setdefault("signer_id", signer_user.id)
        else:
            signer_name = company.official_doc_signer_name
            signer_position = company.official_doc_signer_position
            if not signer_name and "vpk_memo_approver_name" in company._fields:
                signer_name = company.vpk_memo_approver_name
            if not signer_position and "vpk_memo_approver_position" in company._fields:
                signer_position = company.vpk_memo_approver_position
            vals.setdefault("signer_name", signer_name or "")
            vals.setdefault("signer_position", signer_position or "")
        if doc_type in (
            "spec_price_committee",
            "specific_method_approval",
            "purchase_approval_memo",
        ):
            memo_agency = ""
            if "vpk_memo_agency" in company._fields:
                memo_agency = company.vpk_memo_agency
            vals.setdefault(
                "agency",
                memo_agency or "กลุ่มงานพัสดุ โรงพยาบาลวชิระภูเก็ต",
            )
            memo_to = ""
            if "vpk_memo_default_to" in company._fields:
                memo_to = company.vpk_memo_default_to
            vals.setdefault("recipient", memo_to or "ผู้ว่าราชการจังหวัดภูเก็ต")
            if doc_type in ("specific_method_approval", "purchase_approval_memo"):
                head_user = self._person_user_from_company(
                    company,
                    "official_doc_head_officer_id",
                    "official_doc_head_officer_name",
                )
                if head_user:
                    vals.setdefault("head_officer_id", head_user.id)
                else:
                    head_name = company.official_doc_head_officer_name
                    head_position = company.official_doc_head_officer_position
                    if not head_name and "vpk_memo_proposer_name" in company._fields:
                        head_name = company.vpk_memo_proposer_name
                    if (
                        not head_position
                        and "vpk_memo_proposer_position" in company._fields
                    ):
                        head_position = company.vpk_memo_proposer_position
                    vals.setdefault("head_officer_name", head_name or "")
                    vals.setdefault(
                        "head_officer_position",
                        head_position or "หัวหน้าเจ้าหน้าที่",
                    )
                officer_user = self._person_user_from_company(
                    company, "official_doc_officer_id", "official_doc_officer_name"
                )
                if officer_user:
                    vals.setdefault("officer_id", officer_user.id)
                else:
                    officer_name = company.official_doc_officer_name
                    officer_position = company.official_doc_officer_position
                    vals.setdefault("officer_name", officer_name or "")
                    vals.setdefault(
                        "officer_position",
                        officer_position or "เจ้าหน้าที่",
                    )
                if "vpk_memo_approver_acting" in company._fields:
                    vals.setdefault(
                        "approver_acting",
                        company.vpk_memo_approver_acting or "",
                    )
            return
        vals.setdefault("agency", company.official_doc_agency or company.name)
        if doc_type == "integrity_over_100k":
            head_user = self._person_user_from_company(
                company,
                "official_doc_head_officer_id",
                "official_doc_head_officer_name",
            )
            if head_user:
                vals.setdefault("head_officer_id", head_user.id)
            else:
                head_name = company.official_doc_head_officer_name
                head_position = company.official_doc_head_officer_position
                if not head_name and "vpk_memo_proposer_name" in company._fields:
                    head_name = company.vpk_memo_proposer_name
                if (
                    not head_position
                    and "vpk_memo_proposer_position" in company._fields
                ):
                    head_position = company.vpk_memo_proposer_position
                vals.setdefault("head_officer_name", head_name or "")
                vals.setdefault(
                    "head_officer_position",
                    head_position or "หัวหน้าเจ้าหน้าที่",
                )
            officer_user = self._person_user_from_company(
                company, "official_doc_officer_id", "official_doc_officer_name"
            )
            if officer_user:
                vals.setdefault("officer_id", officer_user.id)
            else:
                officer_name = company.official_doc_officer_name
                officer_position = company.official_doc_officer_position
                vals.setdefault("officer_name", officer_name or "")
                vals.setdefault(
                    "officer_position",
                    officer_position or "เจ้าหน้าที่",
                )
            return
        if not vals.get("duty"):
            vals["duty"] = (
                "โดยให้มีอำนาจหน้าที่  ทำการตรวจรับพัสดุให้เป็นไปตามเงื่อนไขของสัญญาหรือข้อตกลงนั้น  "
                "และปฏิบัติตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
                "พ.ศ. ๒๕๖๐  หมวด  ๖  การบริหารสัญญา  และการตรวจรับพัสดุ  ข้อ  ๑๗๕"
            )
        if not vals.get("effective"):
            vals["effective"] = (
                "ทั้งนี้  ตั้งแต่บัดนี้เป็นต้นไป  หรือจนกว่าจะดำเนินการตรวจรับพัสดุแล้วเสร็จ"
            )

    def _ensure_template(self):
        for rec in self:
            if rec.template_id:
                continue
            template = rec._get_default_template()
            if template:
                rec.template_id = template.id

    def _get_default_template(self):
        self.ensure_one()
        Template = self.env["vpk.official.document.template"]
        return Template.search(
            [
                ("document_type", "=", self.document_type),
                ("company_id", "in", [self.company_id.id, False]),
            ],
            limit=1,
        )

    def _next_order_no(self):
        self.ensure_one()
        year = (self.date.year + 543) if self.date else fields.Date.context_today(self).year + 543
        last = self.search(
            [
                ("id", "!=", self.id),
                ("document_type", "=", self.document_type),
                ("company_id", "=", self.company_id.id),
                ("date", ">=", f"{year - 543}-01-01"),
                ("date", "<=", f"{year - 543}-12-31"),
            ],
            order="id desc",
            limit=1,
        )
        number = 1
        if last and last.order_no:
            raw = last.order_no.translate(str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789"))
            digits = "".join(ch for ch in raw if ch.isdigit())
            if digits:
                number = int(digits) + 1
        return self._thai_digits(number)

    def _default_subject(self):
        self.ensure_one()
        item = self.item_summary or "................................"
        if self.document_type == "spec_price_committee":
            return (
                "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดรายละเอียดคุณลักษณะเฉพาะ"
                f"และกำหนดราคากลางของ{item}"
            )
        if self.document_type == "specific_method_approval":
            return f"รายงานขออนุมัติซื้อ/จ้าง{item}  โดยวิธีเฉพาะเจาะจง"
        if self.document_type == "purchase_approval_memo":
            return f"ขออนุมัติจัดซื้อ{item}"
        if self.document_type == "inspection_report":
            return "ใบตรวจรับการจัดซื้อ/จัดจ้าง"
        method = self.procurement_method or "วิธีเฉพาะเจาะจง"
        return f"แต่งตั้งคณะกรรมการตรวจรับพัสดุ  สำหรับการซื้อ/จ้าง{item}  โดย{method}"

    def _request_department_name(self):
        self.ensure_one()
        return (
            self.department_name
            or (self.department_id.name if self.department_id else "")
            or self.company_id.name
            or "................................"
        )

    def _spec_item_count(self):
        self.ensure_one()
        request = self.request_id
        if not request:
            return 1
        lines = request.line_ids.filtered(
            lambda line: not getattr(line, "cancelled", False)
        )
        return len(lines) or 1

    def _spec_amount(self):
        self.ensure_one()
        request = self.request_id
        if request and "estimated_cost" in request._fields:
            return request.estimated_cost or 0.0
        return 0.0

    def _spec_budget_source(self):
        self.ensure_one()
        request = self.request_id
        if request and "budget_id" in request._fields and request.budget_id:
            return request.budget_id.display_name
        return ""

    def _amount_to_thai_text(self, amount):
        self.ensure_one()
        currency = self.company_id.currency_id
        try:
            text = currency.with_context(lang="th_TH").amount_to_text(amount or 0.0)
        except Exception:
            text = currency.amount_to_text(amount or 0.0)
        return text or ""

    def _default_spec_body(self):
        self.ensure_one()
        department = self._request_department_name()
        item = self.item_summary or "................................"
        method = self.procurement_method or "วิธีเฉพาะเจาะจง"
        count = self._spec_item_count()
        amount = self._spec_amount()
        amount_str = self._thai_digits("{:,.2f}".format(amount))
        baht = self._amount_to_thai_text(amount)
        if baht and "บาท" not in baht:
            baht = f"{baht}บาทถ้วน"
        budget = self._spec_budget_source()
        if budget:
            budget_part = f"โดย{method}  ใช้งบประมาณจาก{budget}  "
        else:
            budget_part = f"โดย{method}  "
        reason = ""
        if self.request_id and "expense_reason" in self.request_id._fields:
            reason = (self.request_id.expense_reason or "").strip()
        purpose = f"เพื่อ{reason}" if reason else "เพื่อใช้ในราชการ"
        return (
            f"ด้วย  {department}  มีความประสงค์จะดำเนินการจัดซื้อ/จัดจ้าง{item}  "
            f"จำนวน  {self._thai_digits(count)}  รายการ  "
            f"{budget_part}จำนวนเงิน  {amount_str}  บาท  ({baht})  "
            f"{purpose}  โดยเตรียมความพร้อมสำหรับการดำเนินงานจัดหาพัสดุตามแนวทางปฏิบัติและระเบียบที่เกี่ยวข้อง"
        )

    def _format_amount_display(self, amount=None):
        self.ensure_one()
        if amount is None:
            amount = self.amount_total or self._spec_amount()
        return self._thai_digits("{:,.2f}".format(amount or 0.0))

    def _format_qty_display(self, qty):
        qty = qty or 0.0
        if abs(qty - round(qty)) < 1e-9:
            return self._thai_digits(int(round(qty)))
        formatted = "{:.4f}".format(qty).rstrip("0").rstrip(".")
        return self._thai_digits(formatted)

    def _baht_text_display(self, amount=None):
        self.ensure_one()
        if amount is None:
            amount = self.amount_total or self._spec_amount()
        baht = self._amount_to_thai_text(amount)
        if baht and "บาท" not in baht:
            baht = f"{baht}บาทถ้วน"
        return baht

    def _default_reason_text(self):
        self.ensure_one()
        if self.reason_text:
            return self.reason_text
        reason = ""
        if self.request_id and "expense_reason" in self.request_id._fields:
            reason = (self.request_id.expense_reason or "").strip()
        if reason:
            return f"เพื่อ{reason}"
        return "เพื่อใช้ในราชการ"

    def _default_price_mid_text(self):
        self.ensure_one()
        source = self.price_mid_source or "ราคากลางตามท้องตลาด"
        return (
            f"จำนวน  {self._format_amount_display()}  บาท  "
            f"({self._baht_text_display()})  จาก{source}"
        )

    def _default_budget_text(self):
        self.ensure_one()
        budget = self.budget_source or self._spec_budget_source() or "งบประมาณของหน่วยงาน"
        return (
            f"ภายในวงเงินงบประมาณ  {self._format_amount_display()}  บาท  "
            f"({self._baht_text_display()})  โดยเบิกจ่ายจาก{budget}"
        )

    def _default_delivery_text(self):
        self.ensure_one()
        days = self.delivery_days or 30
        if (
            not self.delivery_days
            and self.request_id
            and "memo_delivery_days" in self.request_id._fields
            and self.request_id.memo_delivery_days
        ):
            days = self.request_id.memo_delivery_days
        return (
            f"กำหนดเวลาส่งมอบงานหรือให้งานแล้วเสร็จภายใน  {self._thai_digits(days)}  วัน  "
            "นับถัดจากวันที่ลงนามในสัญญา"
        )

    def _default_method_text(self):
        self.ensure_one()
        method = self.procurement_method or "วิธีเฉพาะเจาะจง"
        return (
            f"โดย{method}  ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
            "พ.ศ. ๒๕๖๐  มาตรา  ๕๖  (๒)  (ข)  การจัดซื้อจัดจ้างที่มีการผลิต  จำหน่าย  "
            "ก่อสร้าง  หรือให้บริการทั่วไป  และมีวงเงินในการจัดซื้อจัดจ้างครั้งหนึ่งไม่เกิน  "
            "๕๐๐,๐๐๐  บาท"
        )

    def _default_criteria_text(self):
        return "การพิจารณาคัดเลือกข้อเสนอโดยใช้เกณฑ์ราคา"

    def _default_announcement_text(self):
        return (
            "ไม่ต้องจัดทำร่างประกาศและร่างเอกสารประกวดราคา  "
            "เนื่องจากเป็นการจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง"
        )

    def _default_legal_text(self):
        return (
            "ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  พ.ศ. ๒๕๖๐  "
            "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
            "พ.ศ. ๒๕๖๐  และกฎกระทรวงกำหนดวงเงินการจัดซื้อจัดจ้างพัสดุโดยวิธีเฉพาะเจาะจง  "
            "วงเงินการจัดซื้อจัดจ้างที่ไม่ทำข้อตกลงเป็นหนังสือ  "
            "และวงเงินการจัดซื้อจัดจ้างในการแต่งตั้งผู้ตรวจรับพัสดุ  พ.ศ. ๒๕๖๐"
        )

    def _default_other_proposal_text(self):
        return "แต่งตั้งคณะกรรมการตรวจรับพัสดุ  ตามรายชื่อที่เสนอในหนังสือฉบับนี้"

    def _work_detail_is_blank(self):
        text = (self.work_detail or "").strip()
        return not text or text == WORK_DETAIL_PLACEHOLDER

    def _default_work_detail(self):
        self.ensure_one()
        items = self._item_values_from_request()
        if not items:
            return WORK_DETAIL_PLACEHOLDER
        lines = []
        for index, item in enumerate(items, start=1):
            name = (item.get("name") or "").strip() or "-"
            qty = self._format_qty_display(item.get("qty"))
            uom = (item.get("uom") or "").strip()
            amount = self._format_amount_display(item.get("amount"))
            qty_part = f"  จำนวน  {qty}"
            if uom:
                qty_part += f"  {uom}"
            lines.append(
                f"{self._thai_digits(index)}. {name}{qty_part}  เป็นเงิน  {amount}  บาท"
            )
        return "\n".join(lines)

    def _specific_section_vals(self, overwrite=False):
        self.ensure_one()
        vals = {}
        mapping = {
            "work_detail": self._default_work_detail,
            "price_mid_text": self._default_price_mid_text,
            "budget_text": self._default_budget_text,
            "delivery_text": self._default_delivery_text,
            "method_text": self._default_method_text,
            "criteria_text": self._default_criteria_text,
            "announcement_text": self._default_announcement_text,
            "legal_text": self._default_legal_text,
            "other_proposal_text": self._default_other_proposal_text,
        }
        for field_name, getter in mapping.items():
            blank = not self[field_name]
            if field_name == "work_detail":
                blank = self._work_detail_is_blank()
            if overwrite or blank:
                vals[field_name] = getter()
        return vals

    def _item_values_from_request(self):
        self.ensure_one()
        items = []
        request = self.request_id
        if not request:
            return items
        lines = request.line_ids.filtered(
            lambda line: not getattr(line, "cancelled", False)
        )
        for line in lines:
            qty = line.product_qty or 0.0
            amount = line.estimated_cost or 0.0
            unit_price = (amount / qty) if qty else amount
            items.append(
                {
                    "name": line.name or (line.product_id.display_name if line.product_id else "") or "",
                    "qty": qty,
                    "uom": line.product_uom_id.name if line.product_uom_id else "",
                    "unit_price": unit_price,
                    "amount": amount,
                }
            )
        return items

    def _default_specific_method_body(self):
        self.ensure_one()
        department = self._request_department_name()
        item = self.item_summary or "................................"
        amount = self.amount_total or self._spec_amount()
        amount_str = self._format_amount_display(amount)
        baht = self._baht_text_display(amount)
        budget = self.budget_source or self._spec_budget_source() or "งบประมาณของหน่วยงาน"
        reason = self._default_reason_text()
        return (
            f"ด้วย{department}  มีความประสงค์ในการจัดซื้อจัดจ้าง{item}  "
            f"เป็นจำนวนเงินทั้งสิ้น  {amount_str}  บาท  ({baht})  "
            f"{reason}  โดยใช้งบประมาณจาก{budget}  "
            "ซึ่งขอจัดซื้อจัดจ้างตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
            "พ.ศ. ๒๕๖๐  ข้อ  ๒๒  โดยมีรายละเอียด  ดังต่อไปนี้"
        )

    def _default_body(self):
        self.ensure_one()
        if self.document_type == "spec_price_committee":
            return self._default_spec_body()
        if self.document_type == "specific_method_approval":
            return self._default_specific_method_body()
        department = self._request_department_name()
        item = self.item_summary or "................................"
        method = self.procurement_method or "วิธีเฉพาะเจาะจง"
        return (
            f"ด้วย  {department}  มีความประสงค์จะดำเนินการจัดซื้อจัดจ้าง{item}  โดย{method}  "
            "เพื่อให้เป็นไปตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
            "พ.ศ. ๒๕๖๐  และตามกฎกระทรวงกำหนดวงเงินการจัดซื้อจัดจ้างพัสดุโดยวิธีเฉพาะเจาะจง  "
            "วงเงินการจัดซื้อจัดจ้างที่ไม่ทำข้อตกลงเป็นหนังสือ  "
            "และวงเงินการจัดซื้อจัดจ้างในการแต่งตั้งผู้ตรวจรับพัสดุ  พ.ศ. ๒๕๖๐  ข้อ  ๕  "
            f"จึงขอแต่งตั้งคณะกรรมการตรวจรับพัสดุ  สำหรับการจัดซื้อ/จัดจ้าง{item}  โดย{method}  ประกอบด้วย"
        )

    def _format_order_date(self):
        self.ensure_one()
        if not self.date:
            return ""
        thai_date = self.env["thai.utils"].format_thai_date(self.date)
        return self._thai_digits(thai_date)

    def _get_template_bytes(self):
        self.ensure_one()
        template = self.template_id or self._get_default_template()
        if template and template.datas:
            return base64.b64decode(template.datas)
        path = file_path(
            TEMPLATE_FILES.get(self.document_type) or TEMPLATE_FILES["wa_committee_order"]
        )
        with open(path, "rb") as handle:
            return handle.read()

    def _member_values(self):
        self.ensure_one()
        members = []
        lines = self.line_ids.sorted(key=lambda line: (line.sequence, line.id))
        for line in lines:
            members.append(
                {
                    "name": line.name,
                    "position": line.position or "",
                    "role": ROLE_LABELS.get(line.role, line.role or "กรรมการ"),
                }
            )
        return members

    def _integrity_render_values(self):
        self.ensure_one()
        members = []
        lines = self.line_ids.sorted(
            key=lambda line: (
                0 if line.role == "chairman" else 1,
                line.sequence,
                line.id,
            )
        )
        for line in lines:
            role_key = line.role if line.role in ROLE_LABELS else "committee"
            members.append(
                {
                    "name": line.name,
                    "position": line.position or "",
                    "role_key": role_key,
                }
            )
        return {
            "head_officer": {
                "name": self.head_officer_name or "",
                "position": self.head_officer_position or "หัวหน้าเจ้าหน้าที่",
            },
            "officer": {
                "name": self.officer_name or "",
                "position": self.officer_position or "เจ้าหน้าที่",
            },
            "members": members,
        }

    def _person_from_user(self, user):
        if not user:
            return "", ""
        employee = user.employee_id
        if not employee and "employee_ids" in user._fields:
            employee = user.employee_ids[:1]
        name = (employee.name if employee else "") or user.name or ""
        position = ""
        if employee:
            position = employee.job_title or (
                employee.job_id.name if employee.job_id else ""
            )
        return name, position

    @api.model
    def _user_by_person_name(self, name):
        name = " ".join((name or "").split())
        if not name:
            return self.env["res.users"]
        User = self.env["res.users"].sudo().with_context(active_test=True)
        user = User.search(
            [("name", "=", name), ("share", "=", False)],
            limit=1,
        )
        if user:
            return user
        employees = self.env["hr.employee"].sudo().search([("name", "=", name)], limit=2)
        if len(employees) == 1 and employees.user_id:
            return employees.user_id
        return self.env["res.users"]

    @api.model
    def _person_user_from_company(self, company, user_field, name_field):
        user = (
            company[user_field]
            if user_field in company._fields
            else self.env["res.users"]
        )
        if user:
            return user
        name = company[name_field] if name_field in company._fields else False
        return self._user_by_person_name(name)

    @api.depends("signer_id", "head_officer_id", "officer_id")
    def _compute_people_from_users(self):
        for rec in self:
            if rec.signer_id:
                name, position = rec._person_from_user(rec.signer_id)
                rec.signer_name = name
                rec.signer_position = (
                    position or rec.signer_position or "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต"
                )
            else:
                rec.signer_name = rec.signer_name
                rec.signer_position = rec.signer_position
            if rec.head_officer_id:
                name, position = rec._person_from_user(rec.head_officer_id)
                rec.head_officer_name = name
                rec.head_officer_position = (
                    position or rec.head_officer_position or "หัวหน้าเจ้าหน้าที่"
                )
            else:
                rec.head_officer_name = rec.head_officer_name
                rec.head_officer_position = rec.head_officer_position
            if rec.officer_id:
                name, position = rec._person_from_user(rec.officer_id)
                rec.officer_name = name
                rec.officer_position = (
                    position or rec.officer_position or "เจ้าหน้าที่"
                )
            else:
                rec.officer_name = rec.officer_name
                rec.officer_position = rec.officer_position

    def _render_values(self):
        self.ensure_one()
        return {
            "agency": self.agency or self.company_id.name or "",
            "order_no": self.order_no or "....",
            "year_be": self.year_be or self._thai_digits(
                (self.date.year + 543) if self.date else ""
            ),
            "order_no_line": self._committee_order_no_line(),
            "subject": self.subject or self._default_subject(),
            "body": self.body or self._default_body(),
            "members": self._member_values(),
            "duty": self.duty,
            "effective": self.effective,
            "order_date": self._format_order_date(),
            "signer_name": self.signer_name or "",
            "signer_position": self.signer_position or "",
        }

    def _spec_render_values(self):
        self.ensure_one()
        signer_org = self.signer_position or ""
        if "ผู้อำนวยการ" not in signer_org:
            signer_org = "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต"
        return {
            "agency": self.agency or self.company_id.name or "",
            "memo_number": self._printed_document_number(),
            "order_date": self._format_order_date(),
            "subject": self.subject or self._default_subject(),
            "recipient": self.recipient or "ผู้ว่าราชการจังหวัดภูเก็ต",
            "body": self.body or self._default_body(),
            "members": self._member_values(),
            "signer_name": self.signer_name or "",
            "signer_position": self.signer_position or "",
            "signer_org": signer_org,
        }

    def _specific_method_render_values(self):
        self.ensure_one()
        amount = self.amount_total or self._spec_amount()
        delivery = self.delivery_days
        if not delivery and self.request_id and "memo_delivery_days" in self.request_id._fields:
            delivery = self.request_id.memo_delivery_days
        delivery = delivery or 30
        acting = self.approver_acting or ""
        if not acting and "vpk_memo_approver_acting" in self.company_id._fields:
            acting = self.company_id.vpk_memo_approver_acting or ""
        return {
            "agency": self.agency or self.company_id.name or "",
            "memo_number": self._printed_document_number(),
            "order_date": self._format_order_date(),
            "subject": self.subject or self._default_subject(),
            "recipient": self.recipient or "ผู้ว่าราชการจังหวัดภูเก็ต",
            "body": self.body or self._default_specific_method_body(),
            "reason": self.reason_text or self._default_reason_text(),
            "work_detail": (
                (self.work_detail or "").strip()
                if not self._work_detail_is_blank()
                else self._default_work_detail()
            ),
            "price_mid_text": self.price_mid_text or self._default_price_mid_text(),
            "budget_text": self.budget_text or self._default_budget_text(),
            "delivery_text": self.delivery_text or self._default_delivery_text(),
            "method_text": self.method_text or self._default_method_text(),
            "criteria_text": self.criteria_text or self._default_criteria_text(),
            "announcement_text": (
                self.announcement_text or self._default_announcement_text()
            ),
            "legal_text": self.legal_text or self._default_legal_text(),
            "other_proposal_text": (
                self.other_proposal_text or self._default_other_proposal_text()
            ),
            "amount_text": self._format_amount_display(amount),
            "baht_text": self._baht_text_display(amount),
            "price_mid_source": self.price_mid_source or "ราคากลางตามท้องตลาด",
            "budget_source": self.budget_source or self._spec_budget_source() or "งบประมาณของหน่วยงาน",
            "delivery_days": self._thai_digits(delivery),
            "members": self._member_values(),
            "officer_name": self.officer_name or "",
            "officer_position": self.officer_position or "เจ้าหน้าที่",
            "head_officer_name": self.head_officer_name or "",
            "head_officer_position": self.head_officer_position or "หัวหน้าเจ้าหน้าที่",
            "signer_name": self.signer_name or "",
            "signer_position": self.signer_position or "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต",
            "approver_acting": acting or "ปฏิบัติราชการแทนผู้ว่าราชการจังหวัดภูเก็ต",
        }

    def action_load_committee_from_source(self):
        for rec in self:
            rec.line_ids.unlink()
            rec.line_ids = rec._committee_commands_from_source()
            if not rec.line_ids:
                if rec.document_type == "spec_price_committee":
                    raise UserError(
                        _("ไม่พบคณะกรรมการราคากลางในใบขอซื้อที่อ้างอิง")
                    )
                raise UserError(
                    _("ไม่พบคณะกรรมการตรวจรับในใบขอซื้อหรือใบตรวจรับที่อ้างอิง")
                )
            if rec.document_type == "inspection_report":
                rec._seed_inspection_signers(replace=True)
        return True

    def _pr_committee_records(self):
        self.ensure_one()
        request = self.request_id
        empty = self.env["procurement.committee"]
        if not request:
            return empty
        if self.document_type == "spec_price_committee":
            if "price_mid_committee_ids" in request._fields:
                return request.price_mid_committee_ids
            return empty
        if "work_acceptance_committee_ids" in request._fields:
            return request.work_acceptance_committee_ids
        return empty

    def _committee_commands_from_source(self):
        self.ensure_one()
        commands = []
        sequence = 10
        pr_members = self._pr_committee_records()
        if self.document_type == "inspection_report" and self.wa_id.committee_ids:
            # ใบตรวจรับใช้กรรมการตรวจรับของใบรับมอบงานก่อน
            pr_members = self.env["procurement.committee"]
        if pr_members:
            for member in pr_members:
                role = member.approve_role or "committee"
                commands.append(
                    (
                        0,
                        0,
                        {
                            "sequence": sequence,
                            "employee_id": member.employee_id.id,
                            "user_id": member.employee_id.user_id.id,
                            "name": member.name or member.employee_id.name,
                            "position": self._employee_position(member.employee_id),
                            "role": role if role in ROLE_LABELS else "committee",
                            "note": member.note or "",
                        },
                    )
                )
                sequence += 10
            return commands
        if self.wa_id and "committee_ids" in self.wa_id._fields:
            for member in self.wa_id.committee_ids:
                role = member.role or "member"
                if role == "member":
                    role = "committee"
                wa_user = member.employee_id
                employee = wa_user.employee_id if wa_user else False
                commands.append(
                    (
                        0,
                        0,
                        {
                            "sequence": sequence,
                            "employee_id": employee.id if employee else False,
                            "user_id": wa_user.id if wa_user else False,
                            "name": member.name,
                            "position": member.position or "",
                            "role": role if role in ROLE_LABELS else "committee",
                            "note": member.note or "",
                        },
                    )
                )
                sequence += 10
        return commands

    def _employee_position(self, employee):
        if not employee:
            return ""
        return employee.job_title or (employee.job_id.name if employee.job_id else "")

    @api.model
    def _find_existing_document(self, document_type, request=None, acceptance=None):
        domain = [
            ("document_type", "=", document_type),
            ("state", "!=", "cancelled"),
        ]
        if request:
            domain.append(("request_id", "=", request.id))
        elif acceptance:
            domain.append(("wa_id", "=", acceptance.id))
        else:
            return self.browse()
        return self.search(domain, order="id desc", limit=1)

    @api.model
    def _find_existing_wa_committee_order(self, request=None, acceptance=None):
        return self._find_existing_document(
            "wa_committee_order", request=request, acceptance=acceptance
        )

    def action_open_form(self):
        self.ensure_one()
        if self.source_mode == "studio" and self.studio_document_id:
            return self.action_open_studio_document()
        return self._action_open_form()

    def action_open_studio_document(self):
        self.ensure_one()
        if not self.studio_document_id:
            raise UserError(_("ยังไม่มีเอกสาร Document Studio ที่ผูกกับรายการนี้"))
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร Document Studio"),
            "res_model": "vpk.document.studio.document",
            "res_id": self.studio_document_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_delete_from_request(self):
        self.ensure_one()
        if self.state in ("to_approve", "approved"):
            raise UserError(
                _("ไม่สามารถลบเอกสารที่ส่งลงนามหรืออนุมัติแล้ว")
            )
        if self.signature_state in ("waiting", "signed"):
            raise UserError(_("ไม่สามารถลบเอกสารที่อยู่ระหว่างลงนามหรือลงนามแล้ว"))
        self.sudo().unlink()
        return True

    def _attach_uploaded_file(self, file_b64, filename):
        self.ensure_one()
        if not file_b64:
            raise UserError(_("กรุณาแนบไฟล์ต้นทาง"))
        raw = base64.b64decode(file_b64)
        name = filename or "document.pdf"
        lower = name.lower()
        if lower.endswith(".pdf"):
            self._store_generated_file(raw, name, "application/pdf", "pdf")
            return
        if lower.endswith(".docx"):
            self._store_generated_file(
                raw,
                name,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "docx",
            )
            return
        attachment = self.env["ir.attachment"].create(
            {
                "name": name,
                "datas": file_b64,
                "res_model": self._name,
                "res_id": self.id,
                "type": "binary",
            }
        )
        self.message_post(
            body=_("แนบไฟล์ต้นทาง %s แล้ว") % name,
            attachment_ids=[attachment.id],
            subtype_xmlid="mail.mt_note",
        )

    def _action_open_form(self):
        self.ensure_one()
        titles = {
            "wa_committee_order": "คำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
            "integrity_over_100k": "แบบแสดงความบริสุทธิ์ใจ",
            "spec_price_committee": "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดคุณลักษณะ",
            "specific_method_approval": "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
            "purchase_approval_memo": "บันทึกข้อความอนุมัติขอซื้อ",
            "winner_announcement": "ประกาศผู้ชนะการเสนอราคา",
            "inspection_report": "ใบตรวจรับการจัดซื้อ/จัดจ้าง",
        }
        return {
            "type": "ir.actions.act_window",
            "name": titles.get(self.document_type, "หนังสือราชการ"),
            "res_model": "vpk.official.document",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def create_from_purchase_request(self, request):
        request.ensure_one()
        existing = self._find_existing_wa_committee_order(request=request)
        if existing:
            return existing
        if not request.work_acceptance_committee_ids:
            raise UserError(
                _("กรุณาบันทึกคณะกรรมการตรวจรับในแท็บคณะกรรมการก่อนออกคำสั่ง")
            )
        item = self._item_summary_from_request(request)
        method = self._method_from_request(request)
        department_name = (
            request.department_id.name
            if request.department_id
            else request.company_id.name
        )
        document = self.create(
            {
                "document_type": "wa_committee_order",
                "request_id": request.id,
                "department_id": request.department_id.id,
                "department_name": department_name,
                "item_summary": item,
                "procurement_method": method,
                "company_id": request.company_id.id,
            }
        )
        document.line_ids = document._committee_commands_from_source()
        document.subject = document._default_subject()
        document.body = document._default_body()
        return document

    @api.model
    def _recipient_from_request(self, request):
        if "committee_memo_to" in request._fields and request.committee_memo_to:
            return request.committee_memo_to
        if "memo_to" in request._fields and request.memo_to:
            return request.memo_to
        company = request.company_id
        if "vpk_memo_default_to" in company._fields and company.vpk_memo_default_to:
            return company.vpk_memo_default_to
        return "ผู้ว่าราชการจังหวัดภูเก็ต"

    @api.model
    def create_spec_price_committee_from_purchase_request(self, request):
        request.ensure_one()
        existing = self._find_existing_document(
            "spec_price_committee", request=request
        )
        if existing:
            return existing
        if (
            "price_mid_committee_ids" not in request._fields
            or not request.price_mid_committee_ids
        ):
            raise UserError(
                _("กรุณาบันทึกคณะกรรมการราคากลางในแท็บคณะกรรมการก่อนออกหนังสือ")
            )
        item = self._item_summary_from_request(request)
        method = self._method_from_request(request)
        department_name = (
            request.department_id.name
            if request.department_id
            else request.company_id.name
        )
        document = self.create(
            {
                "document_type": "spec_price_committee",
                "request_id": request.id,
                "department_id": request.department_id.id,
                "department_name": department_name,
                "item_summary": item,
                "procurement_method": method,
                "recipient": self._recipient_from_request(request),
                "company_id": request.company_id.id,
            }
        )
        document.line_ids = document._committee_commands_from_source()
        document.subject = document._default_subject()
        document.body = document._default_body()
        return document

    @api.model
    def create_specific_method_approval_from_purchase_request(self, request):
        request.ensure_one()
        existing = self._find_existing_document(
            "specific_method_approval", request=request
        )
        if existing:
            return existing
        item = self._item_summary_from_request(request)
        method = self._method_from_request(request) or "วิธีเฉพาะเจาะจง"
        department_name = (
            request.department_id.name
            if request.department_id
            else request.company_id.name
        )
        amount = request.estimated_cost if "estimated_cost" in request._fields else 0.0
        delivery = 30
        if "memo_delivery_days" in request._fields and request.memo_delivery_days:
            delivery = request.memo_delivery_days
        budget = ""
        if "budget_id" in request._fields and request.budget_id:
            budget = request.budget_id.display_name
        reason = ""
        if "expense_reason" in request._fields and request.expense_reason:
            reason = f"เพื่อ{request.expense_reason.strip()}"
        document = self.create(
            {
                "document_type": "specific_method_approval",
                "request_id": request.id,
                "department_id": request.department_id.id,
                "department_name": department_name,
                "item_summary": item,
                "procurement_method": method,
                "recipient": (
                    request.memo_to
                    if "memo_to" in request._fields and request.memo_to
                    else self._recipient_from_request(request)
                ),
                "amount_total": amount,
                "delivery_days": delivery,
                "budget_source": budget,
                "reason_text": reason or "เพื่อใช้ในราชการ",
                "company_id": request.company_id.id,
            }
        )
        document._apply_integrity_people_from_request(request)
        document.line_ids = document._committee_commands_from_source()
        document.subject = document._default_subject()
        document.body = document._default_body()
        return document

    @api.model
    def create_purchase_approval_memo_from_purchase_request(self, request):
        request.ensure_one()
        existing = self._find_existing_document(
            "purchase_approval_memo", request=request
        )
        if existing:
            return existing
        item = self._item_summary_from_request(request)
        method = self._method_from_request(request) or "วิธีเฉพาะเจาะจง"
        department_name = (
            request.department_id.name
            if request.department_id
            else request.company_id.name
        )
        amount = request.estimated_cost if "estimated_cost" in request._fields else 0.0
        budget = ""
        if "budget_id" in request._fields and request.budget_id:
            budget = request.budget_id.display_name
        reason = ""
        if "expense_reason" in request._fields and request.expense_reason:
            reason = request.expense_reason.strip()
        document = self.create(
            {
                "document_type": "purchase_approval_memo",
                "request_id": request.id,
                "department_id": request.department_id.id,
                "department_name": department_name,
                "item_summary": item,
                "procurement_method": method,
                "recipient": (
                    request.memo_to
                    if "memo_to" in request._fields and request.memo_to
                    else self._recipient_from_request(request)
                ),
                "amount_total": amount,
                "budget_source": budget,
                "reason_text": reason,
                "company_id": request.company_id.id,
            }
        )
        document._apply_integrity_people_from_request(request)
        document.subject = document._default_subject()
        document.body = document._purchase_approval_memo_values()["intro"]
        document.body_2 = document._default_purchase_approval_body_2()
        document._seed_purchase_approval_signers()
        return document

    def _apply_integrity_people_from_request(self, request):
        self.ensure_one()
        company = request.company_id
        vals = {}
        officer_user = self._person_user_from_company(
            company, "official_doc_officer_id", "official_doc_officer_name"
        )
        if not officer_user:
            officer_user = request.assigned_to or request.requested_by
        if officer_user and not self.officer_id:
            vals["officer_id"] = officer_user.id
        elif not officer_user:
            officer_name, officer_position = self._person_from_user(
                request.assigned_to or request.requested_by
            )
            if officer_name and not self.officer_name:
                vals["officer_name"] = officer_name
            if officer_position and not self.officer_position:
                vals["officer_position"] = officer_position or "เจ้าหน้าที่"
        if vals:
            self.write(vals)

    @api.model
    def create_integrity_from_purchase_request(self, request):
        request.ensure_one()
        existing = self._find_existing_document("integrity_over_100k", request=request)
        if existing:
            return existing
        item = self._item_summary_from_request(request)
        method = self._method_from_request(request)
        department_name = (
            request.department_id.name
            if request.department_id
            else request.company_id.name
        )
        document = self.create(
            {
                "document_type": "integrity_over_100k",
                "request_id": request.id,
                "department_id": request.department_id.id,
                "department_name": department_name,
                "item_summary": item,
                "procurement_method": method,
                "company_id": request.company_id.id,
            }
        )
        document._apply_integrity_people_from_request(request)
        document.line_ids = document._committee_commands_from_source()
        return document

    @api.model
    def create_inspection_report_from_work_acceptance(self, acceptance):
        """สร้างใบตรวจรับจากใบรับมอบงาน (ถ้ามีแล้วเปิดฉบับเดิม)."""
        acceptance.ensure_one()
        existing = self._find_existing_document(
            "inspection_report", acceptance=acceptance
        )
        if existing:
            return existing
        request = self._request_from_work_acceptance(acceptance)
        document = self.create(
            {
                "document_type": "inspection_report",
                "wa_id": acceptance.id,
                "purchase_id": acceptance.purchase_id.id,
                "request_id": request.id if request else False,
                "department_id": request.department_id.id if request else False,
                "date": acceptance.acceptance_date or fields.Date.context_today(self),
                "item_summary": (
                    acceptance.purchase_id.name if acceptance.purchase_id else acceptance.name
                ),
                "company_id": acceptance.company_id.id,
            }
        )
        if not document.signer_line_ids:
            raise UserError(
                _("กรุณาบันทึกคณะกรรมการตรวจรับในแท็บคณะกรรมการก่อนออกใบตรวจรับ")
            )
        return document

    def _seed_inspection_signers(self, replace=False):
        """ผู้ลงนามเริ่มต้นคือกรรมการตรวจรับ (ประธานก่อน) แก้ไขในตารางผู้อนุมัติได้."""
        Signer = self.env["vpk.official.document.signer"]
        for rec in self.filtered(lambda doc: doc.document_type == "inspection_report"):
            if rec.signer_line_ids and not replace:
                continue
            if replace:
                rec.signer_line_ids.with_context(vpk_skip_signer_sync=True).unlink()
            rows = []
            seen = set()
            for line in rec._vpk_integrity_committee_lines():
                user = rec._vpk_line_signer_user(line)
                if not user or user.id in seen:
                    continue
                seen.add(user.id)
                if not line.user_id:
                    line.write({"user_id": user.id})
                _name, position = rec._person_from_user(user)
                rows.append(
                    {
                        "document_id": rec.id,
                        "sequence": len(rows) + 1,
                        "user_id": user.id,
                        "position": line.position or position,
                        "is_sign": True,
                    }
                )
            if rows:
                Signer.with_context(vpk_skip_signer_sync=True).create(rows)
                rec._sync_signers_from_lines()

    def _inspection_signer_rows(self):
        """ผู้ลงนามที่พิมพ์ในใบตรวจรับ ตามตารางผู้อนุมัติ (ชื่อต้องตรงกับที่ใช้ประทับลายเซ็น)."""
        self.ensure_one()
        role_by_user = {}
        for line in self.line_ids:
            user = self._vpk_line_signer_user(line)
            if user:
                role_by_user[user.id] = line.role
        rows = []
        signers = self.signer_line_ids.filtered(
            lambda item: item.user_id and not (item.is_check and not item.is_sign)
        ).sorted(key=lambda item: (item.sequence, item.id))
        for signer in signers:
            name, _position = self._person_from_user(signer.user_id)
            role = role_by_user.get(signer.user_id.id, "committee")
            rows.append(
                {
                    "role": INSPECTION_ROLE_LABELS.get(role, "กรรมการ"),
                    "name": name or signer.user_id.name,
                }
            )
        if rows:
            return rows
        for line in self.line_ids.sorted(key=lambda item: (item.sequence, item.id)):
            rows.append(
                {
                    "role": INSPECTION_ROLE_LABELS.get(line.role, "กรรมการ"),
                    "name": (line.name or "").strip("()"),
                }
            )
        return rows

    def _inspection_render_values(self):
        self.ensure_one()
        wa = self.sudo().wa_id
        if not wa:
            raise UserError(_("ใบตรวจรับต้องอ้างอิงใบรับมอบงาน"))
        purchase = wa.purchase_id
        contract = wa.contract_id
        request = self.sudo().request_id or self._request_from_work_acceptance(wa)
        company = self.company_id
        thai = self._thai_digits

        def thai_date(value):
            if not value:
                return ""
            return thai(self.env["thai.utils"].format_thai_date(value))

        if contract:
            ref_text = "ตาม สัญญา เลขที่ {} ลงวันที่ {}".format(
                thai(contract.name), thai_date(contract.date_start)
            )
            total = contract.amount_total
        else:
            order_date = purchase.date_approve or purchase.date_order
            if hasattr(order_date, "date"):
                order_date = order_date.date()
            ref_text = "ตาม ใบสั่งซื้อ เลขที่ {} ลงวันที่ {}".format(
                thai(purchase.name or ""), thai_date(order_date)
            )
            total = purchase.amount_total
        kind_names = ""
        if request:
            kind_names = " ".join(
                filter(
                    None,
                    [
                        request.procurement_type_id.name
                        if "procurement_type_id" in request._fields
                        else "",
                        request.purchase_type_id.name
                        if "purchase_type_id" in request._fields
                        else "",
                    ],
                )
            )
        found = [word for word in ("ซื้อ", "จ้าง", "เช่า") if word in kind_names]
        if len(found) == 1:
            verb = found[0]
        else:
            # ชื่อประเภทรวมหลายคำ (เช่น ซื้อ/จ้าง/เช่า) ให้ดูจากชนิดสินค้าในใบสั่งซื้อ
            products = purchase.order_line.mapped("product_id")
            verb = (
                "จ้าง"
                if products and all(p.type == "service" for p in products)
                else "ซื้อ"
            )
        project = ""
        for source in (purchase, request):
            if source and "egp_project_name" in source._fields and source.egp_project_name:
                project = source.egp_project_name
                break
        if not project and request:
            project = self._item_summary_from_request(request)
        project = project or purchase.name or wa.name or ""
        method = (
            self.procurement_method
            or (self._method_from_request(request) if request else "")
            or "วิธีเฉพาะเจาะจง"
        )
        if not method.startswith("วิธี"):
            method = f"วิธี{method}"
        intro = "{} {} ได้ตกลง {} กับ {} สำหรับโครงการ {} โดย{} เป็นจำนวนเงินทั้งสิ้น {} บาท ({})".format(
            ref_text,
            company.name or "",
            verb,
            purchase.partner_id.name or "",
            project,
            method,
            self._format_amount_display(total),
            self._baht_text_display(total),
        )
        installment = wa.contract_installment_id
        if installment:
            inspect_intro = "คณะกรรมการตรวจรับพัสดุ ได้ตรวจรับงาน{} แล้ว ผลปรากฏ ดังนี้".format(
                thai(installment.name)
            )
        else:
            inspect_intro = "คณะกรรมการตรวจรับพัสดุ ได้ตรวจรับพัสดุแล้ว ผลปรากฏ ดังนี้"
        checked, unchecked = "☑", "☐"
        penalty = wa.penalty_amount or 0.0
        has_penalty = bool(wa.has_penalty)
        complete = wa.inspection_completeness != "incomplete"
        payout = wa.payment_amount or 0.0
        project_no = ""
        for source in (purchase, request):
            if source and "egp_project_reference" in source._fields and source.egp_project_reference:
                project_no = source.egp_project_reference
                break
        return {
            "report_date": "วันที่ {}".format(self._format_order_date()),
            "intro": intro,
            "inspect_intro": inspect_intro,
            "chk_correct": checked if wa.inspection_correct else unchecked,
            "chk_complete": checked if complete else unchecked,
            "chk_incomplete": unchecked if complete else checked,
            "chk_fine": checked if has_penalty else unchecked,
            "fine_text": (
                " เป็นจำนวนเงิน {} บาท".format(self._format_amount_display(penalty))
                if has_penalty and penalty > 0
                else ""
            ),
            "chk_nofine": unchecked if has_penalty else checked,
            "pay_amount": self._format_amount_display(payout),
            "signers": self._inspection_signer_rows(),
            "project_no": thai(project_no or "-"),
            "contract_no": thai((contract.name if contract else "") or "-"),
            "wa_no": thai(wa.name or "-"),
        }

    @api.model
    def create_integrity_from_work_acceptance(self, acceptance):
        acceptance.ensure_one()
        request = self._request_from_work_acceptance(acceptance)
        existing = (
            self._find_existing_document("integrity_over_100k", request=request)
            if request
            else self.browse()
        )
        if not existing:
            existing = self._find_existing_document(
                "integrity_over_100k", acceptance=acceptance
            )
        if existing:
            vals = {}
            if not existing.wa_id:
                vals["wa_id"] = acceptance.id
            if acceptance.purchase_id and not existing.purchase_id:
                vals["purchase_id"] = acceptance.purchase_id.id
            if vals:
                existing.write(vals)
            return existing
        if request:
            document = self.create_integrity_from_purchase_request(request)
            document.wa_id = acceptance.id
            document.purchase_id = acceptance.purchase_id.id
            if not document.line_ids:
                document.line_ids = document._committee_commands_from_source()
            return document
        document = self.create(
            {
                "document_type": "integrity_over_100k",
                "wa_id": acceptance.id,
                "purchase_id": acceptance.purchase_id.id,
                "item_summary": (
                    acceptance.purchase_id.name if acceptance.purchase_id else acceptance.name
                ),
                "company_id": acceptance.company_id.id,
            }
        )
        document.line_ids = document._committee_commands_from_source()
        return document

    @api.model
    def create_from_work_acceptance(self, acceptance):
        acceptance.ensure_one()
        request = self._request_from_work_acceptance(acceptance)
        existing = self._find_existing_wa_committee_order(request=request) if request else self.browse()
        if not existing:
            existing = self._find_existing_wa_committee_order(acceptance=acceptance)
        if existing:
            vals = {}
            if not existing.wa_id:
                vals["wa_id"] = acceptance.id
            if acceptance.purchase_id and not existing.purchase_id:
                vals["purchase_id"] = acceptance.purchase_id.id
            if vals:
                existing.write(vals)
            return existing
        if request and request.work_acceptance_committee_ids:
            document = self.create_from_purchase_request(request)
            document.wa_id = acceptance.id
            document.purchase_id = acceptance.purchase_id.id
            return document
        if not acceptance.committee_ids:
            raise UserError(
                _("กรุณาบันทึกคณะกรรมการตรวจรับในแท็บคณะกรรมการก่อนออกคำสั่ง")
            )
        item = acceptance.purchase_id.name if acceptance.purchase_id else acceptance.name
        document = self.create(
            {
                "document_type": "wa_committee_order",
                "wa_id": acceptance.id,
                "purchase_id": acceptance.purchase_id.id,
                "request_id": request.id if request else False,
                "item_summary": item,
                "company_id": acceptance.company_id.id,
            }
        )
        document.line_ids = document._committee_commands_from_source()
        document.subject = document._default_subject()
        document.body = document._default_body()
        return document

    @api.model
    def _request_from_work_acceptance(self, acceptance):
        purchase = acceptance.purchase_id
        if not purchase:
            return self.env["purchase.request"]
        if "purchase_request_lines" not in purchase.order_line._fields:
            return self.env["purchase.request"]
        requests = purchase.order_line.mapped("purchase_request_lines.request_id")
        return requests[:1]

    @api.model
    def _item_summary_from_request(self, request):
        if "memo_item_summary" in request._fields and request.memo_item_summary:
            return request.memo_item_summary
        lines = request.line_ids.filtered(
            lambda line: not getattr(line, "cancelled", False)
        )
        if lines:
            line = lines[0]
            return line.name or line.product_id.display_name or request.name
        return request.description or request.name or ""

    @api.model
    def _method_from_request(self, request):
        if "memo_procurement_method" in request._fields and request.memo_procurement_method:
            return request.memo_procurement_method
        if request.procurement_method_id:
            return request.procurement_method_id.name
        return "วิธีเฉพาะเจาะจง"

    def _output_basename(self):
        self.ensure_one()
        suffix = self.order_no or self.name
        source = self.sudo().request_id.name or self.sudo().wa_id.name or self.id
        if self.document_type == "inspection_report":
            return "ใบตรวจรับ-{}".format(self.sudo().wa_id.name or self.name)
        if self.document_type == "integrity_over_100k":
            return "แบบแสดงความบริสุทธิ์ใจ-{}-{}".format(suffix, source)
        if self.document_type == "spec_price_committee":
            return "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดคุณลักษณะ-{}-{}".format(
                suffix, source
            )
        if self.document_type == "specific_method_approval":
            return "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง-{}-{}".format(
                suffix, source
            )
        if self.document_type == "winner_announcement":
            source = (
                self.sudo().requisition_id.egp_reference
                or self.sudo().requisition_id.name
                or source
            )
            return "ประกาศผู้ชนะ-{}".format(source)
        return "คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ-{}-{}".format(suffix, source)

    def _store_generated_file(self, content, filename, mimetype, kind):
        self.ensure_one()
        field_file, field_name, field_attach = {
            "docx": ("docx_file", "docx_filename", "docx_attachment_id"),
            "pdf": ("pdf_file", "pdf_filename", "pdf_attachment_id"),
        }[kind]
        old_attachment = self[field_attach]
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "datas": base64.b64encode(content),
                "res_model": self._name,
                "res_id": self.id,
                "type": "binary",
                "mimetype": mimetype,
            }
        )
        next_state = (
            self.state if self.state in ("to_approve", "approved") else "generated"
        )
        self.write(
            {
                "state": next_state,
                field_file: base64.b64encode(content),
                field_name: filename,
                field_attach: attachment.id,
            }
        )
        if old_attachment:
            old_attachment.unlink()
        self.message_post(
            body=_("แนบไฟล์ %s แล้ว") % filename,
            attachment_ids=[attachment.id],
            subtype_xmlid="mail.mt_note",
        )
        self._sync_winner_egp_attachment()
        return attachment

    def _purchase_approval_item_lines(self):
        self.ensure_one()
        request = self.request_id
        lines = []
        if request:
            source = request.line_ids.filtered(
                lambda line: not getattr(line, "cancelled", False) and line.product_qty
            )
            for index, line in enumerate(source, start=1):
                name = (line.name or line.product_id.display_name or "").strip()
                qty = self._format_qty_display(line.product_qty)
                uom = line.product_uom_id.name if "product_uom_id" in line._fields else ""
                amount = self._format_amount_display(line.estimated_cost or 0.0)
                detail = "%s จำนวน %s" % (name, qty)
                if uom:
                    detail = "%s %s" % (detail, uom)
                detail = "%s เป็นเงิน %s บาท" % (detail, amount)
                lines.append("%s. %s" % (self._thai_digits(index), detail))
        if lines:
            return lines
        text = (self.work_detail or "").strip()
        if not text:
            return []
        result = []
        for index, raw in enumerate(
            [line.strip() for line in text.splitlines() if line.strip()], start=1
        ):
            if raw[:1].isdigit() or raw[:1] in "๐๑๒๓๔๕๖๗๘๙":
                result.append(raw)
            else:
                result.append("%s. %s" % (self._thai_digits(index), raw))
        return result

    def _default_purchase_approval_body_2(self):
        self.ensure_one()
        item = self.item_summary or self.subject or "พัสดุตามรายการ"
        method = self.procurement_method or "วิธีเฉพาะเจาะจง"
        return (
            "ทั้งนี้  ได้ตรวจสอบความจำเป็นและงบประมาณแล้ว  "
            "เห็นควรอนุมัติให้จัดซื้อ%s  โดย%s  "
            "ตามรายละเอียดข้างต้น"
            % (item, method)
        )

    def _seed_default_approvers(self, replace=False):
        """Fill the approver table from officer, head, secretary, and director."""
        Signer = self.env["vpk.official.document.signer"]
        for rec in self:
            if rec.signer_line_ids and not replace:
                continue
            if replace and rec.signer_line_ids:
                rec.signer_line_ids.with_context(vpk_skip_signer_sync=True).unlink()
            rows = []
            sequence = 1
            seen = set()
            secretary = rec._vpk_director_secretary_user()
            for user, position, fallback in (
                (rec.officer_id, rec.officer_position, "เจ้าหน้าที่"),
                (rec.head_officer_id, rec.head_officer_position, "หัวหน้าเจ้าหน้าที่"),
                (secretary, "", "เลขาผู้อำนวยการ"),
                (rec.signer_id, rec.signer_position, "ผู้อำนวยการ"),
            ):
                if not user or user.id in seen:
                    continue
                seen.add(user.id)
                is_check = bool(secretary and user == secretary)
                rows.append(
                    {
                        "document_id": rec.id,
                        "sequence": sequence,
                        "user_id": user.id,
                        "position": position or fallback,
                        "is_check": is_check,
                        "is_sign": not is_check,
                    }
                )
                sequence += 1
            if rows:
                Signer.with_context(vpk_skip_signer_sync=True).create(rows)
                rec._sync_signers_from_lines()

    def _seed_purchase_approval_signers(self):
        """Start from the company officer, head, and director. Rows can then be changed."""
        self.filtered(
            lambda doc: doc.document_type == "purchase_approval_memo"
        )._seed_default_approvers()

    def _sync_signers_from_lines(self):
        for rec in self:
            lines = rec.signer_line_ids.sorted(
                key=lambda line: (line.sequence, line.id)
            )
            if not lines:
                continue
            users = lines.mapped("user_id")
            officer = users[:1]
            head = users[1:2] if len(users) >= 3 else self.env["res.users"]
            signer = users[-1:] if len(users) > 1 else officer
            vals = {
                "officer_id": officer.id,
                "head_officer_id": head.id,
                "signer_id": signer.id,
            }
            if lines[:1].position:
                vals["officer_position"] = lines[0].position
            if len(lines) >= 3 and lines[1].position:
                vals["head_officer_position"] = lines[1].position
            if lines[-1:].position and len(lines) > 1:
                vals["signer_position"] = lines[-1].position
            elif len(lines) == 1 and lines.position:
                vals["signer_position"] = lines.position
            rec.with_context(skip_validation_check=True).write(vals)

    def _purchase_approval_signer_rows(self):
        self.ensure_one()
        if self.document_type == "purchase_approval_memo" and not self.signer_line_ids:
            self._seed_purchase_approval_signers()
        rows = []
        for line in self.signer_line_ids.sorted(
            key=lambda item: (item.sequence, item.id)
        ):
            if line.is_check and not line.is_sign:
                continue  # screening rows (secretary) are not printed as signers
            name = ""
            auto_position = ""
            if line.user_id:
                name, auto_position = self._person_from_user(line.user_id)
            rows.append(
                {
                    "sequence": line.sequence,
                    "name": name or "................................",
                    "position": line.position or auto_position or "",
                }
            )
        return rows

    def _vpk_definition_for_added_approvers(self):
        self.ensure_one()
        Definition = self.env["tier.definition"]
        if self.document_type:
            found = Definition.search(
                [
                    ("model", "=", self._name),
                    ("active", "=", True),
                    ("definition_domain", "ilike", self.document_type),
                ],
                limit=1,
                order="sequence, id",
            )
            if found:
                return found
        return Definition.search(
            [("model", "=", self._name), ("active", "=", True)],
            limit=1,
            order="sequence, id",
        )

    def _vpk_signing_complete(self):
        """True when every review is approved, i.e. the signing flow is already done.

        Used so a late request_validation (for example from the PR approving itself
        after the last signature) never opens a second batch of signer reviews.
        """
        self.ensure_one()
        return bool(self.review_ids) and all(
            review.status == "approved" for review in self.review_ids
        )

    def _vpk_create_reviews_from_signer_lines(self):
        """Create one review per row in the approver table."""
        Review = self.env["tier.review"]
        created = Review.browse()
        for doc in self:
            if doc.document_type == "purchase_approval_memo" and not doc.signer_line_ids:
                doc._seed_purchase_approval_signers()
            if doc.document_type == "inspection_report" and not doc.signer_line_ids:
                doc._seed_inspection_signers()
            lines = doc.signer_line_ids.filtered("user_id").sorted(
                key=lambda line: (line.sequence, line.id)
            )
            if not lines:
                if doc.document_type in ("purchase_approval_memo", "inspection_report"):
                    raise UserError(_("กรุณาเพิ่มผู้ลงนามอย่างน้อย 1 คน"))
                continue
            if doc._vpk_signing_complete() or doc.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            ):
                continue
            definition = doc._vpk_definition_for_added_approvers()
            if not definition:
                raise UserError(_("ยังไม่ได้ตั้งลำดับลงนามของเอกสารนี้"))
            # The approver table decides the whole order; no one is added automatically.
            ordered_lines = list(lines)
            vals_list = []
            for index, line in enumerate(ordered_lines, start=1):
                user = line if line._name == "res.users" else line.user_id
                name, _position = doc._person_from_user(user)
                if line._name == "res.users":
                    role = "check"
                else:
                    role = line._vpk_approval_role()
                vals_list.append(
                    {
                        "model": doc._name,
                        "res_id": doc.id,
                        "definition_id": definition.id,
                        "requested_by": self.env.uid,
                        "sequence": index,
                        "vpk_signer_user_id": user.id,
                        "vpk_signer_name": name or user.name,
                        "vpk_approval_role": role,
                    }
                )
            created |= Review.sudo().create(vals_list)
        if created:
            created._compute_reviewer_ids()
            created._compute_can_review()
        return created

    def _vpk_create_purchase_approval_sign_reviews(self):
        """Create one review per signer row, in the table order."""
        return self._vpk_create_reviews_from_signer_lines()

    def _purchase_approval_memo_values(self, refresh_intro=False):
        self.ensure_one()
        amount = self.amount_total or self._spec_amount()
        count = self._thai_digits(len(self._purchase_approval_item_lines()) or self._spec_item_count())
        intro = "" if refresh_intro else (self.body or "").strip()
        if not intro:
            department = self._request_department_name()
            subject = self.subject or "พัสดุตามรายการ"
            budget = self.budget_source or self._spec_budget_source() or "งบประมาณของหน่วยงาน"
            intro = (
                "ด้วย%s  มีความประสงค์ขออนุมัติจัดซื้อ%s  "
                "จำนวน  %s  รายการ  รวมเป็นเงินทั้งสิ้น  %s  บาท  (%s)  "
                "โดยใช้งบประมาณจาก%s  รายละเอียดดังต่อไปนี้"
                % (
                    department,
                    subject,
                    count,
                    self._format_amount_display(amount),
                    self._baht_text_display(amount),
                    budget,
                )
            )
        signers = self._purchase_approval_signer_rows()
        proposer = signers[:1]
        reviewer = signers[1:2] if len(signers) >= 3 else []
        approver = signers[-1:] if len(signers) > 1 else signers[:1]
        return {
            "agency": self.agency or self._request_department_name(),
            "memo_number": self._printed_document_number(),
            "memo_date": self._format_order_date(),
            "subject": self.subject or "",
            "recipient": self.recipient or "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต",
            "intro": intro,
            "body_2": (self.body_2 or "").strip() or self._default_purchase_approval_body_2(),
            "items": self._purchase_approval_item_lines(),
            "signers": signers,
            "proposer_name": (proposer[0]["name"] if proposer else self.officer_name) or "",
            "proposer_position": (
                proposer[0]["position"] if proposer else self.officer_position
            )
            or "",
            "reviewer_name": reviewer[0]["name"] if reviewer else "",
            "reviewer_position": reviewer[0]["position"] if reviewer else "",
            "reviewer_date": "",
            "approver_name": (approver[0]["name"] if approver else self.signer_name) or "",
            "approver_position": (
                approver[0]["position"] if approver else self.signer_position
            )
            or "",
            "approver_date": "",
        }

    def _render_docx_bytes(self):
        self.ensure_one()
        self._ensure_saraban_book_no()
        try:
            if self.document_type == "winner_announcement":
                return self._render_winner_announcement_docx()
            if self.document_type == "integrity_over_100k":
                if not (
                    self.head_officer_name or self.officer_name or self.line_ids
                ):
                    raise UserError(
                        _("กรุณาระบุหัวหน้าเจ้าหน้าที่ เจ้าหน้าที่ หรือคณะกรรมการตรวจรับอย่างน้อย 1 คน")
                    )
                return render_integrity_over_100k_docx(
                    self._get_template_bytes(),
                    self._integrity_render_values(),
                )
            if self.document_type == "inspection_report":
                return render_inspection_report_docx(
                    self._get_template_bytes(),
                    self._inspection_render_values(),
                )
            if self.document_type == "specific_method_approval":
                return render_specific_method_approval_docx(
                    self._get_template_bytes(),
                    self._specific_method_render_values(),
                )
            if self.document_type == "purchase_approval_memo":
                return render_purchase_approval_memo_docx(
                    self._get_template_bytes(),
                    self._purchase_approval_memo_values(),
                )
            if not self.line_ids:
                if self.document_type == "spec_price_committee":
                    raise UserError(
                        _("กรุณาระบุรายชื่อคณะกรรมการกำหนดคุณลักษณะอย่างน้อย 1 คน")
                    )
                raise UserError(_("กรุณาระบุรายชื่อคณะกรรมการตรวจรับอย่างน้อย 1 คน"))
            if self.document_type == "spec_price_committee":
                return render_spec_price_committee_docx(
                    self._get_template_bytes(),
                    self._spec_render_values(),
                )
            return render_wa_committee_order_docx(
                self._get_template_bytes(),
                self._render_values(),
            )
        except OfficialDocumentRenderError as error:
            raise UserError(str(error)) from error

    def _winner_egp_document(self):
        self.ensure_one()
        Egp = self.env["purchase.requisition.egp.document"]
        found = Egp.search([("official_document_id", "=", self.id)], limit=1)
        if found:
            return found
        if self.requisition_id:
            return self.requisition_id.egp_document_ids.filtered(
                lambda doc: doc.document_type_code == "winner_announcement"
            )[:1]
        return Egp

    def _render_winner_announcement_docx(self):
        self.ensure_one()
        from odoo.addons.vpk_purchase_agreement_egp.models.winner_announcement_docx import (
            WinnerAnnouncementRenderError,
            render_winner_announcement_docx,
        )

        egp = self._winner_egp_document()
        if not egp:
            raise UserError(_("ไม่พบเอกสารประกาศผู้ชนะในกระบวนการ e-GP"))
        try:
            return render_winner_announcement_docx(
                self._get_template_bytes(),
                egp._winner_announcement_values(),
            )
        except WinnerAnnouncementRenderError as error:
            raise UserError(str(error)) from error

    def _sync_winner_egp_attachment(self):
        Egp = self.env["purchase.requisition.egp.document"].sudo()
        for rec in self:
            if not rec.pdf_file:
                continue
            egp = Egp.search([("official_document_id", "=", rec.id)], limit=1)
            if not egp and rec.document_type == "winner_announcement":
                egp = rec._winner_egp_document()
            if not egp:
                continue
            vals = {
                "document_file": rec.pdf_file,
                "document_filename": rec.pdf_filename or egp.document_filename,
            }
            if rec.date and not egp.document_date:
                vals["document_date"] = rec.date
            egp.write(vals)

    def _soffice_path(self):
        path = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_official_document.soffice_path")
            or self.env["ir.config_parameter"]
            .sudo()
            .get_param("py3o.conversion_command")
            or None
        )
        return find_soffice(path)

    def _render_pdf_from_docx(self):
        self.ensure_one()
        try:
            return convert_docx_bytes_to_pdf(
                self._render_docx_bytes(),
                soffice_path=self._soffice_path(),
            )
        except PdfConversionError as error:
            raise UserError(str(error)) from error

    def action_generate_docx(self):
        self.ensure_one()
        self._ensure_saraban_book_no()
        if self.document_type == "specific_method_approval":
            section_vals = self._specific_section_vals(overwrite=False)
            if section_vals:
                self.write(section_vals)
        content = self._render_docx_bytes()
        filename = "{}.docx".format(self._output_basename())
        self._store_generated_file(
            content,
            filename,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx",
        )
        return True

    def action_generate_pdf(self):
        self.ensure_one()
        self._ensure_saraban_book_no()
        if self.document_type == "specific_method_approval":
            section_vals = self._specific_section_vals(overwrite=False)
            if section_vals:
                self.write(section_vals)
        docx_content = self._render_docx_bytes()
        self._store_generated_file(
            docx_content,
            "{}.docx".format(self._output_basename()),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx",
        )
        try:
            pdf_content = convert_docx_bytes_to_pdf(
                docx_content,
                soffice_path=self._soffice_path(),
            )
        except PdfConversionError as error:
            raise UserError(str(error)) from error
        filename = "{}.pdf".format(self._output_basename())
        self._store_generated_file(
            pdf_content,
            filename,
            "application/pdf",
            "pdf",
        )
        return True

    def action_view_pdf(self):
        self.ensure_one()
        return self.action_open_pdf_viewer()

    def action_open_pdf_viewer(self):
        self.ensure_one()
        attachment = self._get_pdf_attachment()
        if not attachment:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        can_sign = self.state == "to_approve" and bool(
            "can_review" in self._fields and self.can_review
        )
        return {
            "type": "ir.actions.client",
            "tag": "vpk_official_document_sign_pdf_viewer",
            "name": self.display_name,
            "params": {
                "attachment_id": attachment.id,
                "res_model": self._name,
                "res_id": self.id,
                "title": self.pdf_filename or self.display_name,
                "can_sign": can_sign and not self.vpk_secretary_can_screen,
                "secretary_screen": bool(self.vpk_secretary_can_screen),
            },
        }

    def action_open_sign_viewer(self):
        """Fallback when the form JS dialog is not available."""
        return self.action_open_pdf_viewer()

    def action_open_send_wizard(self):
        self.ensure_one()
        if self.state == "cancelled":
            raise UserError(_("ไม่สามารถส่งเอกสารที่ยกเลิกแล้ว"))
        if self.signature_state == "signed" or self.state == "approved":
            raise UserError(_("เอกสารนี้ลงนามแล้ว"))
        if self.signature_state == "waiting":
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว กำลังรอลงนาม"))
        return {
            "type": "ir.actions.act_window",
            "name": _("ส่งเอกสาร"),
            "res_model": "vpk.official.document.send.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_document_id": self.id},
        }

    def action_skip_approval_for_test(self):
        """Mark the document signed without the approval inbox, for flow testing."""
        now = fields.Datetime.now()
        for rec in self:
            if rec.state == "cancelled":
                raise UserError(_("ไม่สามารถส่งเอกสารที่ยกเลิกแล้ว"))
            if rec.state == "approved":
                continue
            if not rec._get_pdf_attachment():
                rec.with_context(skip_validation_check=True).action_generate_pdf()
            if not rec._get_pdf_attachment():
                raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
            pending = rec.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            if pending:
                pending.sudo().write(
                    {
                        "status": "approved",
                        "done_by": self.env.user.id,
                        "reviewed_date": now,
                    }
                )
            # skip_check_state_condition forces the tier gate and creates
            # signer reviews, which then block this test skip.
            rec.sudo().with_context(
                skip_validation_check=True,
                vpk_skip_tier_gate=True,
            ).write(
                {
                    "state": "approved",
                    "signed_on": rec.signed_on or now,
                }
            )
            rec.message_post(
                body=_(
                    "ข้ามการอนุมัติเพื่อทดสอบเดินเอกสารต่อ โดย %s"
                )
                % self.env.user.display_name
            )
            if rec.document_type == "award_approval":
                rec._approve_linked_award_report()
            if rec.document_type in (
                "wa_committee_order",
                "specific_method_approval",
            ):
                request = rec.sudo().request_id
                if request:
                    request._vpk_approve_if_packet_complete()
            if rec.request_id and "can_send_to_egp" in rec.request_id._fields:
                rec.request_id.invalidate_recordset(["can_send_to_egp"])
        return True

    def action_send_for_signature(self):
        for rec in self:
            if rec.state == "cancelled":
                raise UserError(_("ไม่สามารถส่งเอกสารที่ยกเลิกแล้ว"))
            if rec.signature_state == "signed" or rec.state == "approved":
                raise UserError(_("เอกสารนี้ลงนามแล้ว"))
            if rec.signature_state == "waiting":
                continue
            rec._vpk_check_signer_table()
            if not rec._get_pdf_attachment():
                rec.with_context(skip_validation_check=True).action_generate_pdf()
            if not rec._get_pdf_attachment():
                raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
            rec.with_context(skip_validation_check=True).write(
                {"state": "to_approve", "vpk_secretary_screen_state": False}
            )
            if rec.signer_line_ids.filtered("user_id") or (
                rec.document_type in ("purchase_approval_memo", "inspection_report")
            ):
                created = rec._vpk_create_reviews_from_signer_lines()
                if created:
                    rec._notify_review_requested(created)
                    rec._update_counter({"review_created": True})
            elif rec.document_type in (
                "specific_method_approval",
                "award_approval",
            ):
                rec._vpk_create_sequential_sign_reviews()
            elif rec.document_type == "integrity_over_100k":
                rec._vpk_create_integrity_sign_reviews()
            elif rec.document_type == "winner_announcement":
                rec._vpk_create_winner_sign_reviews()
            elif rec.document_type in COMMITTEE_ORDER_TYPES:
                rec._vpk_create_committee_sign_reviews()
            else:
                rec._vpk_request_signature_reviews()
        return True

    def _vpk_request_signature_reviews(self):
        Review = self.env["tier.review"]
        Definition = self.env["tier.definition"]
        created = Review.browse()
        for rec in self:
            if rec.state in ("approved", "cancelled"):
                continue
            if rec.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending", "approved")
            ):
                continue
            request = rec.request_id
            source = Review
            if request:
                source = request.review_ids.filtered(
                    lambda review: review.status in ("waiting", "pending", "approved")
                )
            if source:
                rec._vpk_create_reviews_from_purchase_request(source)
                continue
            vals_list = []
            sequence = 0
            eval_rec = request or rec
            model_name = "purchase.request" if request else rec._name
            definitions = Definition.search(
                [
                    ("model", "=", model_name),
                    ("company_id", "in", [False] + rec._get_company().ids),
                ],
                order="sequence desc",
            )
            for definition in definitions:
                if eval_rec.evaluate_tier(definition):
                    sequence += 1
                    vals_list.append(
                        {
                            "model": rec._name,
                            "res_id": rec.id,
                            "definition_id": definition.id,
                            "requested_by": self.env.uid,
                            "sequence": sequence,
                        }
                    )
            if vals_list:
                created |= Review.sudo().create(vals_list)
        if created:
            created._compute_can_review()
            self._notify_review_requested(created)
            self._update_counter({"review_created": True})
        return created

    def action_draft(self):
        self.mapped("review_ids").unlink()
        self.with_context(skip_validation_check=True).write({"state": "draft"})

    def action_cancel(self):
        self.with_context(skip_validation_check=True).write({"state": "cancelled"})

    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        return list(
            set(
                res
                + [
                    "state",
                    "pdf_file",
                    "pdf_filename",
                    "pdf_attachment_id",
                    "docx_file",
                    "docx_filename",
                    "docx_attachment_id",
                    "saraban_book_no",
                    "saraban_document_id",
                    "message_main_attachment_id",
                    "approver_signature",
                    "signed_on",
                    "signature_state",
                ]
            )
        )

    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        return list(
            set(
                res
                + [
                    "state",
                    "pdf_file",
                    "pdf_filename",
                    "pdf_attachment_id",
                    "approver_signature",
                    "signed_on",
                    "signature_state",
                ]
            )
        )

    def _signature_search_needles(self, signer_user=None):
        self.ensure_one()
        name = " ".join((self._signature_name_for_user(signer_user) or "").split())
        needles = []
        if name:
            if name.startswith("(") and name.endswith(")"):
                needles.append(name)
                inner = name[1:-1].strip()
                if inner:
                    needles.append(inner)
            else:
                needles.append("(%s)" % name)
                needles.append(name)
        return needles

    def _signature_name_for_user(self, signer_user=None):
        self.ensure_one()
        user = signer_user or self.env.user
        doc = self.sudo()
        pending = doc.review_ids.filtered(
            lambda review: review.status == "pending" and user in review.reviewer_ids
        )[:1]
        if pending.vpk_signer_name:
            return pending.vpk_signer_name
        if doc.officer_id and user.id == doc.officer_id.id and doc.officer_name:
            return doc.officer_name
        if doc.head_officer_id and user.id == doc.head_officer_id.id and doc.head_officer_name:
            return doc.head_officer_name
        if doc.signer_id and user.id == doc.signer_id.id and doc.signer_name:
            return doc.signer_name
        field_name = (
            pending.sudo().reviewer_field_id.name
            if pending and pending.sudo().reviewer_field_id
            else ""
        )
        if field_name == "officer_id":
            return doc.officer_name
        if field_name == "head_officer_id":
            return doc.head_officer_name
        named = doc.review_ids.filtered(
            lambda review: review.vpk_signer_name and user in review.reviewer_ids
        )[:1]
        if named.vpk_signer_name:
            return named.vpk_signer_name
        return doc.signer_name

    def _apply_signature_to_pdf(self, signature, signer_user=None, signature_box=None):
        self.ensure_one()
        signer_user = signer_user or self.env.user
        raw = signature or ""
        if isinstance(raw, bytes):
            raw = raw.decode("ascii", errors="ignore")
        if raw.startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        raw = raw.strip()
        if not raw:
            raise UserError(_("กรุณาลงลายเซ็น"))
        attachment = self._get_pdf_attachment()
        if not attachment:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        pdf_bytes = base64.b64decode(attachment.datas)
        has_egp_link = bool(
            self.env["purchase.requisition.egp.document"]
            .sudo()
            .search_count([("official_document_id", "=", self.id)])
        )
        try:
            stamped = stamp_signature_on_pdf(
                pdf_bytes,
                base64.b64decode(raw),
                self._signature_search_needles(signer_user),
                fallback_bottom_right=has_egp_link,
                custom_box=signature_box,
            )
        except SignatureStampError as error:
            raise UserError(str(error)) from error
        filename = self.pdf_filename or ("%s.pdf" % self._output_basename())
        if not filename.lower().endswith(".pdf"):
            filename = "%s.pdf" % filename
        if "-signed" not in filename.lower():
            filename = "%s-signed.pdf" % filename[:-4]
        self._store_generated_file(stamped, filename, "application/pdf", "pdf")
        vals = {"approver_signature": raw}
        if self.document_type not in (
            "specific_method_approval",
            "integrity_over_100k",
            "winner_announcement",
        ):
            vals["signed_on"] = fields.Datetime.now()
        self.write(vals)
        return True

    def action_apply_signature(self, signature, signature_box=None):
        self.ensure_one()
        if self.state != "to_approve":
            raise UserError(_("เอกสารถึงขั้นตอนลงนามแล้วเท่านั้น"))
        if "can_review" in self._fields and not self.can_review:
            self._compute_can_review()
        if "can_review" in self._fields and not self.can_review:
            raise UserError(_("คุณไม่มีสิทธิ์ลงนามเอกสารนี้"))
        self.sudo()._apply_signature_to_pdf(
            signature, signer_user=self.env.user, signature_box=signature_box
        )
        return self.validate_tier()

    def evaluate_formula_tier(self, tier):
        request = self.sudo().request_id
        if request:
            return request.evaluate_formula_tier(tier)
        return super().evaluate_formula_tier(tier)

    def _tier_validation_check_state_on_write(self, vals):
        if self.env.context.get("vpk_skip_tier_gate"):
            return
        return super()._tier_validation_check_state_on_write(vals)

    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers)
        for rec in self:
            rec.invalidate_recordset(["validation_status", "validated"])
            if rec.validation_status == "validated" and rec.state != "approved":
                rec.sudo().with_context(
                    skip_validation_check=True,
                    skip_check_state_condition=True,
                ).write(
                    {
                        "state": "approved",
                        "signed_on": rec.signed_on or fields.Datetime.now(),
                    }
                )
            if rec.validation_status == "validated":
                egp_docs = rec.env["purchase.requisition.egp.document"].sudo().search(
                    [("official_document_id", "=", rec.id)]
                )
                if egp_docs:
                    egp_docs.mapped("requisition_id").invalidate_recordset(
                        ["egp_award_approved"]
                    )
            if (
                rec.document_type == "award_approval"
                and rec.validation_status == "validated"
            ):
                rec._approve_linked_award_report()
            if rec.document_type in (
                "wa_committee_order",
                "specific_method_approval",
            ):
                request = rec.sudo().request_id
                if request:
                    request._vpk_approve_if_packet_complete()
            if rec.request_id and "can_send_to_egp" in rec.request_id._fields:
                rec.request_id.invalidate_recordset(["can_send_to_egp"])
        return res

    def _rejected_tier(self, tiers=False):
        res = super()._rejected_tier(tiers)
        secretary = self._vpk_director_secretary_user()
        returned = self.browse()
        if secretary:
            for rec in self.filtered(lambda doc: doc.state == "to_approve"):
                secretary_rejected = rec.review_ids.filtered(
                    lambda review: review.status == "rejected"
                    and secretary in review.reviewer_ids
                )
                if not secretary_rejected:
                    continue
                partners = rec.review_ids.mapped("requested_by.partner_id")
                rec.review_ids.sudo().unlink()
                rec.sudo().with_context(skip_validation_check=True).write(
                    {"state": "generated", "vpk_secretary_screen_state": False}
                )
                rec.sudo().message_post(
                    body=_(
                        "เลขาผู้อำนวยการตีกลับเอกสารให้ผู้จัดทำแก้ไข "
                        "แล้วส่งขออนุมัติใหม่"
                    ),
                    partner_ids=partners.ids,
                )
                returned |= rec
        if self.env.context.get("vpk_skip_pr_reject_from_packet"):
            return res
        for rec in self - returned:
            if rec.document_type not in (
                "wa_committee_order",
                "specific_method_approval",
            ):
                continue
            request = rec.sudo().request_id
            if request and request.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            ):
                request.with_context(
                    vpk_skip_pr_reject_from_packet=True
                ).reject_tier()
        return res

    def _vpk_check_signer_table(self):
        """Every document needs at least one row in the approver table before it is sent."""
        for rec in self:
            if rec.document_type == "purchase_approval_memo":
                rec._seed_purchase_approval_signers()
            elif rec.document_type == "inspection_report":
                rec._seed_inspection_signers()
            if not rec.signer_line_ids.filtered("user_id"):
                raise UserError(
                    _(
                        'กรุณาเพิ่มผู้อนุมัติในตาราง "ผู้อนุมัติ" ของเอกสาร %s '
                        "อย่างน้อย 1 คนก่อนส่งอนุมัติ"
                    )
                    % (rec.name or rec.display_name)
                )

    def request_validation(self):
        self._vpk_check_signer_table()
        with_signers = self.filtered(
            lambda doc: doc.signer_line_ids.filtered("user_id")
            or doc.document_type in ("purchase_approval_memo", "inspection_report")
        )
        created = with_signers._vpk_create_reviews_from_signer_lines()
        if created:
            with_signers._notify_review_requested(created)
            with_signers._update_counter({"review_created": True})
        rest = self - with_signers
        approval = rest.filtered(
            lambda doc: doc.document_type == "specific_method_approval"
        )
        integrity = rest.filtered(
            lambda doc: doc.document_type == "integrity_over_100k"
        )
        winners = rest.filtered(
            lambda doc: doc.document_type == "winner_announcement"
        )
        awards = rest.filtered(lambda doc: doc.document_type == "award_approval")
        committees = rest.filtered(
            lambda doc: doc.document_type in COMMITTEE_ORDER_TYPES
        )
        others = rest - approval - integrity - winners - awards - committees
        if others:
            created |= super(OfficialDocument, others).request_validation()
        if approval:
            created |= approval._vpk_create_sequential_sign_reviews()
        if integrity:
            created |= integrity._vpk_create_integrity_sign_reviews()
        if winners:
            created |= winners._vpk_create_winner_sign_reviews()
        if awards:
            created |= awards._vpk_create_sequential_sign_reviews()
        if committees:
            created |= committees._vpk_create_committee_sign_reviews()
        return created

    def _approve_linked_award_report(self):
        Report = self.env["purchase.requisition.award.report"].sudo()
        Document = self.env["purchase.requisition.egp.document"].sudo()
        for rec in self:
            egp = Document.search(
                [("official_document_id", "=", rec.id)],
                limit=1,
            )
            report = egp.award_report_id if egp else Report
            if not report and rec.requisition_id:
                report = rec.requisition_id.award_report_ids.filtered(
                    lambda item: item.state != "cancelled"
                )[:1]
            if report and report.state not in ("approved", "cancelled"):
                report.sudo().action_approve()

    def action_secretary_mark_checked(self):
        """Secretary marks the document reviewed before it can go to the director."""
        for rec in self:
            if not rec.vpk_secretary_can_screen:
                raise UserError(_("เฉพาะเลขาผู้อำนวยการที่กำลังกลั่นกรองเอกสารนี้"))
            if rec.vpk_secretary_screen_state == "checked":
                continue
            rec.sudo().with_context(skip_validation_check=True).write(
                {"vpk_secretary_screen_state": "checked"}
            )
            rec.sudo().message_post(body=_("เลขาผู้อำนวยการตรวจสอบเอกสารแล้ว"))
        return True

    def action_secretary_send_director(self):
        """Forward a reviewed document to the director."""
        for rec in self:
            if not rec.vpk_secretary_can_screen:
                raise UserError(_("เฉพาะเลขาผู้อำนวยการที่กำลังกลั่นกรองเอกสารนี้"))
            if rec.vpk_secretary_screen_state != "checked":
                raise UserError(_("กรุณากดตรวจสอบแล้ว ก่อนส่งผู้อำนวยการ"))
        return self.validate_tier()

    def _vpk_director_secretary_user(self):
        return self.env.ref(
            "vpk_tier_validation.user_director_secretary",
            raise_if_not_found=False,
        )

    def _vpk_insert_secretary_before_director(self):
        """Put the secretary ahead of a director step that was opened without one."""
        secretary = self._vpk_director_secretary_user()
        if not secretary:
            return self.env["tier.review"]
        Review = self.env["tier.review"].sudo()
        created = Review.browse()
        for doc in self.filtered(lambda item: item.state == "to_approve" and item.signer_id):
            if doc.signer_id == secretary:
                continue
            reviews = doc.review_ids
            if reviews.filtered(
                lambda review: review.vpk_signer_user_id == secretary
                or secretary in review.reviewer_ids
            ):
                continue
            director_review = reviews.filtered(
                lambda review: review.status in ("pending", "waiting")
                and (
                    review.vpk_signer_user_id == doc.signer_id
                    or doc.signer_id in review.reviewer_ids
                )
            ).sorted("sequence")[:1]
            if not director_review:
                continue
            slot = director_review.sequence or 1
            later = reviews.filtered(lambda review: (review.sequence or 0) >= slot)
            for review in later.sorted(key=lambda item: item.sequence or 0, reverse=True):
                vals = {"sequence": (review.sequence or 0) + 1}
                if review == director_review:
                    vals.update({"status": "waiting", "can_review": False})
                review.with_context(
                    tier_validation_defer_compute_can_review=True
                ).write(vals)
            name, _position = doc._person_from_user(secretary)
            created |= Review.with_context(
                tier_validation_defer_compute_can_review=True
            ).create(
                {
                    "model": doc._name,
                    "res_id": doc.id,
                    "definition_id": director_review.definition_id.id,
                    "requested_by": director_review.requested_by.id or self.env.uid,
                    "sequence": slot,
                    "status": "waiting",
                    "vpk_signer_user_id": secretary.id,
                    "vpk_signer_name": name or secretary.name,
                }
            )
            open_reviews = doc.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            open_reviews._compute_reviewer_ids()
            open_reviews._compute_can_review()
        return created

    def _vpk_sequential_sign_definitions(self, document_type=None):
        if document_type == "award_approval":
            xmlids = (
                "vpk_official_document.tier_definition_award_approval_officer",
                "vpk_official_document.tier_definition_award_approval_head_officer",
                "vpk_official_document.tier_definition_award_approval_secretary",
                "vpk_official_document.tier_definition_award_approval_director",
            )
            domain_hint = "award_approval"
        elif document_type == "purchase_approval_memo":
            xmlids = (
                "vpk_official_document.tier_definition_purchase_approval_officer",
                "vpk_official_document.tier_definition_purchase_approval_head_officer",
                "vpk_official_document.tier_definition_purchase_approval_secretary",
                "vpk_official_document.tier_definition_purchase_approval_director",
            )
            domain_hint = "purchase_approval_memo"
        else:
            xmlids = (
                "vpk_official_document.tier_definition_specific_method_officer",
                "vpk_official_document.tier_definition_specific_method_head_officer",
                "vpk_official_document.tier_definition_specific_method_secretary",
                "vpk_official_document.tier_definition_specific_method_director",
            )
            domain_hint = "specific_method_approval"
        definitions = self.env["tier.definition"]
        for xmlid in xmlids:
            definition = self.env.ref(xmlid, raise_if_not_found=False)
            if definition:
                definitions |= definition
        if len(definitions) == len(xmlids):
            return definitions
        return self.env["tier.definition"].search(
            [
                ("model", "=", self._name),
                ("review_type", "=", "field"),
                ("approve_sequence", "=", True),
                (
                    "definition_domain",
                    "ilike",
                    domain_hint,
                ),
            ],
            order="sequence",
        )

    def _vpk_ensure_sequential_signers(self):
        self.ensure_one()
        company = self.company_id
        vals = {}
        if not self.officer_id:
            officer = self._person_user_from_company(
                company, "official_doc_officer_id", "official_doc_officer_name"
            )
            if officer:
                vals["officer_id"] = officer.id
        if not self.head_officer_id:
            head = self._person_user_from_company(
                company,
                "official_doc_head_officer_id",
                "official_doc_head_officer_name",
            )
            if head:
                vals["head_officer_id"] = head.id
        if not self.signer_id:
            signer = self._person_user_from_company(
                company, "official_doc_signer_id", "official_doc_signer_name"
            )
            if signer:
                vals["signer_id"] = signer.id
        if vals:
            self.with_context(skip_validation_check=True).write(vals)
        missing = []
        if not self.officer_id:
            missing.append(_("เจ้าหน้าที่"))
        if not self.head_officer_id:
            missing.append(_("หัวหน้าเจ้าหน้าที่"))
        if not self.signer_id:
            missing.append(_("ผู้อำนวยการ"))
        if missing:
            raise UserError(
                _("กรุณาระบุ %s ในเอกสาร") % "  ".join(missing)
            )
        return True

    def _vpk_create_sequential_sign_reviews(self):
        """Create officer → head officer → secretary → director reviews in order."""
        Review = self.env["tier.review"]
        created = Review.browse()
        for doc in self:
            if doc.document_type not in (
                "specific_method_approval",
                "purchase_approval_memo",
                "award_approval",
            ):
                continue
            if doc._vpk_signing_complete() or doc.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            ):
                continue
            if doc.document_type == "purchase_approval_memo" or doc.signer_line_ids.filtered(
                "user_id"
            ):
                created |= doc._vpk_create_reviews_from_signer_lines()
                continue
            doc._vpk_ensure_sequential_signers()
            definitions = doc._vpk_sequential_sign_definitions(doc.document_type)
            if len(definitions) < 3:  # officer, head, and director are required
                raise UserError(
                    _("ยังไม่ได้ตั้งลำดับลงนามของเอกสารนี้")
                )
            vals_list = []
            sequence = 0
            for definition in definitions.sorted("sequence"):
                sequence += 1
                vals_list.append(
                    {
                        "model": doc._name,
                        "res_id": doc.id,
                        "definition_id": definition.id,
                        "requested_by": self.env.uid,
                        "sequence": sequence,
                    }
                )
            created |= Review.sudo().create(vals_list)
        if created:
            created._compute_reviewer_ids()
            created._compute_can_review()
            self._notify_review_requested(created)
            self._update_counter({"review_created": True})
        return created

    def _vpk_ensure_winner_signers(self):
        self.ensure_one()
        vals = {}
        if not self.officer_id:
            vals["officer_id"] = self.env.user.id
        if not self.signer_id:
            signer = self._person_user_from_company(
                self.company_id, "official_doc_signer_id", "official_doc_signer_name"
            )
            if signer:
                vals["signer_id"] = signer.id
        if vals:
            self.with_context(skip_validation_check=True).write(vals)
        if not self.signer_id:
            raise UserError(_("กรุณาระบุผู้อำนวยการก่อนส่งประกาศผู้ชนะลงนาม"))
        return True

    @api.model
    def _vpk_ensure_winner_tier_definitions(self):
        """Winner announcement is screened by the secretary, then signed by the director."""
        signer_field = self.env.ref(
            "vpk_official_document.field_vpk_official_document__signer_id",
            raise_if_not_found=False,
        )
        generator = self.env.ref(
            "vpk_official_document.tier_definition_winner_announcement_generator",
            raise_if_not_found=False,
        )
        secretary_def = self.env.ref(
            "vpk_official_document.tier_definition_winner_announcement_secretary",
            raise_if_not_found=False,
        )
        director = self.env.ref(
            "vpk_official_document.tier_definition_winner_announcement_director",
            raise_if_not_found=False,
        )
        if generator and generator.active:
            generator.sudo().write({"active": False})
        secretary_user = self._vpk_director_secretary_user()
        if secretary_def and secretary_user:
            vals = {}
            if secretary_def.review_type != "individual":
                vals["review_type"] = "individual"
            if secretary_def.reviewer_id != secretary_user:
                vals["reviewer_id"] = secretary_user.id
            if secretary_def.sequence != 10:
                vals["sequence"] = 10
            if not secretary_def.approve_sequence:
                vals["approve_sequence"] = True
            if not secretary_def.active:
                vals["active"] = True
            if vals:
                secretary_def.sudo().write(vals)
        if director and signer_field:
            vals = {}
            if director.reviewer_field_id != signer_field:
                vals["reviewer_field_id"] = signer_field.id
            if director.sequence != 20:
                vals["sequence"] = 20
            if director.review_type != "field":
                vals["review_type"] = "field"
            if not director.approve_sequence:
                vals["approve_sequence"] = True
            if not director.active:
                vals["active"] = True
            if vals:
                director.sudo().write(vals)
        return True

    def _vpk_winner_sign_definitions(self):
        self._vpk_ensure_winner_tier_definitions()
        secretary_def = self.env.ref(
            "vpk_official_document.tier_definition_winner_announcement_secretary",
            raise_if_not_found=False,
        )
        director = self.env.ref(
            "vpk_official_document.tier_definition_winner_announcement_director",
            raise_if_not_found=False,
        )
        definitions = self.env["tier.definition"]
        if secretary_def and secretary_def.active:
            definitions |= secretary_def
        if director and director.active:
            definitions |= director
        if definitions:
            return list(definitions.sorted("sequence"))
        found = self.env["tier.definition"].search(
            [
                ("model", "=", self._name),
                ("review_type", "=", "field"),
                ("reviewer_field_id.name", "=", "signer_id"),
                ("definition_domain", "ilike", "winner_announcement"),
                ("active", "=", True),
            ],
            order="sequence, id",
            limit=1,
        )
        return list(found)

    def _vpk_create_winner_sign_reviews(self):
        """Create secretary then director reviews for winner announcement."""
        Review = self.env["tier.review"]
        created = Review.browse()
        definitions = self._vpk_winner_sign_definitions()
        if not definitions:
            raise UserError(_("ยังไม่ได้ตั้งลำดับลงนามของประกาศผู้ชนะ"))
        for doc in self:
            if doc.document_type != "winner_announcement":
                continue
            if doc._vpk_signing_complete() or doc.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            ):
                continue
            doc._vpk_ensure_winner_signers()
            vals_list = []
            sequence = 0
            for definition in definitions:
                sequence += 1
                vals_list.append(
                    {
                        "model": doc._name,
                        "res_id": doc.id,
                        "definition_id": definition.id,
                        "requested_by": self.env.uid,
                        "sequence": sequence,
                    }
                )
            created |= Review.sudo().create(vals_list)
        if created:
            created._compute_reviewer_ids()
            created._compute_can_review()
            self._notify_review_requested(created)
            self._update_counter({"review_created": True})
        return created

    def _vpk_committee_sign_definition(self):
        definition = self.env.ref(
            "vpk_official_document.tier_definition_committee_order_director",
            raise_if_not_found=False,
        )
        if definition and not definition.active:
            definition.sudo().write({"active": True})
        return definition

    def _vpk_create_committee_sign_reviews(self):
        """Committee orders and requests are signed once, by the director.

        Without this the generic path copies the PR amount tiers, so the same
        director has to approve the document once per tier (>30,000, >100,000).
        """
        Review = self.env["tier.review"]
        created = Review.browse()
        definition = self._vpk_committee_sign_definition()
        if not definition:
            raise UserError(_("ยังไม่ได้ตั้งลำดับลงนามของเอกสารแต่งตั้งคณะกรรมการ"))
        for doc in self:
            if doc.document_type not in COMMITTEE_ORDER_TYPES:
                continue
            if doc._vpk_signing_complete() or doc.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            ):
                continue
            if not doc.signer_id:
                signer = doc._person_user_from_company(
                    doc.company_id,
                    "official_doc_signer_id",
                    "official_doc_signer_name",
                )
                if signer:
                    doc.with_context(skip_validation_check=True).write(
                        {"signer_id": signer.id}
                    )
            if not doc.signer_id:
                raise UserError(_("กรุณาระบุผู้อำนวยการก่อนส่งเอกสารลงนาม"))
            created |= Review.sudo().create(
                {
                    "model": doc._name,
                    "res_id": doc.id,
                    "definition_id": definition.id,
                    "requested_by": self.env.uid,
                    "sequence": 1,
                }
            )
        if created:
            created._compute_reviewer_ids()
            created._compute_can_review()
            self._notify_review_requested(created)
            self._update_counter({"review_created": True})
        return created

    def _vpk_integrity_sign_definitions(self):
        xmlids = (
            "vpk_official_document.tier_definition_integrity_officer",
            "vpk_official_document.tier_definition_integrity_head_officer",
            "vpk_official_document.tier_definition_integrity_committee",
        )
        definitions = self.env["tier.definition"]
        for xmlid in xmlids:
            definition = self.env.ref(xmlid, raise_if_not_found=False)
            if definition:
                definitions |= definition
        if len(definitions) == 3:
            return definitions
        return self.env["tier.definition"].search(
            [
                ("model", "=", self._name),
                ("approve_sequence", "=", True),
                (
                    "definition_domain",
                    "ilike",
                    "integrity_over_100k",
                ),
            ],
            order="sequence",
        )

    def _vpk_ensure_integrity_signers(self):
        self.ensure_one()
        company = self.company_id
        vals = {}
        if not self.officer_id:
            officer = self._person_user_from_company(
                company, "official_doc_officer_id", "official_doc_officer_name"
            )
            if officer:
                vals["officer_id"] = officer.id
        if not self.head_officer_id:
            head = self._person_user_from_company(
                company,
                "official_doc_head_officer_id",
                "official_doc_head_officer_name",
            )
            if head:
                vals["head_officer_id"] = head.id
        if vals:
            self.with_context(skip_validation_check=True).write(vals)
        missing = []
        if not self.officer_id:
            missing.append(_("เจ้าหน้าที่"))
        if not self.head_officer_id:
            missing.append(_("หัวหน้าเจ้าหน้าที่"))
        if missing:
            raise UserError(
                _("กรุณาระบุ %s ในแบบแสดงความบริสุทธิ์ใจ") % "  ".join(missing)
            )
        if not self.line_ids:
            raise UserError(
                _("กรุณาดึงรายชื่อคณะกรรมการในแบบแสดงความบริสุทธิ์ใจ")
            )
        return True

    def _vpk_integrity_committee_lines(self):
        self.ensure_one()
        return self.line_ids.sorted(
            key=lambda line: (
                0 if line.role == "chairman" else 1,
                line.sequence,
                line.id,
            )
        )

    def _vpk_line_signer_user(self, line):
        if line.user_id:
            return line.user_id
        if line.employee_id and line.employee_id.user_id:
            return line.employee_id.user_id
        return self._user_by_person_name(line.name)

    def _vpk_integrity_sign_steps(self):
        """Officer → head officer → committee lines in document order."""
        self.ensure_one()
        steps = []
        seen = set()

        def add_step(kind, user, name, line=False):
            if not user or user.id in seen:
                return
            seen.add(user.id)
            steps.append(
                {
                    "kind": kind,
                    "user": user,
                    "name": " ".join((name or user.name or "").split()),
                    "line": line,
                }
            )

        add_step(
            "officer",
            self.officer_id,
            self.officer_name or self.officer_id.name,
        )
        add_step(
            "head",
            self.head_officer_id,
            self.head_officer_name or self.head_officer_id.name,
        )
        missing = []
        for line in self._vpk_integrity_committee_lines():
            user = self._vpk_line_signer_user(line)
            if not user:
                missing.append(line.name)
                continue
            if not line.user_id:
                line.write({"user_id": user.id})
            add_step("committee", user, line.name, line)
        if missing:
            raise UserError(
                _("ไม่พบผู้ใช้งานของกรรมการ: %s") % ", ".join(missing)
            )
        committee_steps = [step for step in steps if step["kind"] == "committee"]
        if not committee_steps:
            raise UserError(
                _("กรุณาดึงรายชื่อคณะกรรมการในแบบแสดงความบริสุทธิ์ใจ")
            )
        return steps

    def _vpk_create_integrity_sign_reviews(self):
        """Create officer → head officer → committee reviews in order."""
        Review = self.env["tier.review"]
        created = Review.browse()
        definitions = self._vpk_integrity_sign_definitions()
        if len(definitions) < 3:
            raise UserError(
                _("ยังไม่ได้ตั้งลำดับลงนามของแบบแสดงความบริสุทธิ์ใจ")
            )
        officer_def = definitions.sorted("sequence")[0]
        head_def = definitions.sorted("sequence")[1]
        committee_def = definitions.sorted("sequence")[2]
        named = {
            "officer": self.env.ref(
                "vpk_official_document.tier_definition_integrity_officer",
                raise_if_not_found=False,
            )
            or officer_def,
            "head": self.env.ref(
                "vpk_official_document.tier_definition_integrity_head_officer",
                raise_if_not_found=False,
            )
            or head_def,
            "committee": self.env.ref(
                "vpk_official_document.tier_definition_integrity_committee",
                raise_if_not_found=False,
            )
            or committee_def,
        }
        for doc in self:
            if doc.document_type != "integrity_over_100k":
                continue
            if doc._vpk_signing_complete() or doc.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            ):
                continue
            doc._vpk_ensure_integrity_signers()
            steps = doc._vpk_integrity_sign_steps()
            vals_list = []
            sequence = 0
            for step in steps:
                sequence += 1
                definition = named[step["kind"]]
                vals = {
                    "model": doc._name,
                    "res_id": doc.id,
                    "definition_id": definition.id,
                    "requested_by": self.env.uid,
                    "sequence": sequence,
                    "vpk_signer_user_id": step["user"].id,
                    "vpk_signer_name": step["name"],
                }
                if step["line"]:
                    vals["vpk_signer_line_id"] = step["line"].id
                vals_list.append(vals)
            created |= Review.sudo().create(vals_list)
        if created:
            created._compute_reviewer_ids()
            created._compute_can_review()
            self._notify_review_requested(created)
            self._update_counter({"review_created": True})
        return created

    def _vpk_create_reviews_from_purchase_request(self, pr_reviews):
        """Clone PR reviews onto committee orders; approval/integrity use sequential signers."""
        Review = self.env["tier.review"]
        committee_created = Review.browse()
        sequential_types = (
            "specific_method_approval",
            "purchase_approval_memo",
            "integrity_over_100k",
        ) + COMMITTEE_ORDER_TYPES
        committee = self.filtered(
            lambda doc: doc.document_type not in sequential_types
        )
        committee_orders = self.filtered(
            lambda doc: doc.document_type in COMMITTEE_ORDER_TYPES
        )
        approval = self.filtered(
            lambda doc: doc.document_type
            in ("specific_method_approval", "purchase_approval_memo")
        )
        integrity = self.filtered(
            lambda doc: doc.document_type == "integrity_over_100k"
        )
        for doc in committee:
            if doc.state in ("approved", "cancelled"):
                continue
            if doc.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending", "approved")
            ):
                continue
            request = doc.request_id
            source = pr_reviews.filtered(
                lambda review, req=request: (
                    review.model == "purchase.request" and review.res_id == req.id
                )
            )
            if not source and request:
                source = request.review_ids.filtered(
                    lambda review: review.status in ("waiting", "pending", "approved")
                )
            for review in source:
                committee_created |= Review.sudo().create(
                    {
                        "model": doc._name,
                        "res_id": doc.id,
                        "definition_id": review.definition_id.id,
                        "requested_by": review.requested_by.id,
                        "sequence": review.sequence,
                    }
                )
        sequential_created = Review.browse()
        if approval:
            sequential_created |= approval._vpk_create_sequential_sign_reviews()
        if integrity:
            sequential_created |= integrity._vpk_create_integrity_sign_reviews()
        if committee_orders:
            sequential_created |= committee_orders._vpk_create_committee_sign_reviews()
        if committee_created:
            committee_created._compute_can_review()
            committee._notify_review_requested(committee_created)
            self._update_counter({"review_created": True})
        return committee_created | sequential_created


class OfficialDocumentSigner(models.Model):
    _name = "vpk.official.document.signer"
    _description = "ผู้ลงนามหนังสือราชการ"
    _order = "sequence, id"

    document_id = fields.Many2one(
        comodel_name="vpk.official.document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="ลำดับอนุมัติ", default=1)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ชื่อ",
        ondelete="restrict",
        domain=[("share", "=", False)],
    )
    position = fields.Char(string="ตำแหน่ง")
    is_check = fields.Boolean(string="ตรวจสอบ")
    is_sign = fields.Boolean(string="ลงนาม", default=True)
    company_id = fields.Many2one(related="document_id.company_id", store=True)

    def _is_director_secretary(self, user):
        secretary = self.env.ref(
            "vpk_tier_validation.user_director_secretary",
            raise_if_not_found=False,
        )
        return bool(secretary and user == secretary)

    def _vpk_approval_role(self):
        self.ensure_one()
        if self.is_check and not self.is_sign:
            return "check"
        return "sign"

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if not self.user_id:
            return
        _name, position = self.env["vpk.official.document"]._person_from_user(
            self.user_id
        )
        if position:
            self.position = position
        if self._is_director_secretary(self.user_id):
            self.is_check = True
            self.is_sign = False
        elif not self.is_check:
            self.is_sign = True

    @api.onchange("is_check")
    def _onchange_is_check(self):
        if self.is_check:
            self.is_sign = False

    @api.onchange("is_sign")
    def _onchange_is_sign(self):
        if self.is_sign:
            self.is_check = False

    @api.model_create_multi
    def create(self, vals_list):
        Document = self.env["vpk.official.document"]
        for vals in vals_list:
            if vals.get("user_id") and not vals.get("position"):
                user = self.env["res.users"].browse(vals["user_id"])
                _name, position = Document._person_from_user(user)
                if position:
                    vals["position"] = position
            if vals.get("is_check") and vals.get("is_sign"):
                vals["is_sign"] = False
            elif "is_check" not in vals and "is_sign" not in vals:
                user = self.env["res.users"].browse(vals.get("user_id"))
                if user and self._is_director_secretary(user):
                    vals["is_check"] = True
                    vals["is_sign"] = False
                else:
                    vals["is_sign"] = True
            if not vals.get("sequence") and vals.get("document_id"):
                siblings = self.search([("document_id", "=", vals["document_id"])])
                vals["sequence"] = max(siblings.mapped("sequence") or [0]) + 1
        records = super().create(vals_list)
        if not self.env.context.get("vpk_skip_signer_sync"):
            records.mapped("document_id")._sync_signers_from_lines()
        return records

    def write(self, vals):
        if vals.get("user_id") and "position" not in vals:
            user = self.env["res.users"].browse(vals["user_id"])
            _name, position = self.env["vpk.official.document"]._person_from_user(
                user
            )
            if position:
                vals = dict(vals, position=position)
        result = super().write(vals)
        if not self.env.context.get("vpk_skip_signer_sync"):
            self.mapped("document_id")._sync_signers_from_lines()
        return result

    def unlink(self):
        documents = self.mapped("document_id")
        result = super().unlink()
        documents._sync_signers_from_lines()
        return result


class OfficialDocumentLine(models.Model):
    _name = "vpk.official.document.line"
    _description = "รายชื่อในหนังสือราชการ"
    _order = "sequence, id"

    document_id = fields.Many2one(
        comodel_name="vpk.official.document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="พนักงาน",
        ondelete="restrict",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ใช้งาน",
        ondelete="set null",
    )
    name = fields.Char(string="ชื่อ-สกุล", required=True)
    position = fields.Char(string="ตำแหน่ง")
    role = fields.Selection(
        selection=[
            ("chairman", "ประธานกรรมการ"),
            ("committee", "กรรมการ"),
            ("secretary", "กรรมการและเลขานุการ"),
        ],
        string="บทบาท",
        required=True,
        default="committee",
    )
    note = fields.Char(string="หมายเหตุ")
    company_id = fields.Many2one(related="document_id.company_id", store=True)

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if not self.employee_id:
            return
        self.name = self.employee_id.name
        self.position = (
            self.employee_id.job_title
            or (self.employee_id.job_id.name if self.employee_id.job_id else "")
        )
        self.user_id = self.employee_id.user_id

    @api.model_create_multi
    def create(self, vals_list):
        Employee = self.env["hr.employee"]
        for vals in vals_list:
            if vals.get("employee_id") and not vals.get("user_id"):
                employee = Employee.browse(vals["employee_id"])
                if employee.user_id:
                    vals["user_id"] = employee.user_id.id
        return super().create(vals_list)
