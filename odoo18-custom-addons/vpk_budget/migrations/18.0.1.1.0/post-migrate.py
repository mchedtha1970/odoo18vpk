import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'vpk_budget_material_group'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'vpk_budget_group'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute("SELECT COUNT(*) FROM vpk_budget_group")
    if cr.fetchone()[0]:
        return

    cr.execute(
        """
        INSERT INTO vpk_budget_group (
            sequence, name, code, active, description,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            sequence, name, code, active, description,
            create_uid, create_date, write_uid, write_date
        FROM vpk_budget_material_group
        """
    )
    _logger.info(
        "Migrated records from vpk.budget.material.group to vpk.budget.group"
    )
