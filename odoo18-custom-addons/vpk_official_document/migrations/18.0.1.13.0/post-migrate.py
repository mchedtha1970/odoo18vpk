# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Request = env["purchase.request"]
    inflight = Request.search(
        [("state", "not in", ("draft", "rejected", "cancel", "cancelled", "done"))]
    )
    docs = env["vpk.official.document"].search(
        [
            ("document_type", "=", "integrity_over_100k"),
            ("state", "in", ("generated", "to_approve")),
            ("request_id", "in", inflight.ids),
        ]
    )
    for doc in docs:
        pending = doc.review_ids.filtered(
            lambda review: review.status in ("waiting", "pending")
        )
        if pending:
            pending.unlink()
        if doc.state == "generated":
            doc.with_context(skip_validation_check=True).write({"state": "to_approve"})
        doc._vpk_create_integrity_sign_reviews()
