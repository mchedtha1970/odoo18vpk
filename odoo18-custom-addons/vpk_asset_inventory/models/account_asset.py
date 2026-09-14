# -*- coding: utf-8 -*-
from urllib.parse import quote

from odoo import models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    def get_inventory_qr_value(self):
        """Absolute /ai/<number> URL so phone camera opens inventory count."""
        self.ensure_one()
        number = (self.number or "").strip()
        if not number:
            return ""
        base = self.get_base_url().rstrip("/")
        return f"{base}/ai/{quote(number, safe='')}"
