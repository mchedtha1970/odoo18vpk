import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'departmental_budget_request_line'
              AND column_name = 'received_budget_amount'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    # Keep allocated values; if empty, copy from received before drop.
    cr.execute(
        """
        UPDATE departmental_budget_request_line
           SET allocated_budget_amount = received_budget_amount
         WHERE COALESCE(allocated_budget_amount, 0) = 0
           AND COALESCE(received_budget_amount, 0) <> 0
        """
    )
    cr.execute(
        """
        ALTER TABLE departmental_budget_request_line
        DROP COLUMN IF EXISTS received_budget_amount
        """
    )
    _logger.info("Removed received_budget_amount; using allocated_budget_amount instead")
