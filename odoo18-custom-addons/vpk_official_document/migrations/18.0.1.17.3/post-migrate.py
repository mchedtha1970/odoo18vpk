# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Document = env["vpk.official.document"].sudo()

    inflight = Document.search(
        [
            ("document_type", "=", "winner_announcement"),
            ("state", "=", "to_approve"),
        ]
    )
    # Snapshot misconfigured review shapes BEFORE repairing definitions
    # (writing reviewer_field_id recomputes reviewer_ids on existing reviews).
    rebuild_ids = []
    generator_def = env.ref(
        "vpk_official_document.tier_definition_winner_announcement_generator",
        raise_if_not_found=False,
    )
    for doc in inflight:
        reviews = doc.review_ids.sorted("sequence")
        if not reviews:
            rebuild_ids.append(doc.id)
            continue
        fields_used = {
            (review.definition_id.reviewer_field_id.name or "")
            for review in reviews
            if review.definition_id.reviewer_field_id
        }
        reviewer_sets = {
            tuple(sorted(review.reviewer_ids.ids)) for review in reviews
        }
        wrong_done_by = False
        if doc.officer_id and reviews and generator_def:
            first = reviews[0]
            if (
                first.status == "approved"
                and first.done_by
                and first.done_by != doc.officer_id
                and first.definition_id == generator_def
            ):
                wrong_done_by = True
        if (
            fields_used == {"signer_id"}
            or (
                len(reviews) >= 2
                and len(reviewer_sets) == 1
                and doc.officer_id
                and doc.signer_id
                and doc.officer_id != doc.signer_id
            )
            or wrong_done_by
        ):
            rebuild_ids.append(doc.id)

    Document._vpk_ensure_winner_tier_definitions()

    for doc in Document.browse(rebuild_ids):
        doc.review_ids.unlink()
        if doc.state != "to_approve":
            doc.with_context(skip_validation_check=True).write({"state": "to_approve"})
        doc._vpk_create_winner_sign_reviews()
