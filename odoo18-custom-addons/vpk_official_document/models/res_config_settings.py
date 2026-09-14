# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    official_doc_agency = fields.Char(
        related="company_id.official_doc_agency",
        readonly=False,
    )
    official_doc_signer_id = fields.Many2one(
        related="company_id.official_doc_signer_id",
        readonly=False,
    )
    official_doc_signer_name = fields.Char(
        related="company_id.official_doc_signer_name",
        readonly=False,
    )
    official_doc_signer_position = fields.Char(
        related="company_id.official_doc_signer_position",
        readonly=False,
    )
    official_doc_head_officer_id = fields.Many2one(
        related="company_id.official_doc_head_officer_id",
        readonly=False,
    )
    official_doc_head_officer_name = fields.Char(
        related="company_id.official_doc_head_officer_name",
        readonly=False,
    )
    official_doc_head_officer_position = fields.Char(
        related="company_id.official_doc_head_officer_position",
        readonly=False,
    )
    official_doc_officer_id = fields.Many2one(
        related="company_id.official_doc_officer_id",
        readonly=False,
    )
    official_doc_officer_name = fields.Char(
        related="company_id.official_doc_officer_name",
        readonly=False,
    )
    official_doc_officer_position = fields.Char(
        related="company_id.official_doc_officer_position",
        readonly=False,
    )
