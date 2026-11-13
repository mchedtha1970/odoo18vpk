# -*- coding: utf-8 -*-
import os

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

FILE_TYPES = [
    ("kb01", "ขบ.01"),
    ("kb11", "ขบ.11"),
    ("other", "อื่น ๆ"),
]
FORM_CODE_TO_TYPE = {"ขบ.01": "kb01", "ขบ.11": "kb11"}
EXCEL_EXT = (".xls", ".xlsx", ".xlsm", ".csv")


class GfmisDocumentFile(models.Model):
    _name = "gfmis.document.file"
    _description = "ไฟล์แนบ Excel สำหรับอัปโหลดเข้า GFMIS"
    _order = "document_id, sequence, id"

    document_id = fields.Many2one(
        "gfmis.document",
        string="เอกสาร GFMIS",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    file_type = fields.Selection(
        FILE_TYPES,
        string="แบบฟอร์ม",
        required=True,
        default=lambda self: self._default_file_type(),
    )
    name = fields.Char(string="รายละเอียด")
    file = fields.Binary(string="ไฟล์ Excel", attachment=True, required=True)
    filename = fields.Char(string="ชื่อไฟล์")
    uploaded_by = fields.Many2one(
        "res.users", string="แนบโดย", default=lambda self: self.env.user, readonly=True
    )
    uploaded_on = fields.Datetime(
        string="แนบเมื่อ", default=fields.Datetime.now, readonly=True
    )
    gfmis_uploaded = fields.Boolean(
        string="อัปโหลดเข้า GFMIS แล้ว",
        help="การเงินติ๊กเมื่อนำไฟล์ไปอัปโหลดเข้าระบบ GFMIS ของกรมบัญชีกลางแล้ว",
    )
    gfmis_uploaded_on = fields.Date(string="วันที่อัปโหลด GFMIS")
    note = fields.Char(string="หมายเหตุ")

    @api.model
    def _default_file_type(self):
        document = self.env["gfmis.document"].browse(
            self.env.context.get("default_document_id") or []
        ).exists()
        return FORM_CODE_TO_TYPE.get(document.form_code, "kb01") if document else "kb01"

    @api.constrains("filename", "file_type")
    def _check_excel(self):
        for rec in self:
            if rec.file_type in ("kb01", "kb11") and rec.filename:
                if os.path.splitext(rec.filename.lower())[1] not in EXCEL_EXT:
                    raise ValidationError(
                        _("ไฟล์ %(type)s ต้องเป็นไฟล์ Excel (.xls / .xlsx) หรือ .csv เท่านั้น",
                          type=dict(FILE_TYPES)[rec.file_type])
                    )

    @api.onchange("gfmis_uploaded")
    def _onchange_gfmis_uploaded(self):
        if self.gfmis_uploaded and not self.gfmis_uploaded_on:
            self.gfmis_uploaded_on = fields.Date.context_today(self)

    def write(self, vals):
        if vals.get("gfmis_uploaded") and "gfmis_uploaded_on" not in vals:
            vals = dict(vals, gfmis_uploaded_on=fields.Date.context_today(self))
        res = super().write(vals)
        if "gfmis_uploaded" in vals:
            for rec in self:
                rec.document_id.message_post(
                    body=_(
                        "ไฟล์ %(type)s (%(file)s) %(state)s",
                        type=dict(FILE_TYPES)[rec.file_type],
                        file=rec.filename or rec.name or "-",
                        state=_("อัปโหลดเข้า GFMIS แล้ว") if rec.gfmis_uploaded else _("ยกเลิกสถานะอัปโหลด GFMIS"),
                    ),
                    subtype_xmlid="mail.mt_note",
                )
        return res
