# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import os
from urllib.parse import quote

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .file_preview import (
    excel_workbook,
    extension_of,
    file_type_from_name,
    mimetype_from_name,
    render_preview,
    sheet_viewer_page,
    validate_file_content,
    viewer_page,
)


class VpkDocument(models.Model):
    _name = "vpk.document"
    _description = "เอกสารแนบไฟล์"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "document_date desc, id desc"

    name = fields.Char(string="ชื่อเอกสาร", required=True, tracking=True)
    category_id = fields.Many2one(
        comodel_name="vpk.document.category",
        string="หมวดหมู่",
        required=True,
        tracking=True,
        index=True,
        ondelete="restrict",
    )
    file = fields.Binary(string="ไฟล์", required=True, attachment=True)
    file_name = fields.Char(string="ชื่อไฟล์", required=True, tracking=True)
    file_type = fields.Selection(
        selection=[
            ("pdf", "PDF"),
            ("excel", "Excel"),
            ("word", "Word"),
            ("image", "รูปภาพ"),
        ],
        string="ชนิดไฟล์",
        compute="_compute_file_type",
        store=True,
        index=True,
    )
    mimetype = fields.Char(string="MIME Type", compute="_compute_file_type", store=True)
    document_date = fields.Date(
        string="วันที่เอกสาร",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อัปโหลด",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    description = fields.Text(string="รายละเอียด")
    active = fields.Boolean(default=True)
    upload_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="vpk_document_multi_upload_rel",
        column1="document_id",
        column2="attachment_id",
        string="ไฟล์",
    )
    preview_html = fields.Html(
        string="ตัวอย่างไฟล์",
        compute="_compute_preview_html",
        sanitize=False,
    )

    @api.depends("file_name")
    def _compute_file_type(self):
        for document in self:
            document.file_type = file_type_from_name(document.file_name)
            document.mimetype = mimetype_from_name(document.file_name) or False

    @api.depends("file", "file_name", "file_type")
    def _compute_preview_html(self):
        for document in self:
            if not isinstance(document.id, int):
                document.preview_html = Markup(
                    '<div class="alert alert-info">'
                    "บันทึกเอกสารก่อนจึงจะดูไฟล์ได้"
                    "</div>"
                )
                continue
            try:
                raw = document._file_bytes()
            except ValueError:
                raw = b""
            if not raw:
                document.preview_html = Markup(
                    '<div class="alert alert-info">ยังไม่มีไฟล์ให้แสดง</div>'
                )
                continue
            document.preview_html = Markup(
                '<iframe src="/vpk_document/open/{}" title="{}" '
                'style="width:100%;height:75vh;border:1px solid #dee2e6;'
                'background:#fff;"></iframe>'
            ).format(document.id, escape(document.file_name or document.name or ""))

    @api.onchange("file_name")
    def _onchange_file_name(self):
        if self.file_name and not self.name:
            self.name = os.path.splitext(self.file_name)[0]
        if self.file_name and not file_type_from_name(self.file_name):
            return {
                "warning": {
                    "title": _("ชนิดไฟล์ไม่รองรับ"),
                    "message": _(
                        "รองรับเฉพาะ PDF, Excel (.xls, .xlsx), "
                        "Word (.doc, .docx) และรูปภาพ"
                    ),
                }
            }
        return None

    def _upload_attachment_ids(self, commands):
        attachment_ids = []
        for command in commands or []:
            if not isinstance(command, (list, tuple)) or not command:
                continue
            if command[0] == 6:
                attachment_ids = list(command[2])
            elif command[0] == 4:
                attachment_ids.append(command[1])
            elif command[0] == 5:
                attachment_ids = []
            elif command[0] == 3 and command[1] in attachment_ids:
                attachment_ids.remove(command[1])
        return attachment_ids

    def _document_vals_from_attachment(self, attachment, shared, name=None):
        attachment = attachment.with_context(bin_size=False)
        filename = attachment.name or _("เอกสาร")
        datas = attachment.datas
        raw = base64.b64decode(datas) if datas else b""
        try:
            validate_file_content(filename, raw)
        except ValueError as error:
            raise ValidationError(_("ไฟล์ %s: %s") % (filename, error)) from error
        values = dict(shared)
        values.update({
            "name": name or os.path.splitext(filename)[0] or filename,
            "file_name": filename,
            "file": datas,
        })
        return values

    @api.model_create_multi
    def create(self, vals_list):
        expanded = []
        staging = self.env["ir.attachment"]
        for vals in vals_list:
            vals = dict(vals)
            upload_commands = vals.pop("upload_ids", None)
            upload_ids = self._upload_attachment_ids(upload_commands)
            if not upload_ids:
                if not vals.get("file") and not vals.get("name"):
                    raise ValidationError(_("กรุณาเลือกไฟล์อย่างน้อย 1 ไฟล์"))
                expanded.append(vals)
                continue
            attachments = self.env["ir.attachment"].browse(upload_ids).exists()
            if not attachments:
                raise ValidationError(_("กรุณาเลือกไฟล์อย่างน้อย 1 ไฟล์"))
            shared = {
                key: vals[key]
                for key in ("category_id", "document_date", "description", "user_id", "company_id")
                if vals.get(key)
            }
            typed_name = vals.get("name")
            use_typed_name = bool(typed_name) and len(attachments) == 1
            for attachment in attachments:
                expanded.append(self._document_vals_from_attachment(
                    attachment,
                    shared,
                    name=typed_name if use_typed_name else None,
                ))
            staging |= attachments
        if staging:
            staging.unlink()
        return super().create(expanded)

    def web_save(self, vals, specification, next_id=None):
        if self:
            self.write(vals)
            records = self
        else:
            records = self.create(vals)
        if next_id:
            records = self.browse(next_id)
        elif len(records) > 1:
            records[0].message_post(
                body=_(
                    "สร้างเอกสาร %s รายการในหมวดหมู่ %s แต่ละไฟล์เป็นเอกสารแยก"
                ) % (len(records), records[0].category_id.display_name),
                subtype_xmlid="mail.mt_note",
            )
            records = records[:1]
        return records.with_context(bin_size=True).web_read(specification)

    def _file_bytes(self):
        """Return the uploaded file bytes.

        The web client saves records with ``bin_size`` in the context, which
        makes a binary field return a label such as ``15.2 Kb``. Decoding that
        label raises ``Incorrect padding``.
        """
        self.ensure_one()
        value = self.with_context(bin_size=False).file
        if not value:
            return b""
        if isinstance(value, str):
            value = value.encode()
        return base64.b64decode(value)

    @api.constrains("file", "file_name")
    def _check_supported_file(self):
        for document in self:
            try:
                raw = document._file_bytes()
            except ValueError as error:
                raise ValidationError(_("อ่านไฟล์ไม่สำเร็จ: %s") % error) from error
            if not raw:
                continue
            try:
                validate_file_content(document.file_name, raw)
            except ValueError as error:
                raise ValidationError(str(error)) from error

    def _get_file_attachment(self):
        self.ensure_one()
        if not isinstance(self.id, int):
            return self.env["ir.attachment"]
        return self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("res_field", "=", "file"),
            ],
            limit=1,
        )

    def _open_payload(self):
        """Bytes to display in the browser, without Content-Disposition attachment."""
        self.ensure_one()
        raw = self._file_bytes()
        if self.file_type in ("pdf", "image"):
            return raw, (self.mimetype or "application/octet-stream")
        if self.file_type == "excel":
            workbook = excel_workbook(raw, extension_of(self.file_name))
            page = sheet_viewer_page(self.name or self.file_name, workbook)
            return page.encode("utf-8"), "text/html; charset=utf-8"
        page = viewer_page(
            self.name or self.file_name,
            render_preview(self.file_name, raw),
        )
        return page.encode("utf-8"), "text/html; charset=utf-8"

    def action_view_file(self):
        self.ensure_one()
        if not isinstance(self.id, int):
            raise UserError(_("บันทึกเอกสารก่อนจึงจะเปิดไฟล์ได้"))
        if not self.with_context(bin_size=False).file:
            raise UserError(_("ยังไม่มีไฟล์แนบ"))
        return {
            "type": "ir.actions.act_url",
            "url": "/vpk_document/open/%s" % self.id,
            "target": "new",
        }

    def action_open_google_sheet(self):
        self.ensure_one()
        self.env["vpk.document.google.service"]._check_google_file(self)
        self.env["vpk.document.google.service"]._client_config()
        return {
            "type": "ir.actions.act_url",
            "url": "/vpk_document/google/open/%s" % self.id,
            "target": "new",
        }

    def _download_filename(self):
        """File name used when saving, taken from the form title."""
        self.ensure_one()
        original = self.file_name or ""
        extension = os.path.splitext(original)[1]
        stem = (self.name or os.path.splitext(original)[0] or "document").strip()
        for char in '\\/:*?"<>|\r\n\t':
            stem = stem.replace(char, " ")
        stem = " ".join(stem.split()) or "document"
        if extension and not stem.lower().endswith(extension.lower()):
            return stem + extension
        return stem

    def action_download(self):
        self.ensure_one()
        attachment = self._get_file_attachment()
        if not attachment:
            raise UserError(_("ไม่พบไฟล์สำหรับดาวน์โหลด"))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s/%s?download=true" % (
                attachment.id,
                quote(self._download_filename()),
            ),
            "target": "new",
        }
