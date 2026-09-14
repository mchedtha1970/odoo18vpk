# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Migrate legacy done → received; ensure warehouse analytic exists."""
    env.cr.execute(
        """
        UPDATE vpk_asset_transfer
           SET state = 'received'
         WHERE state = 'done'
        """
    )
    env["account.asset"]._get_warehouse_analytic_account()
