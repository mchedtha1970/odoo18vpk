from odoo import _, api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def init(self):
        super().init()
        # ไฟล์ที่อัปโหลดจากปุ่มแนบถูกสร้างไว้แล้ว แต่ยังไม่ได้ผูกกับรายการ
        self.env.cr.execute(
            """
            INSERT INTO purchase_request_line_spec_attachment_rel (line_id, attachment_id)
            SELECT a.res_id, a.id
              FROM ir_attachment a
              JOIN purchase_request_line l ON l.id = a.res_id
             WHERE a.res_model = 'purchase.request.line'
               AND COALESCE(a.res_field, '') = ''
               AND NOT EXISTS (
                    SELECT 1
                      FROM purchase_request_line_spec_attachment_rel r
                     WHERE r.line_id = a.res_id
                       AND r.attachment_id = a.id
               )
            """
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (
                vals.get("res_model") == "purchase.request.line"
                and not vals.get("res_field")
                and not (vals.get("name") or "").lower().endswith(".pdf")
            ):
                raise UserError(_("แนบได้เฉพาะไฟล์ PDF"))
        attachments = super().create(vals_list)
        attachments._vpk_link_request_line_specs()
        return attachments

    def _vpk_link_request_line_specs(self):
        """ผูกไฟล์ที่อัปโหลดเข้าช่องเอกสารแนบคุณลักษณะทันที ไม่ต้องรอการบันทึกฟอร์ม."""
        grouped = {}
        for attachment in self:
            if (
                attachment.res_model != "purchase.request.line"
                or not attachment.res_id
                or attachment.res_field
            ):
                continue
            grouped.setdefault(attachment.res_id, self.env["ir.attachment"])
            grouped[attachment.res_id] |= attachment
        if not grouped:
            return
        lines = self.env["purchase.request.line"].sudo().browse(list(grouped))
        for line in lines.exists():
            missing = grouped[line.id] - line.spec_attachment_ids
            if missing:
                line.sudo().write({
                    "spec_attachment_ids": [(4, attachment.id) for attachment in missing],
                })
