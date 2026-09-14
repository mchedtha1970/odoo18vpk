import logging

_logger = logging.getLogger(__name__)

_LINE_TYPE_TO_FORM_CODE = {
    "medical_asset": "asset",
    "non_medical_asset": "asset",
    "item_5000_100000": "item_5000_100000",
    "material_budget": "material_budget",
    "construction": "construction",
    "project": "project",
}


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'departmental_budget_request'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'vpk_budget_request_form_type'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT id
        FROM departmental_budget_request
        WHERE form_type_id IS NULL
        """
    )
    request_ids = [row[0] for row in cr.fetchall()]
    if not request_ids:
        return

    cr.execute("SELECT id, code FROM vpk_budget_request_form_type")
    form_type_by_code = {code: form_type_id for form_type_id, code in cr.fetchall()}

    for request_id in request_ids:
        cr.execute(
            """
            SELECT line_type
            FROM departmental_budget_request_line
            WHERE request_id = %s
            ORDER BY sequence, id
            LIMIT 1
            """,
            (request_id,),
        )
        row = cr.fetchone()
        form_code = _LINE_TYPE_TO_FORM_CODE.get(row[0] if row else None, "material_budget")
        form_type_id = form_type_by_code.get(form_code)
        if not form_type_id:
            continue
        cr.execute(
            """
            UPDATE departmental_budget_request
            SET form_type_id = %s
            WHERE id = %s
            """,
            (form_type_id, request_id),
        )

    _logger.info(
        "Set form_type_id on %s existing departmental budget requests",
        len(request_ids),
    )
