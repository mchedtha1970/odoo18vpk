# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute(
        """
        ALTER TABLE ebidding_plan
            ALTER COLUMN fiscal_year TYPE varchar
            USING fiscal_year::varchar
        """
    )
    cr.execute(
        """
        ALTER TABLE ebidding_plan_line
            ALTER COLUMN fiscal_year TYPE varchar
            USING fiscal_year::varchar
        """
    )
