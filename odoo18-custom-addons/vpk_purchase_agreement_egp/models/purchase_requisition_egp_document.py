# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import logging
import mimetypes

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .winner_announcement_docx import (
    WinnerAnnouncementRenderError,
    load_template_bytes,
    render_winner_announcement_docx,
)

_logger = logging.getLogger(__name__)
_THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")


class PurchaseRequisitionEgpDocumentType(models.Model):
    _name = "purchase.requisition.egp.document.type"
    _description = "e-GP Document Type"
    _order = "sequence, id"

    name = fields.Char(string="Title", required=True, translate=True)
    code = fields.Char(string="Code", required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class PurchaseRequisitionEgpDocument(models.Model):
    _name = "purchase.requisition.egp.document"
    _description = "Purchase Agreement e-GP Document"
    _order = "sequence, id"

    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="Purchase Agreement",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    document_type_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.document.type",
        string="Title",
        required=True,
        ondelete="restrict",
        index=True,
    )
    egp_reference = fields.Char(string="e-GP Reference")
    document_date = fields.Date(string="Document Date")
    notes = fields.Text(string="Notes")
    document_file = fields.Binary(string="PDF File", attachment=True)
    document_filename = fields.Char(string="Filename")
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        related="requisition_id.company_id",
        store=True,
    )
    document_type_code = fields.Char(
        related="document_type_id.code",
        string="Document Type Code",
        store=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        requisition_id = self.env.context.get("default_requisition_id")
        if not res.get("egp_reference"):
            egp_reference = self.env.context.get("default_egp_reference")
            if not egp_reference and requisition_id:
                egp_reference = self.env["purchase.requisition"].browse(requisition_id).egp_reference
            if egp_reference:
                res["egp_reference"] = egp_reference
        return res

    @api.onchange("document_type_id", "requisition_id")
    def _onchange_document_type_id(self):
        if self.requisition_id.egp_reference:
            self.egp_reference = self.requisition_id.egp_reference

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("sequence") and vals.get("requisition_id"):
                max_sequence = max(
                    self.search(
                        [("requisition_id", "=", vals["requisition_id"])],
                        order="sequence desc",
                        limit=1,
                    ).mapped("sequence") or [0]
                )
                vals["sequence"] = max_sequence + 10
            if vals.get("egp_reference") or not vals.get("requisition_id"):
                continue
            requisition = self.env["purchase.requisition"].browse(vals["requisition_id"])
            if requisition.egp_reference:
                vals["egp_reference"] = requisition.egp_reference
        records = super().create(vals_list)
        records._sync_attachment()
        records._update_requisition_egp_reference()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"document_file", "document_filename", "document_type_id"}.intersection(vals):
            self._sync_attachment()
        if {"egp_reference", "document_type_id"}.intersection(vals):
            self._update_requisition_egp_reference()
        return res

    def unlink(self):
        requisitions = self.mapped("requisition_id")
        res = super().unlink()
        requisitions._update_egp_reference_from_documents()
        return res

    def _sync_attachment(self):
        attachment_obj = self.env["ir.attachment"]
        for record in self:
            if not record.document_file:
                if record.attachment_id:
                    record.attachment_id.unlink()
                    record.attachment_id = False
                continue
            filename = (
                record.document_filename
                or record.document_type_id.name
                or "e-GP Document.pdf"
            )
            mimetype = self._mimetype_for_filename(filename)
            attachment_vals = {
                "name": filename,
                "type": "binary",
                "datas": record.document_file,
                "res_model": record._name,
                "res_id": record.id,
                "mimetype": mimetype,
            }
            if record.attachment_id:
                record.attachment_id.write(attachment_vals)
            else:
                record.attachment_id = attachment_obj.create(attachment_vals)

    def _update_requisition_egp_reference(self):
        self.mapped("requisition_id")._update_egp_reference_from_documents()

    def action_preview_document(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(
                _("กรุณากด Gen เพื่อสร้างเอกสาร หรือแนบไฟล์ก่อนเปิดดู")
            )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=false" % self.attachment_id.id,
            "target": "new",
        }

    def action_generate_winner_document(self):
        self.ensure_one()
        if self.document_type_id.code != "winner_announcement":
            raise UserError(_("ปุ่มนี้ใช้สร้างเอกสารประกาศผู้ชนะเท่านั้น"))
        try:
            docx_content = render_winner_announcement_docx(
                load_template_bytes(),
                self._winner_announcement_values(),
            )
        except WinnerAnnouncementRenderError as error:
            raise UserError(str(error)) from error
        basename = "ประกาศผู้ชนะ-%s" % (
            self.egp_reference or self.requisition_id.name or self.id
        )
        pdf_content = self._convert_winner_docx_to_pdf(docx_content)
        if pdf_content:
            self.write(
                {
                    "document_file": base64.b64encode(pdf_content),
                    "document_filename": "%s.pdf" % basename,
                    "document_date": self.document_date or fields.Date.context_today(self),
                }
            )
        else:
            self.write(
                {
                    "document_file": base64.b64encode(docx_content),
                    "document_filename": "%s.docx" % basename,
                    "document_date": self.document_date or fields.Date.context_today(self),
                }
            )
        return True

    def _convert_winner_docx_to_pdf(self, docx_content):
        try:
            from odoo.addons.vpk_official_document.models.pdf_converter import (
                PdfConversionError,
                convert_docx_bytes_to_pdf,
            )
        except ImportError:
            _logger.info(
                "vpk_official_document is not installed; storing winner announcement as Word"
            )
            return False
        try:
            return convert_docx_bytes_to_pdf(docx_content)
        except PdfConversionError as error:
            _logger.warning("Could not convert winner announcement to PDF: %s", error)
            return False

    def _winner_announcement_values(self):
        self.ensure_one()
        requisition = self.requisition_id
        winner = requisition._get_egp_winner_bid()
        announcement = requisition.winner_announcement_ids[:1]
        if not winner and not announcement.winner_partner_id and not requisition.vendor_id:
            raise UserError(
                _("กรุณาเลือกผู้ชนะในแท็บเปรียบเทียบราคาก่อนสร้างประกาศผู้ชนะ")
            )
        partner = (
            winner.partner_id
            or announcement.winner_partner_id
            or requisition.vendor_id
        )
        amount = (
            winner.amount_total
            or announcement.winner_amount
            or requisition.purchase_request_amount_total
            or 0.0
        )
        announce_date = (
            self.document_date
            or announcement.date
            or fields.Date.context_today(self)
        )
        company = requisition.company_id
        province = self._winner_province(company)
        item_text, item_count = self._winner_item_text(requisition)
        project = requisition.egp_project_name or item_text
        method = self._winner_method_phrase(requisition)
        egp_ref = self.egp_reference or requisition.egp_reference or requisition.name
        thai = self._thai_digits
        subject = _(
            "ประกาศผู้ชนะการเสนอราคา %(project)s จำนวน %(count)s รายการ (%(ref)s) %(method)s"
        ) % {
            "project": project,
            "count": thai(item_count),
            "ref": thai(egp_ref),
            "method": method,
        }
        amount_display = thai("{:,.2f}".format(amount or 0.0))
        body = _(
            "ตามที่ %(province)s ได้มีโครงการ %(project)s จำนวน %(count)s รายการ "
            "(%(ref)s) %(method)s นั้น %(items)s ผู้ได้รับการคัดเลือก ได้แก่ %(winner)s "
            "โดยเสนอราคา เป็นเงินทั้งสิ้น %(amount)s บาท (%(amount_text)s) "
            "รวมภาษีมูลค่าเพิ่มและภาษีอื่น ค่าขนส่ง ค่าจดทะเบียน และค่าใช้จ่ายอื่นๆ ทั้งปวง"
        ) % {
            "province": province,
            "project": project,
            "count": thai(item_count),
            "ref": thai(egp_ref),
            "method": method,
            "items": item_text,
            "winner": partner.display_name if partner else "",
            "amount": amount_display,
            "amount_text": self._winner_amount_text(amount),
        }
        signer_full = self._company_person_name(
            company, "official_doc_signer_name", "นายวีระศักดิ์ หล่อทองคำ"
        )
        signer_name, signer_full = self._split_thai_person_name(signer_full)
        signer_title = self._company_person_name(
            company,
            "official_doc_signer_position",
            "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต",
        )
        cert_full = self.env.user.name or ""
        cert_name, cert_full = self._split_thai_person_name(cert_full)
        return {
            "province": province,
            "subject": subject,
            "body": body,
            "announce_date": self._format_thai_date(announce_date, with_be_prefix=True),
            "signer_name": signer_name,
            "signer_full": signer_full,
            "signer_title": signer_title,
            "signer_acting": _("ปฏิบัติราชการแทนผู้ว่าราชการ%s") % province,
            "cert_name": cert_name,
            "cert_full": cert_full,
            "cert_title": self._current_user_job_title(),
            "web_date": self._format_thai_date(
                fields.Date.context_today(self), with_be_prefix=False
            ),
            "web_by": "%s %s" % (cert_full, self._current_user_job_title()),
        }

    def _winner_province(self, company):
        state = company.state_id or company.partner_id.state_id
        name = state.name if state else "ภูเก็ต"
        if name.startswith("จังหวัด"):
            return name
        return "จังหวัด%s" % name

    def _winner_method_phrase(self, requisition):
        method = requisition.procurement_method_id.name or "วิธีเฉพาะเจาะจง"
        if method.startswith("โดย"):
            return method
        if method.startswith("วิธี"):
            return "โดย%s" % method
        return "โดยวิธี%s" % method

    def _winner_item_text(self, requisition):
        lines = requisition.line_ids
        if not lines:
            return requisition.egp_project_name or "", 1
        parts = []
        for line in lines:
            name = line.product_description_variants or line.product_id.display_name
            qty = line.product_qty or 0.0
            qty_text = (
                self._thai_digits(int(qty))
                if float(qty).is_integer()
                else self._thai_digits(qty)
            )
            uom = line.product_uom_id.name or ""
            parts.append("%s จำนวน %s %s" % (name, qty_text, uom))
        return " ".join(parts), len(lines)

    def _winner_amount_text(self, amount):
        currency = self.requisition_id.currency_id
        if not currency:
            return ""
        try:
            return currency.with_context(lang="th_TH").amount_to_text(amount or 0.0)
        except Exception:
            return currency.amount_to_text(amount or 0.0) or ""

    def _company_person_name(self, company, field_name, default):
        if field_name in company._fields and company[field_name]:
            return company[field_name]
        return default

    def _split_thai_person_name(self, name):
        name = " ".join((name or "").split())
        for prefix in ("นางสาว", "นาย", "นาง"):
            if name.startswith(prefix):
                return name[len(prefix):].strip(), name
        return name, name

    def _current_user_job_title(self):
        employee = self.env.user.employee_id
        if employee and employee.job_id:
            return employee.job_id.name
        if employee and employee.job_title:
            return employee.job_title
        return "เจ้าหน้าที่"

    def _format_thai_date(self, date_value, with_be_prefix=False):
        if not date_value:
            return ""
        date_format = "{day} {month} พ.ศ. {year}" if with_be_prefix else "{day} {month} {year}"
        if "thai.utils" in self.env:
            formatted = self.env["thai.utils"].format_thai_date(
                date_value,
                format_date=date_format,
            )
        else:
            months = (
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
            year = date_value.year + 543
            if with_be_prefix:
                formatted = "%s %s พ.ศ. %s" % (
                    date_value.day,
                    months[date_value.month],
                    year,
                )
            else:
                formatted = "%s %s %s" % (
                    date_value.day,
                    months[date_value.month],
                    year,
                )
        return self._thai_digits(formatted)

    def _mimetype_for_filename(self, filename):
        name = (filename or "").lower()
        if name.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if name.endswith(".pdf"):
            return "application/pdf"
        guessed, _encoding = mimetypes.guess_type(filename or "")
        return guessed or "application/octet-stream"

    def _thai_digits(self, value):
        return str(value).translate(_THAI_DIGITS)
