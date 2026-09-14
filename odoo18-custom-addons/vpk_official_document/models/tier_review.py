# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class TierReview(models.Model):
    _inherit = "tier.review"

    vpk_signer_user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ลงนามตามลำดับ",
        ondelete="set null",
        index=True,
    )
    vpk_signer_name = fields.Char(string="ชื่อที่ประทับลายเซ็น")
    vpk_signer_line_id = fields.Many2one(
        comodel_name="vpk.official.document.line",
        string="รายการกรรมการ",
        ondelete="set null",
    )

    @api.model
    def _get_reviewer_fields(self):
        return super()._get_reviewer_fields() + [
            "definition_id.reviewer_field_id",
            "model",
            "res_id",
            "vpk_signer_user_id",
        ]

    @api.depends(lambda self: self._get_reviewer_fields())
    def _compute_reviewer_ids(self):
        # reviewer_field_id is ir.model.fields; purchase users cannot read it.
        for rec in self:
            rec.reviewer_ids = rec.sudo()._get_reviewers()

    def _get_reviewers(self):
        rec = self.sudo()
        if rec.vpk_signer_user_id:
            return rec.vpk_signer_user_id
        if (
            rec.model == "vpk.official.document"
            and rec.review_type == "field"
            and rec.reviewer_field_id
            and rec.res_id
        ):
            document = rec.env["vpk.official.document"].browse(rec.res_id)
            reviewer_field = getattr(document, rec.reviewer_field_id.name, False)
            if reviewer_field and reviewer_field._name == "res.users":
                return reviewer_field
        return super(TierReview, rec)._get_reviewers()

    def _vpk_record_for_reviewer_expression(self):
        """PR formulas use requested_by; evaluate them on the parent PR."""
        self.ensure_one()
        if not self.model or not self.res_id:
            return self.env[self.model] if self.model else self.env["purchase.request"]
        record = self.env[self.model].sudo().browse(self.res_id).exists()
        if (
            self.model == "vpk.official.document"
            and record
            and record.request_id
        ):
            return record.request_id
        return record

    @api.depends("definition_id.reviewer_expression", "review_type", "model", "res_id")
    def _compute_python_reviewer_ids(self):
        official = self.filtered(
            lambda rec: rec.review_type == "expression"
            and rec.model == "vpk.official.document"
        )
        remaining = self - official
        if remaining:
            super(TierReview, remaining)._compute_python_reviewer_ids()
        Users = self.env["res.users"]
        for rec in official:
            record = rec._vpk_record_for_reviewer_expression()
            if not record:
                rec.python_reviewer_ids = Users
                continue
            try:
                reviewer_ids = safe_eval(
                    rec.definition_id.reviewer_expression,
                    globals_dict={"rec": record},
                )
            except Exception as error:
                raise UserError(
                    _("Error evaluating tier validation conditions.\n %s") % error
                ) from error
            if (
                not isinstance(reviewer_ids, models.Model)
                or reviewer_ids._name != "res.users"
            ):
                raise UserError(
                    _("Reviewer python expression must return a res.users recordset.")
                )
            rec.python_reviewer_ids = reviewer_ids
