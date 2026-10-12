from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockQuantCountSheet(models.Model):
    _name = "stock.quant.count.sheet"
    _description = "ใบนับสต็อกที่เปิดไว้"
    _order = "id desc"

    name = fields.Char(required=True, copy=False, default=lambda self: _("ใหม่"))
    state = fields.Selection(
        [("open", "เปิดนับ"), ("done", "ปิดแล้ว")],
        default="open",
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="ผู้เปิดใบนับ",
        default=lambda self: self.env.user,
        required=True,
    )
    line_ids = fields.One2many(
        "stock.quant.count.sheet.line",
        "sheet_id",
        string="รายการนับ",
    )
    line_count = fields.Integer(compute="_compute_progress")
    counted_count = fields.Integer(compute="_compute_progress")

    @api.depends("line_ids.counted")
    def _compute_progress(self):
        for sheet in self:
            sheet.line_count = len(sheet.line_ids)
            sheet.counted_count = len(sheet.line_ids.filtered("counted"))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("ใหม่"):
                vals["name"] = sequence.next_by_code("vpk.stock.quant.count.sheet") or _("ใหม่")
        return super().create(vals_list)

    def action_close(self):
        self.filtered(lambda sheet: sheet.state == "open").write({"state": "done"})
        return True


class StockQuantCountSheetLine(models.Model):
    _name = "stock.quant.count.sheet.line"
    _description = "รายการในใบนับสต็อก"
    _order = "location_id, product_id, lot_id, id"

    sheet_id = fields.Many2one(
        "stock.quant.count.sheet",
        required=True,
        ondelete="cascade",
        index=True,
    )
    quant_id = fields.Many2one("stock.quant", string="รายการสต็อก", required=True, ondelete="cascade")
    product_id = fields.Many2one(related="quant_id.product_id", store=True)
    location_id = fields.Many2one(related="quant_id.location_id", store=True)
    lot_id = fields.Many2one(related="quant_id.lot_id", store=True)
    uom_id = fields.Many2one(related="quant_id.product_uom_id")
    system_qty = fields.Float(related="quant_id.quantity", string="ยอดในระบบ")
    counted_qty = fields.Float(string="จำนวนที่นับได้", digits="Product Unit of Measure")
    counted = fields.Boolean(string="นับแล้ว")

    def write(self, vals):
        if "counted_qty" in vals:
            if vals["counted_qty"] < 0:
                raise UserError(_("จำนวนที่นับได้ต้องไม่ติดลบ"))
            vals = dict(vals, counted=True)
        result = super().write(vals)
        if "counted_qty" in vals:
            self._push_count_to_quant()
        return result

    def _push_count_to_quant(self):
        for line in self:
            if line.sheet_id.state != "open":
                raise UserError(_("ใบนับ %s ปิดแล้ว") % line.sheet_id.name)
            line.quant_id.with_context(inventory_mode=True).write({
                "inventory_quantity": line.counted_qty,
                "inventory_quantity_set": True,
            })

    def action_mobile_add(self, qty=1.0):
        """บวกจำนวนจากกล้องสแกน แล้วเขียนกลับลงใบนับที่เปิดอยู่"""
        step = float(qty or 0.0)
        for line in self:
            base = line.counted_qty if line.counted else 0.0
            line.counted_qty = base + step
        return True

    def action_mobile_set(self, qty):
        """ใส่จำนวนที่นับได้ทั้งก้อน แล้วเขียนกลับลงใบนับที่เปิดอยู่"""
        self.write({"counted_qty": float(qty or 0.0)})
        return True
