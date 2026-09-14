from markupsafe import escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseSpecAttachmentViewer(models.TransientModel):
    _name = "purchase.spec.attachment.viewer"
    _description = "Viewer ไฟล์คุณลักษณะพัสดุ"

    name = fields.Char(string="ชื่อรายการ", readonly=True)
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="ไฟล์ที่กำลังแสดง",
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name="purchase.spec.attachment.viewer.line",
        inverse_name="viewer_id",
        string="ไฟล์ทั้งหมด",
        readonly=True,
    )
    preview_html = fields.Html(
        string="ตัวอย่างไฟล์",
        compute="_compute_preview_html",
        sanitize=False,
    )

    @api.depends("attachment_id")
    def _compute_preview_html(self):
        for viewer in self:
            attachment = viewer.attachment_id
            if not attachment:
                viewer.preview_html = (
                    '<div class="alert alert-info">กรุณาเลือกไฟล์ที่ต้องการดู</div>'
                )
                continue
            url = "/web/content/%s?download=false" % attachment.id
            filename = escape(attachment.name or _("ไฟล์แนบ"))
            mimetype = attachment.mimetype or ""
            if mimetype.startswith("image/"):
                viewer.preview_html = (
                    '<div style="height:68vh;text-align:center;overflow:auto;">'
                    '<img src="%s" alt="%s" '
                    'style="max-width:100%%;max-height:66vh;object-fit:contain;"/>'
                    "</div>"
                ) % (url, filename)
            elif mimetype == "application/pdf":
                viewer.preview_html = (
                    '<iframe src="%s" title="%s" '
                    'style="width:100%%;height:68vh;border:1px solid #ddd;"></iframe>'
                ) % (url, filename)
            elif mimetype.startswith("text/"):
                viewer.preview_html = (
                    '<iframe src="%s" title="%s" '
                    'style="width:100%%;height:68vh;border:1px solid #ddd;"></iframe>'
                ) % (url, filename)
            else:
                viewer.preview_html = (
                    '<div class="alert alert-warning">'
                    "ไฟล์ <strong>%s</strong> ไม่รองรับการแสดงตัวอย่างในหน้าจอ "
                    '<a href="%s" target="_blank">คลิกเพื่อเปิด/ดาวน์โหลด</a>'
                    "</div>"
                ) % (filename, url)

    @api.model
    def action_open_viewer(self, attachments, title=None):
        attachments = attachments.exists()
        if not attachments:
            raise UserError(_("ไม่พบไฟล์แนบสำหรับเปิดดู"))
        viewer = self.create({
            "name": title or _("Viewer ไฟล์คุณลักษณะ"),
            "attachment_id": attachments[0].id,
            "line_ids": [
                (0, 0, {"attachment_id": attachment.id})
                for attachment in attachments
            ],
        })
        return viewer._viewer_action()

    def _viewer_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name or _("Viewer ไฟล์คุณลักษณะ"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_download(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("กรุณาเลือกไฟล์"))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % self.attachment_id.id,
            "target": "new",
        }


class PurchaseSpecAttachmentViewerLine(models.TransientModel):
    _name = "purchase.spec.attachment.viewer.line"
    _description = "รายการไฟล์ใน Viewer คุณลักษณะ"
    _order = "id"

    viewer_id = fields.Many2one(
        comodel_name="purchase.spec.attachment.viewer",
        required=True,
        ondelete="cascade",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="ชื่อไฟล์",
        required=True,
        readonly=True,
    )
    name = fields.Char(related="attachment_id.name", string="ชื่อไฟล์")
    mimetype = fields.Char(related="attachment_id.mimetype", string="ชนิดไฟล์")

    def action_preview(self):
        self.ensure_one()
        self.viewer_id.attachment_id = self.attachment_id
        return self.viewer_id._viewer_action()
