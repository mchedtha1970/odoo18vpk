# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

def migrate(cr, version):
    # Journal is created from _register_hook after the full registry is loaded
    # (base_accounting_kit columns are not on account.journal yet at this stage).
    return
