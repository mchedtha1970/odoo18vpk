# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).


def migrate(cr, version):
    """Backfill PO budget links from PR and release fully-covered PR reservations."""
    cr.execute(
        """
        UPDATE purchase_order_line pol
        SET budget_line_id = prl.budget_line_id,
            budget_post_id = prl.budget_post_id
        FROM purchase_request_purchase_order_line_rel rel
        JOIN purchase_request_line prl ON prl.id = rel.purchase_request_line_id
        WHERE rel.purchase_order_line_id = pol.id
          AND pol.budget_line_id IS NULL
          AND prl.budget_line_id IS NOT NULL
        """
    )
    # Deactivate PR reservation when all lines are fully covered by confirmed POs
    # (ORM will refine on next confirm/cancel; this clears obvious double-hold)
    cr.execute(
        """
        UPDATE purchase_request pr
        SET budget_reservation_active = FALSE
        WHERE pr.budget_reservation_active = TRUE
          AND NOT EXISTS (
            SELECT 1
            FROM purchase_request_line prl
            WHERE prl.request_id = pr.id
              AND COALESCE(prl.cancelled, FALSE) = FALSE
              AND NOT EXISTS (
                SELECT 1
                FROM purchase_request_purchase_order_line_rel rel
                JOIN purchase_order_line pol ON pol.id = rel.purchase_order_line_id
                JOIN purchase_order po ON po.id = pol.order_id
                WHERE rel.purchase_request_line_id = prl.id
                  AND po.state IN ('purchase', 'done')
              )
          )
          AND EXISTS (
            SELECT 1
            FROM purchase_request_line prl2
            JOIN purchase_request_purchase_order_line_rel rel2
              ON rel2.purchase_request_line_id = prl2.id
            JOIN purchase_order_line pol2 ON pol2.id = rel2.purchase_order_line_id
            JOIN purchase_order po2 ON po2.id = pol2.order_id
            WHERE prl2.request_id = pr.id
              AND po2.state IN ('purchase', 'done')
          )
        """
    )
