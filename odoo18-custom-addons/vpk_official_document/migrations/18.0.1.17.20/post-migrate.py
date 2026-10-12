# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    documents = env["vpk.official.document"].sudo().search(
        [("state", "=", "to_approve")]
    )
    documents._vpk_insert_secretary_before_director()
