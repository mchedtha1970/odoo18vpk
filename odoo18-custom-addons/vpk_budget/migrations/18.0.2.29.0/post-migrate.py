import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'account_budget_post'
              AND column_name = 'parent_budget_post_id'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    def get_root_id(post_id):
        current = post_id
        while True:
            cr.execute(
                """
                SELECT parent_budget_post_id
                FROM account_budget_post
                WHERE id = %s
                """,
                (current,),
            )
            row = cr.fetchone()
            if not row or not row[0]:
                return current
            current = row[0]

    while True:
        cr.execute(
            """
            SELECT id
            FROM account_budget_post
            WHERE parent_budget_post_id IS NOT NULL
            """
        )
        generated_ids = [row[0] for row in cr.fetchall()]
        if not generated_ids:
            break

        for post_id in generated_ids:
            root_id = get_root_id(post_id)
            cr.execute(
                """
                UPDATE departmental_budget_request_line
                SET budget_post_id = %s
                WHERE budget_post_id = %s
                """,
                (root_id, post_id),
            )
            cr.execute(
                """
                UPDATE budget_lines
                SET general_budget_id = %s
                WHERE general_budget_id = %s
                """,
                (root_id, post_id),
            )

        cr.execute(
            """
            DELETE FROM account_budget_post
            WHERE parent_budget_post_id IS NOT NULL
            """
        )

    _logger.info(
        "Reverted auto-generated material budget posts; lines now use master posts"
    )
