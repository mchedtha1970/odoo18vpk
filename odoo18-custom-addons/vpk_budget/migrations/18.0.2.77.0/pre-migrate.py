# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Drop product.category FK before asset_categ_id switches to budget model."""
    cr.execute(
        """
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_attribute att
          ON att.attrelid = rel.oid
         AND att.attnum = ANY (con.conkey)
        WHERE rel.relname = 'departmental_budget_request_line'
          AND con.contype = 'f'
          AND att.attname = 'asset_categ_id'
        """
    )
    for (name,) in cr.fetchall():
        cr.execute(
            'ALTER TABLE departmental_budget_request_line DROP CONSTRAINT IF EXISTS "%s"'
            % name.replace('"', "")
        )
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'departmental_budget_request_line'
          AND column_name = 'asset_categ_id'
        """
    )
    if cr.fetchone():
        cr.execute("UPDATE departmental_budget_request_line SET asset_categ_id = NULL")
    cr.execute("DROP TABLE IF EXISTS departmental_budget_request_equip_categ_rel")
    # Keep departmental_budget_request_asset_category_rel if it already has
    # request_id + asset_category_id (legacy budget-group M2M). Drop only when
    # the schema does not match, otherwise Odoo tries to add a missing FK.
    cr.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'departmental_budget_request_asset_category_rel'
        """
    )
    rel_cols = {row[0] for row in cr.fetchall()}
    if rel_cols and not {"request_id", "asset_category_id"} <= rel_cols:
        cr.execute("DROP TABLE IF EXISTS departmental_budget_request_asset_category_rel")
