import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'budget_lines'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        UPDATE budget_lines bl
        SET
            request_line_id = src.request_line_id,
            budget_group_id = src.budget_group_id,
            material_sub_type_id = src.material_sub_type_id
        FROM (
            SELECT DISTINCT ON (dbr.id, dbrl.budget_post_id)
                dbr.id AS request_id,
                dbrl.id AS request_line_id,
                dbrl.budget_post_id,
                dbrl.budget_group_id,
                dbrl.material_sub_type_id
            FROM departmental_budget_request dbr
            JOIN departmental_budget_request_line dbrl
                ON dbrl.request_id = dbr.id
            WHERE dbrl.budget_post_id IS NOT NULL
            ORDER BY dbr.id, dbrl.budget_post_id, dbrl.id
        ) src
        WHERE bl.request_id = src.request_id
            AND bl.general_budget_id = src.budget_post_id
            AND bl.request_line_id IS NULL
        """
    )
    _logger.info("Backfilled budget line request/group links for PR budget checks")
