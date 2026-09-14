# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero

from .his_entitlement_map import ITEM_TYPES, SERVICE_TYPES

LINE_STATES = [
    ("ok", "OK"),
    ("error", "Error"),
]


class HisSaleLine(models.Model):
    _name = "vpk.his.sale.line"
    _description = "HIS Revenue Sale Line"
    _order = "id"

    batch_id = fields.Many2one(
        "vpk.his.batch", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="batch_id.company_id", store=True)
    line_external_id = fields.Char(index=True)
    entitlement_code = fields.Char(required=True)
    entitlement_map_id = fields.Many2one("vpk.his.entitlement.map", ondelete="set null")
    service_type = fields.Selection(
        [s for s in SERVICE_TYPES if s[0] != "both"],
        required=True,
        default="op",
    )
    item_type = fields.Selection(ITEM_TYPES, required=True, default="service")
    department_code = fields.Char()
    ticket_external_id = fields.Char(
        index=True,
        help="รหัสใบรับบริการ/ใบเสร็จ POS ของคนไข้ ใช้เมื่อจ่ายหลายสิทธิ์ในใบเดียว",
    )
    qty = fields.Float(default=1.0, digits="Product Unit of Measure")
    amount_untaxed = fields.Monetary()
    amount_tax = fields.Monetary()
    amount_total = fields.Monetary(required=True)
    currency_id = fields.Many2one(related="batch_id.currency_id")
    income_account_code = fields.Char()
    income_account_id = fields.Many2one("account.account")
    invoice_id = fields.Many2one("account.move", string="Invoice", ondelete="set null")
    line_state = fields.Selection(LINE_STATES, default="ok")
    error_message = fields.Text()

    def _validate_line(self):
        self.ensure_one()
        errors = []
        Map = self.env["vpk.his.entitlement.map"]
        mapping = Map.find_map(
            self.entitlement_code,
            service_type=self.service_type,
            item_type=self.item_type if self.item_type != "all" else "all",
            company=self.company_id,
        )
        self.entitlement_map_id = mapping.id if mapping else False
        if not mapping:
            errors.append(
                _("No entitlement mapping for %s / %s")
                % (self.entitlement_code, self.service_type)
            )
        account = self.env["account.account"]
        if self.income_account_code:
            account = Map._find_account_by_code(self.income_account_code)
            if not account:
                errors.append(
                    _("Unknown income account code %s") % self.income_account_code
                )
        elif mapping and mapping.income_account_id:
            account = mapping.income_account_id
        elif mapping:
            errors.append(
                _("Entitlement %s has no income account") % self.entitlement_code
            )
        self.income_account_id = account.id if account else False
        if float_is_zero(self.amount_total, precision_digits=2) and float_is_zero(
            self.amount_untaxed, precision_digits=2
        ):
            errors.append(_("Sale amount_total must not be zero"))
        self.line_state = "error" if errors else "ok"
        self.error_message = "\n".join(errors) if errors else False
        return not errors
