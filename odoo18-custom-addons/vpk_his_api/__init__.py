# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from . import controllers
from . import models


def post_init_hook(env):
    env["vpk.his.entitlement.map"]._auto_bind()
    env["vpk.his.payment.method.map"]._auto_bind()
    env["vpk.his.entitlement.map"]._tag_entitlement_payers()
    env["vpk.his.entitlement.map"]._ensure_remittance_labels()
