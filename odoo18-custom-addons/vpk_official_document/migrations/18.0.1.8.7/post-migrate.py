# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    from odoo.addons.vpk_official_document.hooks import (
        align_official_document_saraban_numbers,
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    align_official_document_saraban_numbers(env)
