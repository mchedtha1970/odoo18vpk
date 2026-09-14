import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    vendor_moq_qty = fields.Float(
        string="MOQ ผู้จำหน่าย",
        compute="_compute_vendor_moq",
        store=False,
        digits="Product Unit of Measure",
    )
    vendor_order_multiple = fields.Float(
        string="ทวีคูณ",
        compute="_compute_vendor_moq",
        store=False,
        digits="Product Unit of Measure",
    )
    moq_warning = fields.Char(
        string="คำเตือน MOQ",
        compute="_compute_moq_warning",
    )

    @api.depends("product_id", "order_id.partner_id")
    def _compute_vendor_moq(self):
        for line in self:
            si = line._get_supplierinfo()
            line.vendor_moq_qty = si.moq_qty if si else 0.0
            line.vendor_order_multiple = si.order_multiple if si else 0.0

    @api.depends("product_qty", "vendor_moq_qty", "vendor_order_multiple")
    def _compute_moq_warning(self):
        for line in self:
            warnings = []
            if line.vendor_moq_qty and line.product_qty < line.vendor_moq_qty:
                warnings.append(
                    _("จำนวนน้อยกว่า MOQ (%s)") % line.vendor_moq_qty
                )
            if (
                line.vendor_order_multiple
                and line.product_qty > 0
                and line.product_qty % line.vendor_order_multiple != 0
            ):
                suggested = (
                    math.ceil(line.product_qty / line.vendor_order_multiple)
                    * line.vendor_order_multiple
                )
                warnings.append(
                    _("ต้องสั่งเป็นทวีคูณ %s (แนะนำ: %s)")
                    % (line.vendor_order_multiple, suggested)
                )
            line.moq_warning = " | ".join(warnings) if warnings else False

    def _get_supplierinfo(self):
        """ค้นหา supplierinfo ที่ตรงกับ vendor + product ของ PO line นี้"""
        self.ensure_one()
        if not self.product_id or not self.order_id.partner_id:
            return self.env["product.supplierinfo"]
        vendor = self.order_id.partner_id
        return self.env["product.supplierinfo"].search([
            ("partner_id", "in", (vendor | vendor.commercial_partner_id).ids),
            "|",
            ("product_tmpl_id", "=", self.product_id.product_tmpl_id.id),
            ("product_id", "=", self.product_id.id),
        ], limit=1, order="product_id desc, min_qty asc")

    @api.onchange("product_qty")
    def _onchange_product_qty_moq_check(self):
        si = self._get_supplierinfo()
        if not si or not si.moq_qty:
            return
        warnings = []
        if self.product_qty < si.moq_qty:
            warnings.append(
                _("จำนวน %.2f น้อยกว่าจำนวนสั่งซื้อขั้นต่ำ (MOQ = %.2f %s) "
                  "ของผู้จำหน่ายรายนี้")
                % (
                    self.product_qty,
                    si.moq_qty,
                    si.moq_uom_id.name or self.product_uom.name or "",
                )
            )
        if (
            si.order_multiple
            and self.product_qty > 0
            and self.product_qty % si.order_multiple != 0
        ):
            suggested = (
                math.ceil(self.product_qty / si.order_multiple)
                * si.order_multiple
            )
            warnings.append(
                _("ต้องสั่งซื้อเป็นทวีคูณของ %.2f "
                  "(จำนวนที่แนะนำ: %.2f)")
                % (si.order_multiple, suggested)
            )
        if warnings:
            return {
                "warning": {
                    "title": _("คำเตือนจำนวนสั่งซื้อขั้นต่ำ"),
                    "message": "\n".join(warnings),
                    "type": "warning",
                }
            }


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        for order in self:
            moq_errors = []
            for line in order.order_line.filtered(lambda l: l.product_id):
                si = line._get_supplierinfo()
                if not si or not si.moq_qty:
                    continue
                if line.product_qty < si.moq_qty:
                    moq_errors.append(
                        _("- %(product)s: สั่ง %(qty)s แต่ MOQ = %(moq)s %(uom)s")
                        % {
                            "product": line.product_id.display_name,
                            "qty": line.product_qty,
                            "moq": si.moq_qty,
                            "uom": si.moq_uom_id.name
                            or line.product_uom.name
                            or "",
                        }
                    )
            if moq_errors:
                raise UserError(
                    _("ไม่สามารถยืนยัน PO ได้ — "
                      "จำนวนสั่งซื้อน้อยกว่าขั้นต่ำ (MOQ):\n\n%s")
                    % "\n".join(moq_errors)
                )
        return super().button_confirm()
