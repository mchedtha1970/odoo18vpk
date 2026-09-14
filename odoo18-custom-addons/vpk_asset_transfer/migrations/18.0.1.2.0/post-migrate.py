# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute(
        """
        UPDATE vpk_asset_transfer
           SET state = 'received'
         WHERE state = 'done'
        """
    )
