from odoo import api, fields, models

STUDIO_MODEL = "vpk.document.studio.document"


class TierReview(models.Model):
    _inherit = "tier.review"

    vpk_signer_user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ลงนามตามลำดับ",
        ondelete="set null",
        index=True,
    )
    vpk_signer_name = fields.Char(string="ชื่อที่ประทับลายเซ็น")

    @api.model
    def _get_reviewer_fields(self):
        return super()._get_reviewer_fields() + ["vpk_signer_user_id"]

    def _get_reviewers(self):
        if self.vpk_signer_user_id:
            return self.vpk_signer_user_id
        return super()._get_reviewers()

    def _vpk_studio_document(self):
        self.ensure_one()
        if self.model != STUDIO_MODEL or not self.res_id:
            return self.env[STUDIO_MODEL]
        return self.env[STUDIO_MODEL].browse(self.res_id).exists()

    def action_open_pdf_viewer(self):
        self.ensure_one()
        document = self._vpk_studio_document()
        if not document:
            return super().action_open_pdf_viewer()
        can_sign = self.status == "pending" and self.can_review
        return document.sudo()._sign_viewer_action(can_sign=can_sign)
