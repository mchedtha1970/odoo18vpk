import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'vpk_budget'
          AND model = 'vpk.budget.request.form.type.line'
          AND name LIKE 'budget_request_form_type_line_%'
          AND NOT EXISTS (
              SELECT 1
              FROM vpk_budget_request_form_type_line AS line
              WHERE line.id = ir_model_data.res_id
          )
        """
    )
    _logger.info("Cleaned orphaned form type line XML IDs after line-type migration")
