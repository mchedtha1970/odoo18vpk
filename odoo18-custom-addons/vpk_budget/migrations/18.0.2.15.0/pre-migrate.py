import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        ALTER TABLE vpk_budget_request_form_type_line
        DROP CONSTRAINT IF EXISTS vpk_budget_request_form_type_line_form_type_line_type_unique
        """
    )

    cr.execute(
        """
        DELETE FROM vpk_budget_request_form_type_line AS dup
        USING vpk_budget_request_form_type_line AS keep
        WHERE dup.form_type_id = keep.form_type_id
          AND dup.line_type = keep.line_type
          AND dup.id > keep.id
        """
    )

    _logger.info(
        "Dropped legacy form-type line constraint and removed duplicate line types"
    )
