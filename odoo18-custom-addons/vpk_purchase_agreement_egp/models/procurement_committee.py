# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


CONFIRM_SELECTION = [
    ("not_sent", "ยังไม่ส่งคำขอ"),
    ("pending", "รอตอบ"),
    ("accepted", "ยินยอมแล้ว"),
    ("declined", "ไม่สามารถรับได้"),
]


class ProcurementCommittee(models.Model):
    _inherit = "procurement.committee"

    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ e-GP",
        ondelete="cascade",
        index=True,
    )
    source_confirm_state = fields.Selection(
        selection=CONFIRM_SELECTION,
        string="สถานะยินยอม",
        compute="_compute_source_confirm",
    )
    source_confirm_reply_date = fields.Datetime(
        string="วันที่ตอบคำขอยืนยัน",
        compute="_compute_source_confirm",
    )
    source_confirm_note = fields.Char(
        string="เหตุผลที่ไม่รับ",
        compute="_compute_source_confirm",
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

    def write(self, vals):
        res = super().write(vals)
        self._sync_pr_confirm_to_egp(vals)
        return res

    def _sync_pr_confirm_to_egp(self, vals):
        confirm_keys = {
            "confirm_state",
            "confirm_request_date",
            "confirm_reply_date",
            "confirm_note",
            "confirm_requested_by",
        }
        if self.env.context.get("skip_egp_confirm_sync") or not confirm_keys.intersection(
            vals
        ):
            return
        pr_lines = self.filtered(lambda rec: rec.request_id and rec.employee_id)
        if not pr_lines:
            return
        for rec in pr_lines:
            egp_lines = self.search(
                [
                    ("requisition_id.purchase_request_id", "=", rec.request_id.id),
                    ("employee_id", "=", rec.employee_id.id),
                    ("committee_type", "=", rec.committee_type),
                    ("request_id", "=", False),
                ]
            )
            if egp_lines:
                egp_lines.with_context(skip_egp_confirm_sync=True).write(
                    {
                        "confirm_state": rec.confirm_state,
                        "confirm_request_date": rec.confirm_request_date,
                        "confirm_reply_date": rec.confirm_reply_date,
                        "confirm_note": rec.confirm_note,
                        "confirm_requested_by": rec.confirm_requested_by.id,
                    }
                )

    @api.depends(
        "confirm_state",
        "confirm_reply_date",
        "confirm_note",
        "employee_id",
        "committee_type",
        "request_id",
        "requisition_id",
        "requisition_id.purchase_request_id",
    )
    def _compute_source_confirm(self):
        sources = self._pr_confirm_sources()
        for rec in self:
            source = sources.get(rec.id, rec)
            rec.source_confirm_state = source.confirm_state
            rec.source_confirm_reply_date = source.confirm_reply_date
            rec.source_confirm_note = source.confirm_note

    def _pr_confirm_sources(self):
        """Map e-GP committee rows to the matching confirmation row on the PR."""
        sources = {rec.id: rec for rec in self}
        egp_rows = self.filtered(
            lambda rec: rec.requisition_id
            and rec.requisition_id.purchase_request_id
            and rec.employee_id
            and not rec.request_id
        )
        if not egp_rows:
            return sources
        pr_ids = egp_rows.mapped("requisition_id.purchase_request_id").ids
        matches = self.search(
            [
                ("request_id", "in", pr_ids),
                ("employee_id", "in", egp_rows.mapped("employee_id").ids),
            ]
        )
        index = {
            (row.request_id.id, row.employee_id.id, row.committee_type): row
            for row in matches
        }
        for rec in egp_rows:
            key = (
                rec.requisition_id.purchase_request_id.id,
                rec.employee_id.id,
                rec.committee_type,
            )
            if key in index:
                sources[rec.id] = index[key]
        return sources
