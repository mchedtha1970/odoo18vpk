# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class HisUnitMap(models.Model):
    _name = "vpk.his.unit.map"
    _description = "HIS Service Unit Mapping"
    _order = "his_code"
    _check_company_auto = True

    name = fields.Char(required=True)
    his_code = fields.Char(
        required=True,
        index=True,
        help="รหัสหรือชื่อหน่วยบริการฝั่ง HIS เช่น หอผู้ป่วยใน 3",
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        required=True,
        check_company=True,
        ondelete="restrict",
    )
    location_id = fields.Many2one(
        "stock.location",
        check_company=True,
        domain="[('usage', '=', 'internal')]",
        help="ว่าง = ใช้ Stock ของคลัง",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "uniq_his_code_company",
            "unique(his_code, company_id)",
            "Unit mapping must be unique per HIS code and company.",
        ),
    ]

    @api.onchange("warehouse_id")
    def _onchange_warehouse_id(self):
        if self.location_id and self.warehouse_id and self.warehouse_id.lot_stock_id:
            stock = self.warehouse_id.lot_stock_id
            loc = self.location_id
            if loc != stock and not loc.parent_path.startswith(stock.parent_path or ""):
                self.location_id = False

    @api.model
    def find_map(self, his_code, company=None):
        code = (his_code or "").strip()
        if not code:
            return self.browse()
        company = company or self.env.company
        rec = self.search(
            [
                ("his_code", "=", code),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )
        if rec:
            return rec
        return self.search(
            [
                ("his_code", "=ilike", code),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )
