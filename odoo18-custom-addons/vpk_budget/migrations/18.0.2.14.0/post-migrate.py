import logging

_logger = logging.getLogger(__name__)

_OLD_TO_NEW = {
    "material_budget": "supplies_budget",
    "medical_asset": "asset_budget",
    "non_medical_asset": "asset_budget",
    "item_5000_100000": "asset_budget",
    "construction": "construction_budget",
    "project": "project_budget",
}

_FORM_CODE_TO_LINE_TYPE = {
    "asset": "asset_budget",
    "item_5000_100000": "asset_budget",
    "material_budget": "supplies_budget",
    "construction": "construction_budget",
    "project": "project_budget",
}


def _update_request_line_types(cr):
    for old_value, new_value in _OLD_TO_NEW.items():
        cr.execute(
            """
            UPDATE departmental_budget_request_line
            SET line_type = %s
            WHERE line_type = %s
            """,
            (new_value, old_value),
        )


def _rebuild_form_type_lines(cr):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'vpk_budget_request_form_type_line'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        "SELECT id, form_type_id, line_type FROM vpk_budget_request_form_type_line ORDER BY form_type_id, id"
    )
    mapped_types_by_form = {}
    for _line_id, form_type_id, line_type in cr.fetchall():
        mapped_types_by_form.setdefault(form_type_id, set()).add(
            _OLD_TO_NEW.get(line_type, line_type)
        )

    cr.execute("DELETE FROM vpk_budget_request_form_type_line")

    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'vpk_budget'
          AND model = 'vpk.budget.request.form.type.line'
          AND name LIKE 'budget_request_form_type_line_%'
        """
    )

    cr.execute("SELECT id, code FROM vpk_budget_request_form_type")
    for form_type_id, code in cr.fetchall():
        line_types = mapped_types_by_form.get(form_type_id) or set()
        if not line_types:
            default_line_type = _FORM_CODE_TO_LINE_TYPE.get(code)
            if default_line_type:
                line_types.add(default_line_type)
        for sequence, line_type in enumerate(sorted(line_types), start=1):
            cr.execute(
                """
                INSERT INTO vpk_budget_request_form_type_line
                    (form_type_id, sequence, line_type, create_uid, write_uid, create_date, write_date)
                VALUES (%s, %s, %s, 1, 1, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC')
                """,
                (form_type_id, sequence * 10, line_type),
            )


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'departmental_budget_request_line'
        )
        """
    )
    if cr.fetchone()[0]:
        _update_request_line_types(cr)

    _rebuild_form_type_lines(cr)

    cr.execute(
        """
        UPDATE vpk_budget_request_form_type AS ft
        SET allowed_line_type_codes = mapped.codes
        FROM (
            SELECT form_type_id, string_agg(line_type, ',' ORDER BY sequence, id) AS codes
            FROM vpk_budget_request_form_type_line
            GROUP BY form_type_id
        ) AS mapped
        WHERE ft.id = mapped.form_type_id
        """
    )

    _logger.info("Migrated budget request line types to supplies/asset/construction/project budget")
