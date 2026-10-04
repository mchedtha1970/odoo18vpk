# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

MAX_PDF_BYTES = 15 * 1024 * 1024


class VpkVendorTradeDocument(models.Model):
    _name = "vpk.vendor.trade.document"
    _description = "ข้อมูลทางการค้าของผู้จำหน่าย"
    _order = "doc_date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="ผู้จำหน่าย",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="ชื่อเอกสาร", required=True)
    doc_date = fields.Date(string="วันที่", default=fields.Date.context_today, required=True)
    note = fields.Char(string="หมายเหตุ")
    filename = fields.Char(string="ชื่อไฟล์")
    datas = fields.Binary(string="ไฟล์ PDF", attachment=True)
    has_pdf = fields.Boolean(compute="_compute_has_pdf", store=True)

    @api.depends("filename")
    def _compute_has_pdf(self):
        for record in self:
            record.has_pdf = (record.filename or "").lower().endswith(".pdf")

    @api.constrains("datas", "filename")
    def _check_pdf(self):
        for record in self:
            if not record.datas:
                continue
            filename = (record.filename or "").lower()
            if not filename.endswith(".pdf"):
                raise ValidationError(_("อัปโหลดได้เฉพาะไฟล์ PDF"))
            try:
                raw = base64.b64decode(record.datas)
            except Exception as err:
                raise ValidationError(_("ไฟล์ PDF ไม่ถูกต้อง")) from err
            if not raw.startswith(b"%PDF"):
                raise ValidationError(_("ไฟล์ไม่ใช่ PDF"))
            if len(raw) > MAX_PDF_BYTES:
                raise ValidationError(_("ไฟล์ต้องมีขนาดไม่เกิน 15 MB"))

    def _pdf_attachment(self):
        self.ensure_one()
        return self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("res_field", "=", "datas"),
            ],
            limit=1,
        )

    def action_open_pdf_viewer(self):
        self.ensure_one()
        attachment = self._pdf_attachment()
        if not attachment:
            raise UserError(_("ยังไม่มีไฟล์ PDF"))
        if attachment.mimetype != "application/pdf":
            attachment.write({"mimetype": "application/pdf"})
        return {
            "type": "ir.actions.client",
            "tag": "vpk_official_document_sign_pdf_viewer",
            "name": self.name or self.filename,
            "params": {
                "attachment_id": attachment.id,
                "res_model": self._name,
                "res_id": self.id,
                "title": self.filename or self.name,
                "can_sign": False,
            },
        }


class ResPartner(models.Model):
    _inherit = "res.partner"

    trade_document_ids = fields.One2many(
        "vpk.vendor.trade.document",
        "partner_id",
        string="ข้อมูลทางการค้า",
    )
