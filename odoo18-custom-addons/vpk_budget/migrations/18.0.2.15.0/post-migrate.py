import logging

_logger = logging.getLogger(__name__)

_LINE_TYPE_TO_XMLID = {
    "supplies_budget": "budget_type_supplies",
    "asset_budget": "budget_type_asset",
    "construction_budget": "budget_type_construction",
    "project_budget": "budget_type_project",
    "material_budget": "budget_type_supplies",
    "medical_asset": "budget_type_asset",
    "non_medical_asset": "budget_type_asset",
    "item_5000_100000": "budget_type_asset",
    "construction": "budget_type_construction",
    "project": "budget_type_project",
}


def _get_budget_type_id(cr, code):
    xmlid = _LINE_TYPE_TO_XMLID.get(code)
    if not xmlid:
        cr.execute(
            "SELECT id FROM vpk_budget_type WHERE code = %s LIMIT 1",
            (code,),
        )
        row = cr.fetchone()
        return row[0] if row else None
    cr.execute(
        """
        SELECT res_id
        FROM ir_model_data
        WHERE module = 'vpk_budget' AND name = %s
        LIMIT 1
        """,
        (xmlid,),
    )
    row = cr.fetchone()
    if row:
        return row[0]
    cr.execute(
        "SELECT id FROM vpk_budget_type WHERE code = %s LIMIT 1",
        (code,),
    )
    row = cr.fetchone()
    return row[0] if row else None


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'vpk_budget_type'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'vpk_budget_request_form_type_line'
              AND column_name = 'budget_type_id'
        )
        """
    )
    if cr.fetchone()[0]:
        cr.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'vpk_budget_request_form_type_line'
                  AND column_name = 'line_type'
            )
            """
        )
        has_line_type = cr.fetchone()[0]
        if has_line_type:
            cr.execute(
                "SELECT id, line_type FROM vpk_budget_request_form_type_line WHERE budget_type_id IS NULL"
            )
            for line_id, line_type in cr.fetchall():
                budget_type_id = _get_budget_type_id(cr, line_type)
                if budget_type_id:
                    cr.execute(
                        """
                        UPDATE vpk_budget_request_form_type_line
                        SET budget_type_id = %s
                        WHERE id = %s
                        """,
                        (budget_type_id, line_id),
                    )
        cr.execute(
            """
            DELETE FROM vpk_budget_request_form_type_line AS dup
            USING vpk_budget_request_form_type_line AS keep
            WHERE dup.form_type_id = keep.form_type_id
              AND dup.budget_type_id = keep.budget_type_id
              AND dup.id > keep.id
            """
        )
        cr.execute(
            """
            ALTER TABLE vpk_budget_request_form_type_line
            DROP CONSTRAINT IF EXISTS vpk_budget_request_form_type_line_form_type_line_type_unique
            """
        )

    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'departmental_budget_request_line'
              AND column_name = 'budget_type_id'
        )
        """
    )
    if cr.fetchone()[0]:
        cr.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'departmental_budget_request_line'
                  AND column_name = 'line_type'
            )
            """
        )
        if cr.fetchone()[0]:
            cr.execute(
                "SELECT id, line_type FROM departmental_budget_request_line WHERE budget_type_id IS NULL"
            )
            for line_id, line_type in cr.fetchall():
                budget_type_id = _get_budget_type_id(cr, line_type)
                if budget_type_id:
                    cr.execute(
                        """
                        UPDATE departmental_budget_request_line
                        SET budget_type_id = %s
                        WHERE id = %s
                        """,
                        (budget_type_id, line_id),
                    )

    cr.execute(
        """
        UPDATE vpk_budget_request_form_type AS ft
        SET allowed_line_type_codes = mapped.codes
        FROM (
            SELECT
                form_type_id,
                string_agg(bt.code, ',' ORDER BY ftline.sequence, ftline.id) AS codes
            FROM vpk_budget_request_form_type_line AS ftline
            JOIN vpk_budget_type AS bt ON bt.id = ftline.budget_type_id
            GROUP BY form_type_id
        ) AS mapped
        WHERE ft.id = mapped.form_type_id
        """
    )

    _logger.info("Linked budget type master records to form and request lines")
