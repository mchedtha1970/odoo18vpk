from odoo import api, models

from .studio_document import PR_APPROVAL_PACKET_TYPES

STUDIO_MODEL = "vpk.document.studio.document"


class TierReview(models.Model):
    _inherit = "tier.review"

    @api.model
    def _vpk_hidden_pr_inbox_review_ids(self):
        """Hide PR rows while the packet is signed, and reviews of closed documents."""
        hidden_ids = super()._vpk_hidden_pr_inbox_review_ids()
        Review = self.sudo()
        Document = self.env[STUDIO_MODEL].sudo()
        pending = Document.search(
            [
                ("document_type_code", "in", PR_APPROVAL_PACKET_TYPES),
                ("state", "=", "to_approve"),
                ("request_id", "!=", False),
            ]
        )
        if pending:
            hidden_ids += Review.search(
                [
                    ("model", "=", "purchase.request"),
                    ("res_id", "in", pending.mapped("request_id").ids),
                    ("status", "in", ("pending", "waiting")),
                ]
            ).ids
        closed = Document.search([("state", "in", ("approved", "cancelled"))])
        if closed:
            hidden_ids += Review.search(
                [
                    ("model", "=", STUDIO_MODEL),
                    ("res_id", "in", closed.ids),
                    ("status", "in", ("pending", "waiting")),
                ]
            ).ids
        cancelled = closed.filtered(lambda doc: doc.state == "cancelled")
        if cancelled:
            hidden_ids += Review.search(
                [
                    ("model", "=", STUDIO_MODEL),
                    ("res_id", "in", cancelled.ids),
                    ("status", "=", "approved"),
                ]
            ).ids
        return hidden_ids
