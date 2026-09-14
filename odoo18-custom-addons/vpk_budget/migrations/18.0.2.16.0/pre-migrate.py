import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'departmental_budget_request_line'
          AND column_name = 'current_age_year'
        """
    )
    row = cr.fetchone()
    if not row:
        return
    if row[0] not in ("double precision", "numeric", "real", "integer", "bigint"):
        return

    cr.execute(
        """
        ALTER TABLE departmental_budget_request_line
        ALTER COLUMN current_age_year TYPE varchar
        USING CASE
            WHEN current_age_year IS NULL THEN NULL
            ELSE trim(to_char(current_age_year, 'FM999999999.##'))
        END
        """
    )
    _logger.info("Converted current_age_year from numeric to text on budget request lines")
