from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    minimum_receipt_shelf_life_days = fields.Integer(
        related="product_id.product_tmpl_id.minimum_receipt_shelf_life_days",
        string="อายุคงเหลือขั้นต่ำ (วัน)",
        readonly=True,
    )
    receipt_shelf_life_days = fields.Integer(
        string="อายุยาคงเหลือ (วัน)",
        compute="_compute_receipt_shelf_life",
    )
    is_short_shelf_life = fields.Boolean(
        string="ยาอายุต่ำกว่าเกณฑ์",
        compute="_compute_receipt_shelf_life",
    )
    replacement_certificate = fields.Binary(
        string="ใบรับรองการเปลี่ยนยา",
        attachment=True,
        copy=False,
    )
    replacement_certificate_filename = fields.Char(
        string="ชื่อไฟล์ใบรับรอง",
        copy=False,
    )
    short_shelf_life_note = fields.Char(
        string="หมายเหตุยาอายุสั้น",
        copy=False,
    )

    @api.depends(
        "expiration_date",
        "product_id",
        "product_id.product_tmpl_id.minimum_receipt_shelf_life_days",
    )
    def _compute_receipt_shelf_life(self):
        today = fields.Date.context_today(self)
        for line in self:
            expiration_date = (
                fields.Datetime.to_datetime(line.expiration_date).date()
                if line.expiration_date
                else False
            )
            remaining_days = (
                (expiration_date - today).days if expiration_date else 0
            )
            line.receipt_shelf_life_days = remaining_days
            line.is_short_shelf_life = bool(
                expiration_date
                and line.minimum_receipt_shelf_life_days > 0
                and remaining_days
                < line.minimum_receipt_shelf_life_days
            )

    @api.model
    def _vpk_get_matching_picking_move(self, picking, product=None):
        moves = picking.move_ids.filtered(
            lambda move: move.state != "cancel"
            and (not product or move.product_id == product)
        )
        return moves if len(moves) == 1 else self.env["stock.move"]

    @api.model
    def _vpk_apply_move_defaults(self, values, move):
        values.update({
            "move_id": move.id,
            "product_id": move.product_id.id,
            "product_uom_id": move.product_uom.id,
            "location_id": move.location_id.id,
            "location_dest_id": move.location_dest_id.id,
        })

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if not self.env.context.get("vpk_detailed_lot_entry"):
            return values
        picking = self.env["stock.picking"].browse(
            self.env.context.get("default_picking_id")
        )
        if picking and not values.get("move_id"):
            move = self._vpk_get_matching_picking_move(picking)
            if move:
                self._vpk_apply_move_defaults(values, move)
        return values

    @api.onchange("product_id", "picking_id")
    def _onchange_vpk_detailed_lot_product(self):
        if (
            self.env.context.get("vpk_detailed_lot_entry")
            and self.picking_id
            and self.product_id
            and not self.move_id
        ):
            move = self._vpk_get_matching_picking_move(
                self.picking_id, self.product_id
            )
            if move:
                self.move_id = move
                self.product_uom_id = move.product_uom
                self.location_id = move.location_id
                self.location_dest_id = move.location_dest_id

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("vpk_detailed_lot_entry"):
            for values in vals_list:
                if values.get("move_id") or not values.get("picking_id"):
                    continue
                picking = self.env["stock.picking"].browse(
                    values["picking_id"]
                )
                product = self.env["product.product"].browse(
                    values.get("product_id")
                )
                move = self._vpk_get_matching_picking_move(
                    picking, product=product
                )
                if move:
                    self._vpk_apply_move_defaults(values, move)
        return super().create(vals_list)
