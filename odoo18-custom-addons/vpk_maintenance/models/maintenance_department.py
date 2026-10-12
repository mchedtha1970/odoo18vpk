# -*- coding: utf-8 -*-
from odoo import fields, models


class MaintenanceDepartment(models.Model):
    _name = "maintenance.department"
    _description = "หน่วยงานแจ้งซ่อม"
    _order = "name, id"

    name = fields.Char(string="หน่วยงาน", required=True, translate=True)
    active = fields.Boolean(default=True)
