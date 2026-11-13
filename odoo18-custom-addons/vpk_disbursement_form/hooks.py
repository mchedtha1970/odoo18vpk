# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).


def post_init_hook(env):
    env["res.company"]._vpk_ensure_default_disbursement_templates()
