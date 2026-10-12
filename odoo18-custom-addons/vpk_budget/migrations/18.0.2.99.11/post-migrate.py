# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).


def migrate(cr, version):
    """Keep a previously selected single load category as one of the new tags."""
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'departmental_budget_request'
          AND column_name = 'load_budget_post_id'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'departmental_budget_request_load_post_rel'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        INSERT INTO departmental_budget_request_load_post_rel
            (request_id, budget_post_id)
        SELECT request.id, request.load_budget_post_id
        FROM departmental_budget_request request
        WHERE request.load_budget_post_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM departmental_budget_request_load_post_rel rel
              WHERE rel.request_id = request.id
                AND rel.budget_post_id = request.load_budget_post_id
          )
        """
    )
