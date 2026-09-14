from odoo import api, fields, models


class ProcurementCommittee(models.Model):
    _inherit = "procurement.committee"

    committee_type = fields.Selection(
        selection_add=[
            ("price_mid", "คณะกรรมการกำหนดราคากลาง"),
        ],
        ondelete={
            "price_mid": lambda recs: recs.write({"committee_type": "procurement"}),
        },
    )
    approve_role = fields.Selection(
        selection_add=[
            ("secretary", "เลขานุการ"),
        ],
        ondelete={
            "secretary": lambda recs: recs.write({"approve_role": "committee"}),
        },
    )
    _sql_constraints = [
        (
            "employee_request_uniq",
            "unique(employee_id, request_id, committee_type)",
            "คนเดียวกันห้ามซ้ำในคณะกรรมการชุดเดียวกัน",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Reuse an existing row when the form resends a saved member as a new line."""
        last_by_key = {}
        key_order = []
        incomplete = []
        for vals in vals_list:
            request_id = vals.get("request_id")
            employee_id = vals.get("employee_id")
            committee_type = vals.get("committee_type")
            if request_id and employee_id and committee_type:
                key = (int(request_id), int(employee_id), committee_type)
                if key not in last_by_key:
                    key_order.append(key)
                last_by_key[key] = vals
            else:
                incomplete.append(vals)

        records = self.browse()
        to_create = []
        for key in key_order:
            vals = last_by_key[key]
            existing = self.search(
                [
                    ("request_id", "=", key[0]),
                    ("employee_id", "=", key[1]),
                    ("committee_type", "=", key[2]),
                ],
                limit=1,
            )
            if existing:
                write_vals = {name: value for name, value in vals.items() if name != "request_id"}
                if write_vals:
                    existing.write(write_vals)
                records |= existing
            else:
                to_create.append(vals)
        to_create.extend(incomplete)
        if to_create:
            records |= super().create(to_create)
        return records
