# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    vendor_bill_unique_key = fields.Char(
        string="คีย์ตรวจเลขที่ใบวางบิลซ้ำ",
        index=True,
        copy=False,
    )
    vendor_bill_duplicate_ids = fields.Many2many(
        comodel_name="account.move",
        string="ใบวางบิลเลขที่ซ้ำ",
        compute="_compute_vendor_bill_duplicate_ids",
    )

    _sql_constraints = [
        (
            "vendor_bill_ref_unique_per_vendor_company",
            "unique(company_id, commercial_partner_id, vendor_bill_unique_key)",
            "เลขที่ใบวางบิลนี้ถูกใช้แล้วสำหรับผู้จำหน่ายและบริษัทนี้",
        ),
    ]

    @api.model
    def _get_vendor_bill_unique_key(self, move_type, state, reference):
        if (
            move_type == "in_invoice"
            and state != "cancel"
            and reference
            and reference.strip()
        ):
            return reference.strip().casefold()
        return False

    @api.model
    def _raise_if_vendor_bill_reference_exists(
        self,
        company,
        commercial_partner,
        unique_key,
        reference,
        exclude_ids=None,
    ):
        if not unique_key or not commercial_partner:
            return
        duplicate = self.search([
            ("id", "not in", exclude_ids or [0]),
            ("move_type", "=", "in_invoice"),
            ("state", "!=", "cancel"),
            ("company_id", "=", company.id),
            ("commercial_partner_id", "=", commercial_partner.id),
            ("vendor_bill_unique_key", "=", unique_key),
        ], limit=1)
        if duplicate:
            raise ValidationError(
                _(
                    "ไม่สามารถรับเลขที่ใบวางบิลซ้ำได้\n"
                    "ผู้จำหน่าย: %(vendor)s\n"
                    "เลขที่ใบวางบิล: %(reference)s\n"
                    "พบในเอกสาร: %(document)s"
                )
                % {
                    "vendor": commercial_partner.display_name,
                    "reference": reference.strip(),
                    "document": duplicate.display_name,
                }
            )

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for values in vals_list:
            vals = dict(values)
            move_type = vals.get(
                "move_type",
                self.env.context.get("default_move_type", "entry"),
            )
            state = vals.get("state", "draft")
            reference = vals.get("ref")
            unique_key = self._get_vendor_bill_unique_key(
                move_type, state, reference
            )
            vals["vendor_bill_unique_key"] = unique_key
            company = self.env["res.company"].browse(
                vals.get("company_id") or self.env.company.id
            )
            partner = self.env["res.partner"].browse(
                vals.get("partner_id")
            ).commercial_partner_id
            self._raise_if_vendor_bill_reference_exists(
                company, partner, unique_key, reference
            )
            prepared_vals_list.append(vals)
        return super().create(prepared_vals_list)

    def write(self, vals):
        for move in self:
            move_type = vals.get("move_type", move.move_type)
            state = vals.get("state", move.state)
            reference = vals.get("ref", move.ref)
            unique_key = self._get_vendor_bill_unique_key(
                move_type, state, reference
            )
            company = self.env["res.company"].browse(
                vals.get("company_id", move.company_id.id)
            )
            partner = self.env["res.partner"].browse(
                vals.get("partner_id", move.partner_id.id)
            ).commercial_partner_id
            self._raise_if_vendor_bill_reference_exists(
                company,
                partner,
                unique_key,
                reference,
                exclude_ids=self.ids,
            )
            move_vals = dict(vals, vendor_bill_unique_key=unique_key)
            super(AccountMove, move).write(move_vals)
        return True

    @api.depends(
        "ref",
        "move_type",
        "state",
        "company_id",
        "commercial_partner_id",
    )
    def _compute_vendor_bill_duplicate_ids(self):
        for move in self:
            duplicates = self.env["account.move"]
            if (
                move.move_type == "in_invoice"
                and move.state != "cancel"
                and move.company_id
                and move.commercial_partner_id
                and move.ref
                and move.ref.strip()
            ):
                duplicates = self.search([
                    ("id", "!=", move._origin.id or 0),
                    ("move_type", "=", "in_invoice"),
                    ("state", "!=", "cancel"),
                    ("company_id", "=", move.company_id.id),
                    (
                        "commercial_partner_id",
                        "=",
                        move.commercial_partner_id.id,
                    ),
                    (
                        "vendor_bill_unique_key",
                        "=",
                        move.ref.strip().casefold(),
                    ),
                ])
            move.vendor_bill_duplicate_ids = duplicates

