# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class VpkVendorLoan(models.Model):
    _name = "vpk.vendor.loan"
    _description = "ยืมของจากผู้ขาย"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่",
        required=True,
        copy=False,
        default=lambda self: _("ใหม่"),
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="ผู้ขาย",
        required=True,
        tracking=True,
        domain=[("supplier_rank", ">", 0)],
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="คลังที่รับของ",
        required=True,
        default=lambda self: self.env["stock.warehouse"]._vpk_central_warehouse(),
        tracking=True,
    )
    location_dest_id = fields.Many2one(
        "stock.location",
        string="คลังยืม",
        required=True,
        domain="[('usage', '=', 'internal')]",
        default=lambda self: self.env["vpk.vendor.loan"]._vpk_loan_stock_location(),
        tracking=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="สกุลเงิน",
    )
    amount_total = fields.Monetary(
        string="มูลค่าที่จะซื้อภายหลัง",
        currency_field="currency_id",
        compute="_compute_amount_total",
        store=True,
    )
    date = fields.Date(
        string="วันที่ต้องการ",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    reason = fields.Text(
        string="เหตุผลที่ต้องยืมด่วน",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "ร่าง"),
            ("received", "รับของยืมแล้ว"),
            ("purchasing", "เปิดขอซื้อแล้ว"),
            ("cleared", "หักล้างแล้ว"),
            ("cancel", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        "vpk.vendor.loan.line",
        "loan_id",
        string="รายการยืม",
        copy=True,
    )
    picking_ids = fields.One2many(
        "stock.picking",
        "vpk_vendor_loan_id",
        string="ใบรับของยืม",
        copy=False,
    )
    picking_count = fields.Integer(compute="_compute_picking_count")
    purchase_request_id = fields.Many2one(
        "purchase.request",
        string="ใบขอซื้อ",
        copy=False,
        tracking=True,
    )
    note = fields.Text(string="หมายเหตุ")

    @api.depends("picking_ids")
    def _compute_picking_count(self):
        for loan in self:
            loan.picking_count = len(loan.picking_ids)

    @api.depends("line_ids.price_subtotal")
    def _compute_amount_total(self):
        for loan in self:
            loan.amount_total = sum(loan.line_ids.mapped("price_subtotal"))

    @api.model
    def _vpk_loan_stock_location(self):
        return self.env.ref(
            "vpk_vendor_loan.location_vendor_loan_stock",
            raise_if_not_found=False,
        )

    @api.onchange("warehouse_id")
    def _onchange_warehouse_id(self):
        location = self._vpk_loan_stock_location()
        if location:
            self.location_dest_id = location

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("ใหม่")) == _("ใหม่"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.vendor.loan") or _("ใหม่")
                )
            if not vals.get("location_dest_id"):
                location = self._vpk_loan_stock_location()
                if location:
                    vals["location_dest_id"] = location.id
        return super().create(vals_list)

    def unlink(self):
        if any(loan.state != "draft" for loan in self):
            raise UserError(_("ลบได้เฉพาะใบยืมสถานะร่าง"))
        return super().unlink()

    @api.model
    def _vpk_ensure_loan_location(self, warehouse):
        """คลังภายในสำหรับของยืม แยกจากคลังปกติ เพื่อให้รับซื้อตามหลังและหักล้างในที่เดียวกัน"""
        location = self._vpk_loan_stock_location()
        if not location or not warehouse or not warehouse.view_location_id:
            return location
        location.sudo().write(
            {
                "name": "คลังยืมผู้ขาย",
                "usage": "internal",
                "location_id": warehouse.view_location_id.id,
                "company_id": warehouse.company_id.id,
            }
        )
        return location

    @api.model
    def _vpk_configure_vendor_loan_type(self):
        """ประเภทปฏิบัติการรับของยืมของคลังกลาง แยกจากใบรับปกติเพื่อไม่ติดขั้นตอนตรวจคุณภาพ"""
        warehouse = self.env["stock.warehouse"]._vpk_central_warehouse()
        if not warehouse or not warehouse.lot_stock_id:
            return False
        supplier = self.env.ref("stock.stock_location_suppliers", raise_if_not_found=False)
        loan_location = self._vpk_ensure_loan_location(warehouse)
        picking_type = self.env["stock.picking.type"].search(
            [
                ("warehouse_id", "=", warehouse.id),
                ("sequence_code", "=", "LOAN"),
            ],
            limit=1,
        )
        vals = {
            "name": "รับของยืม",
            "code": "incoming",
            "sequence_code": "LOAN",
            "warehouse_id": warehouse.id,
            "company_id": warehouse.company_id.id,
            "default_location_src_id": supplier.id if supplier else False,
            "default_location_dest_id": loan_location.id,
            "use_existing_lots": True,
            "use_create_lots": True,
            "show_operations": True,
        }
        if picking_type:
            picking_type.write(vals)
        else:
            sequence = self.env["ir.sequence"].create(
                {
                    "name": "รับของยืม %s" % warehouse.name,
                    "prefix": warehouse.code + "/LOAN/",
                    "padding": 5,
                    "company_id": warehouse.company_id.id,
                }
            )
            vals["sequence_id"] = sequence.id
            self.env["stock.picking.type"].create(vals)
        return True

    def _vpk_loan_picking_type(self):
        self.ensure_one()
        warehouse = self.warehouse_id or self.env["stock.warehouse"]._vpk_central_warehouse()
        picking_type = self.env["stock.picking.type"].search(
            [("warehouse_id", "=", warehouse.id), ("sequence_code", "=", "LOAN")],
            limit=1,
        )
        if not picking_type:
            # สร้างประเภทปฏิบัติการครั้งแรกด้วยสิทธิ์ระบบ ผู้ใช้คลังไม่มีสิทธิ์แก้ stock.picking.type
            self.sudo()._vpk_configure_vendor_loan_type()
            picking_type = self.env["stock.picking.type"].search(
                [("warehouse_id", "=", warehouse.id), ("sequence_code", "=", "LOAN")],
                limit=1,
            )
        if not picking_type:
            raise UserError(_("ยังไม่มีประเภทปฏิบัติการรับของยืมของคลังนี้"))
        return picking_type

    def action_receive(self):
        """เปิดใบรับของยืม ให้คลังตรวจจำนวนแล้วกดตรวจสอบ"""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("รับของยืมได้เฉพาะใบสถานะร่าง"))
        if not self.line_ids:
            raise UserError(_("ใส่รายการสินค้าที่จะยืมก่อน"))
        missing_cost = self.line_ids.filtered(
            lambda line: float_compare(line.price_unit, 0.0, precision_digits=2) <= 0
        )
        if missing_cost:
            raise UserError(
                _(
                    "ใส่ต้นทุนที่จะซื้อมาหักล้างของ %s "
                    "ถ้าว่างไว้แล้วของถูกใช้ก่อนใบรับที่ซื้อตามหลัง ต้นทุนจะเป็น 0"
                )
                % ", ".join(missing_cost.mapped("product_id.display_name"))
            )
        if not self.location_dest_id:
            self.location_dest_id = self._vpk_loan_stock_location()
        open_picking = self.picking_ids.filtered(lambda picking: picking.state not in ("done", "cancel"))
        if open_picking:
            return self._action_open_pickings(open_picking[:1])
        picking_type = self._vpk_loan_picking_type()
        supplier_loc = self.partner_id.property_stock_supplier
        if not supplier_loc:
            raise UserError(_("ผู้ขายนี้ยังไม่มีตำแหน่งรับจากผู้ขาย"))
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": supplier_loc.id,
                "location_dest_id": self.location_dest_id.id,
                "origin": self.name,
                "vpk_vendor_loan_id": self.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": line.product_id.display_name,
                            "product_id": line.product_id.id,
                            "product_uom": line.product_uom_id.id,
                            "product_uom_qty": line.product_qty,
                            "location_id": supplier_loc.id,
                            "location_dest_id": self.location_dest_id.id,
                            "company_id": self.company_id.id,
                            "price_unit": line.product_uom_id._compute_price(
                                line.price_unit, line.product_id.uom_id
                            ),
                        },
                    )
                    for line in self.line_ids
                ],
            }
        )
        picking.action_confirm()
        return self._action_open_pickings(picking)

    def action_open_purchase_request(self):
        """เปิดใบขอซื้อร่าง ให้เดินอนุมัติและ e-GP ตามรายการปกติ"""
        self.ensure_one()
        if self.purchase_request_id:
            return self._action_open_request()
        if self.state not in ("received", "purchasing"):
            raise UserError(_("รับของยืมเข้าคลังก่อน แล้วค่อยเปิดขอซื้อ"))
        lines = self.line_ids.filtered(
            lambda line: float_compare(
                line.qty_received, 0, precision_rounding=line.product_uom_id.rounding
            )
            > 0
        )
        if not lines:
            raise UserError(_("ยังไม่มีจำนวนที่รับเข้าจากใบยืม"))
        warehouse = self.warehouse_id
        picking_type = warehouse.in_type_id
        if not picking_type:
            raise UserError(_("คลังนี้ยังไม่มีประเภทใบรับสินค้าสำหรับเปิดขอซื้อ"))
        # ผู้ใช้คลังเปิดใบขอซื้อร่างได้ แม้ไม่มีสิทธิ์สร้างใบขอซื้อเอง ฝ่ายพัสดุเดินอนุมัติต่อ
        request = self.env["purchase.request"].sudo().create(
            {
                "origin": self.name,
                "description": self.reason,
                "requested_by": self.env.user.id,
                "company_id": self.company_id.id,
                "picking_type_id": picking_type.id,
                "urgency_level": "urgent",
                "urgency_reason": self.reason,
                "urgency_needed_date": self.date,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "name": line.product_id.display_name,
                            "product_qty": line.qty_received,
                            "product_uom_id": line.product_uom_id.id,
                            "date_required": self.date,
                            "estimated_cost": line.price_unit * line.qty_received,
                        },
                    )
                    for line in lines
                ],
            }
        )
        self.write({"purchase_request_id": request.id, "state": "purchasing"})
        self.message_post(
            body=_("เปิดใบขอซื้อ %s เพื่อจัดซื้อตามหลังรายการยืมนี้") % request.name
        )
        return self._action_open_request()

    def action_view_pickings(self):
        self.ensure_one()
        return self._action_open_pickings(self.picking_ids)

    def action_view_purchase_request(self):
        self.ensure_one()
        return self._action_open_request()

    def action_cancel(self):
        for loan in self:
            if loan.state not in ("draft", "received"):
                raise UserError(_("ยกเลิกใบ %s ไม่ได้ในสถานะนี้") % loan.name)
            if loan.purchase_request_id:
                raise UserError(_("ใบ %s เปิดขอซื้อแล้ว ยกเลิกใบขอซื้อก่อน") % loan.name)
            open_pickings = loan.picking_ids.filtered(
                lambda picking: picking.state not in ("done", "cancel")
            )
            if open_pickings:
                open_pickings.action_cancel()
            done = loan.picking_ids.filtered(lambda picking: picking.state == "done")
            if done:
                raise UserError(
                    _("ใบ %s รับของเข้าคลังแล้ว ต้องคืนของก่อนยกเลิก") % loan.name
                )
            loan.state = "cancel"
        return True

    def _vpk_mark_received_from_pickings(self):
        for loan in self.filtered(lambda item: item.state == "draft"):
            if any(
                float_compare(
                    line.qty_received, 0, precision_rounding=line.product_uom_id.rounding
                )
                > 0
                for line in loan.line_ids
            ):
                loan.state = "received"

    def _vpk_refresh_clear_state(self):
        for loan in self.filtered(lambda item: item.state in ("received", "purchasing")):
            if not loan.line_ids:
                continue
            cleared = all(
                float_compare(
                    line.qty_remaining,
                    0,
                    precision_rounding=line.product_uom_id.rounding,
                )
                <= 0
                and not float_is_zero(
                    line.qty_received, precision_rounding=line.product_uom_id.rounding
                )
                for line in loan.line_ids
            )
            if cleared:
                loan.state = "cleared"

    def _action_open_pickings(self, pickings):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_incoming"
        )
        action["domain"] = [("id", "in", pickings.ids)]
        if len(pickings) == 1:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = pickings.id
        return action

    def _action_open_request(self):
        self.ensure_one()
        if not self.env.user.has_group("purchase_request.group_purchase_request_user"):
            # บัญชีคลังสร้างใบขอซื้อได้ แต่ฟอร์มใบขอซื้อมีข้อมูลคณะกรรมการที่เปิดได้เฉพาะฝ่ายพัสดุ
            return {
                "type": "ir.actions.act_window",
                "name": _("ยืมของจากผู้ขาย"),
                "res_model": "vpk.vendor.loan",
                "res_id": self.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบขอซื้อ"),
            "res_model": "purchase.request",
            "res_id": self.purchase_request_id.id,
            "view_mode": "form",
            "target": "current",
        }


