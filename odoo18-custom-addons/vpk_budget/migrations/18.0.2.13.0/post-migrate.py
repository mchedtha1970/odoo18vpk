import logging

_logger = logging.getLogger(__name__)

_CODE_TO_LINE_TYPES = {
    "asset": ["medical_asset", "non_medical_asset"],
    "item_5000_100000": ["item_5000_100000"],
    "material_budget": ["material_budget"],
    "construction": ["construction"],
    "project": ["project"],
}


def migrate(cr, version):
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

    cr.execute("SELECT id, code FROM vpk_budget_request_form_type")
    for form_type_id, code in cr.fetchall():
        cr.execute(
            """
            SELECT COUNT(*)
            FROM vpk_budget_request_form_type_line
            WHERE form_type_id = %s
            """,
            (form_type_id,),
        )
        if cr.fetchone()[0]:
            continue

        line_types = _CODE_TO_LINE_TYPES.get(code, [])
        for sequence, line_type in enumerate(line_types, start=1):
            cr.execute(
                """
                INSERT INTO vpk_budget_request_form_type_line
                    (form_type_id, sequence, line_type, create_uid, write_uid, create_date, write_date)
                VALUES (%s, %s, %s, 1, 1, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC')
                """,
                (form_type_id, sequence * 10, line_type),
            )

        _logger.info(
            "Seeded %s line type mappings for form type %s (%s)",
            len(line_types),
            form_type_id,
            code,
        )

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
