# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'ebidding_plan_line'
           AND column_name = 'expected_announce_month'
        """
    )
    row = cr.fetchone()
    if not row or row[0] == "date":
        return
    cr.execute(
        """
        ALTER TABLE ebidding_plan_line
            ALTER COLUMN expected_announce_month TYPE date
            USING CASE
                WHEN expected_announce_month ~ '^(0[1-9]|1[0-2])[0-9]{4}$'
                THEN make_date(
                    substring(expected_announce_month FROM 3 FOR 4)::integer - 543,
                    substring(expected_announce_month FROM 1 FOR 2)::integer,
                    1
                )
                WHEN expected_announce_month ~ '^(0?[1-9]|1[0-2])/[0-9]{4}$'
                THEN make_date(
                    split_part(expected_announce_month, '/', 2)::integer
                        - CASE
                            WHEN split_part(expected_announce_month, '/', 2)::integer >= 2400
                            THEN 543
                            ELSE 0
                          END,
                    split_part(expected_announce_month, '/', 1)::integer,
                    1
                )
                ELSE NULL
            END
        """
    )