class VpkVendorLoanLine(models.Model):
    _name = "vpk.vendor.loan.line"
    _description = "รายการยืมของจากผู้ขาย"

    loan_id = fields.Many2one(
        "vpk.vendor.loan",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="สินค้า",
        required=True,
        domain=[("purchase_ok", "=", True)],
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="หน่วย",
        required=True,
    )
    product_qty = fields.Float(
        string="จำนวนยืม",
        digits="Product Unit of Measure",
        required=True,
        default=1.0,
    )
    qty_received = fields.Float(
        string="รับแล้ว",
        digits="Product Unit of Measure",
        compute="_compute_qty_received",
        store=True,
    )
    qty_cleared = fields.Float(
        string="หักล้างแล้ว",
        digits="Product Unit of Measure",
        default=0.0,
        copy=False,
    )
    qty_remaining = fields.Float(
        string="คงค้างยืม",
        digits="Product Unit of Measure",
        compute="_compute_qty_remaining",
        store=True,
    )
    company_id = fields.Many2one(related="loan_id.company_id", store=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    price_unit = fields.Monetary(
        string="ต้นทุนที่จะซื้อภายหลัง",
        currency_field="currency_id",
        help="ราคาต่อหน่วยของของที่จะซื้อมาหักล้าง "
        "ระบบใช้เป็นต้นทุนตอนรับของยืม "
        "ถ้าเว้นว่างแล้วของถูกใช้ก่อนใบรับที่ซื้อตามหลัง ต้นทุนจะเป็น 0",
    )
    price_subtotal = fields.Monetary(
        string="มูลค่าที่จะซื้อ",
        currency_field="currency_id",
        compute="_compute_price_subtotal",
        store=True,
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            self.price_unit = self.product_id.standard_price

    @api.depends("product_qty", "price_unit")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_qty * line.price_unit

    @api.depends(
        "product_id",
        "product_uom_id",
        "loan_id.picking_ids.state",
        "loan_id.picking_ids.move_ids.state",
        "loan_id.picking_ids.move_ids.quantity",
        "loan_id.picking_ids.move_ids.product_id",
        "loan_id.picking_ids.move_ids.product_uom",
    )
    def _compute_qty_received(self):
        for line in self:
            qty = 0.0
            if not line.product_id or not line.product_uom_id:
                line.qty_received = 0.0
                continue
            moves = line.loan_id.picking_ids.move_ids.filtered(
                lambda move: move.state == "done" and move.product_id == line.product_id
            )
            for move in moves:
                qty += move.product_uom._compute_quantity(
                    move.quantity, line.product_uom_id
                )
            line.qty_received = qty

    @api.depends("qty_received", "qty_cleared")
    def _compute_qty_remaining(self):
        for line in self:
            line.qty_remaining = max(line.qty_received - line.qty_cleared, 0.0)

    @api.constrains("product_qty")
    def _check_product_qty(self):
        for line in self:
            if (
                line.product_uom_id
                and float_compare(
                    line.product_qty, 0, precision_rounding=line.product_uom_id.rounding
                )
                <= 0
            ):
                raise UserError(_("จำนวนยืมต้องมากกว่าศูนย์"))
