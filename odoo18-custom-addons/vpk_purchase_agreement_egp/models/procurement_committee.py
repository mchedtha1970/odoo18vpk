# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class ProcurementCommittee(models.Model):
    _inherit = "procurement.committee"

    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ e-GP",
        ondelete="cascade",
        index=True,
    )

    def init(self):
        super().init()
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            procurement_committee_employee_requisition_type_uniq
            ON procurement_committee (employee_id, requisition_id, committee_type)
            WHERE requisition_id IS NOT NULL AND employee_id IS NOT NULL
            """
        )

    @api.model_create_multi
    def create(self, vals_list):
        last_by_key = {}
        key_order = []
        remaining = []
        for vals in vals_list:
            requisition_id = vals.get("requisition_id")
            employee_id = vals.get("employee_id")
            committee_type = vals.get("committee_type")
            if requisition_id and employee_id and committee_type:
                key = (int(requisition_id), int(employee_id), committee_type)
                if key not in last_by_key:
                    key_order.append(key)
                last_by_key[key] = vals
            else:
                remaining.append(vals)

        records = self.browse()
        to_create = []
        for key in key_order:
            vals = last_by_key[key]
            existing = self.search(
                [
                    ("requisition_id", "=", key[0]),
                    ("employee_id", "=", key[1]),
                    ("committee_type", "=", key[2]),
                ],
                limit=1,
            )
            if existing:
                write_vals = {
                    name: value
                    for name, value in vals.items()
                    if name != "requisition_id"
                }
                if write_vals:
                    existing.write(write_vals)
                records |= existing
            else:
                to_create.append(vals)
        to_create.extend(remaining)
        if to_create:
            records |= super().create(to_create)
        return records
