# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class HisApiLog(models.Model):
    _name = "vpk.his.api.log"
    _description = "HIS API Request Log"
    _order = "create_date desc, id desc"

    endpoint = fields.Char(required=True)
    http_method = fields.Char(default="POST")
    remote_addr = fields.Char(string="Remote IP")
    request_body = fields.Text()
    response_body = fields.Text()
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("success", "Success"),
            ("error", "Error"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    action = fields.Selection(
        [
            ("created", "Created"),
            ("updated", "Updated"),
            ("ingested", "Ingested"),
            ("unchanged", "Idempotent Replay"),
            ("lookup", "Lookup"),
            ("error", "Error"),
        ],
        string="Result Action",
    )
    http_status = fields.Integer()
    external_id = fields.Char(index=True)
    source_system = fields.Char(index=True)
    batch_id = fields.Many2one("vpk.his.batch", index=True, ondelete="set null")
    error_message = fields.Text()
