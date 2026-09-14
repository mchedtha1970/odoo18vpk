# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    maintenance_request_id = fields.Many2one(
        comodel_name="maintenance.request",
        string="คำขอซ่อมบำรุง",
        index=True,
        copy=False,
        check_company=True,
        ondelete="set null",
    )
