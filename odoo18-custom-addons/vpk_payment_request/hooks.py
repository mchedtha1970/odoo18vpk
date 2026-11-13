# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).


def post_init_hook(env):
    env["account.payment.method"]._vpk_ensure_gfmis_vendor_direct_method_lines()
