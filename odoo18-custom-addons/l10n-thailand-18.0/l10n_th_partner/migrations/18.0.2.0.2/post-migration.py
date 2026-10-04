# Copyright 2026 VPK
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def migrate(cr, version):
    cr.execute(
        """
        UPDATE res_partner
           SET name_company = btrim(name)
         WHERE is_company
           AND COALESCE(btrim(name_company), '') = ''
           AND COALESCE(btrim(name), '') <> ''
        """
    )
