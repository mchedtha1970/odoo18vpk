# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class VendorApiLog(models.Model):
    _name = "vpk.vendor.api.log"
    _description = "Vendor API Request Log"
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
            ("documents_uploaded", "Documents Uploaded"),
        ],
        string="Result Action",
    )
    http_status = fields.Integer()
    external_id = fields.Char(index=True)
    partner_id = fields.Many2one("res.partner", string="Vendor", index=True)
    error_message = fields.Text()
