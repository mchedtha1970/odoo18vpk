# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Document = env["vpk.official.document"].sudo()
    Document._vpk_ensure_winner_tier_definitions()
    director = env.ref(
        "vpk_official_document.tier_definition_winner_announcement_director",
        raise_if_not_found=False,
    )

    inflight = Document.search(
        [
            ("document_type", "=", "winner_announcement"),
            ("state", "=", "to_approve"),
        ]
    )
    for doc in inflight:
        reviews = doc.review_ids.sorted("sequence")
        ok_single = (
            len(reviews) == 1
            and director
            and reviews[0].definition_id == director
            and reviews[0].status in ("waiting", "pending")
        )
        if ok_single:
            continue
        reviews.unlink()
        if doc.state != "to_approve":
            doc.with_context(skip_validation_check=True).write({"state": "to_approve"})
        doc._vpk_create_winner_sign_reviews()
