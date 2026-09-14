from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    vpk_replenishment_source_wh_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="คลังเติมสต็อกหลัก",
        check_company=True,
        domain="[('company_id', '=', company_id)]",
        help="เมื่อสต็อกต่ำกว่า Min ระบบจะดึงจากคลังนี้ก่อน หากไม่พอจึงเปิด PR",
    )

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        warehouses._vpk_sync_resupply_from_source()
        return warehouses

    def write(self, vals):
        res = super().write(vals)
        if "vpk_replenishment_source_wh_id" in vals:
            self._vpk_sync_resupply_from_source()
        return res

    def _vpk_sync_resupply_from_source(self):
        for warehouse in self:
            source_wh = warehouse.vpk_replenishment_source_wh_id
            if not source_wh:
                continue
            if source_wh not in warehouse.resupply_wh_ids:
                warehouse.resupply_wh_ids = [(4, source_wh.id)]

    def _vpk_get_resupply_route(self, source_wh):
        self.ensure_one()
        return self.resupply_route_ids.filtered(
            lambda route: route.supplier_wh_id == source_wh
        )[:1]

    @api.constrains("vpk_replenishment_source_wh_id")
    def _check_vpk_replenishment_source_wh(self):
        for warehouse in self:
            if warehouse.vpk_replenishment_source_wh_id == warehouse:
                raise ValidationError(
                    _("คลังเติมสต็อกหลักต้องไม่ใช่คลังเดียวกัน")
                )
