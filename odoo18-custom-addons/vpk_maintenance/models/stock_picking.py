# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    maintenance_request_id = fields.Many2one(
        comodel_name="maintenance.request",
        string="คำขอซ่อมบำรุง",
        index=True,
        copy=False,
        check_company=True,
        ondelete="set null",
    )
    can_validate_receipt = fields.Boolean(
        compute="_compute_receipt_permissions",
    )
    can_cancel_receipt = fields.Boolean(
        compute="_compute_receipt_permissions",
    )
    receipt_validated_by_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้รับสินค้า",
        readonly=True,
        copy=False,
    )
    receipt_validated_at = fields.Datetime(
        string="วันที่รับสินค้า",
        readonly=True,
        copy=False,
    )
    receipt_cancelled_by_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ยกเลิกการรับ",
        readonly=True,
        copy=False,
    )
    receipt_cancelled_at = fields.Datetime(
        string="วันที่ยกเลิกการรับ",
        readonly=True,
        copy=False,
    )
    has_short_shelf_life_drug = fields.Boolean(
        string="มียาอายุต่ำกว่าเกณฑ์",
        compute="_compute_short_shelf_life_warning",
    )
    short_shelf_life_line_count = fields.Integer(
        string="จำนวน LOT ยาอายุต่ำกว่าเกณฑ์",
        compute="_compute_short_shelf_life_warning",
    )

    @api.depends(
        "move_line_ids.quantity",
        "move_line_ids.expiration_date",
        "move_line_ids.minimum_receipt_shelf_life_days",
    )
    def _compute_short_shelf_life_warning(self):
        for picking in self:
            short_lines = picking.move_line_ids.filtered(
                lambda line: line.quantity > 0 and line.is_short_shelf_life
            )
            picking.has_short_shelf_life_drug = bool(short_lines)
            picking.short_shelf_life_line_count = len(short_lines)

    @api.depends_context("uid")
    def _compute_receipt_permissions(self):
        can_validate = (
            self.env.su
            or self.env.user.has_group(
                "vpk_maintenance.group_stock_receipt_validator"
            )
        )
        can_cancel = (
            self.env.su
            or self.env.user.has_group(
                "vpk_maintenance.group_stock_receipt_canceller"
            )
        )
        for picking in self:
            is_receipt = picking.picking_type_code == "incoming"
            picking.can_validate_receipt = not is_receipt or can_validate
            picking.can_cancel_receipt = not is_receipt or can_cancel

    def button_validate(self):
        unauthorized = self.filtered(
            lambda picking: picking.picking_type_code == "incoming"
            and not picking.can_validate_receipt
        )
        if unauthorized:
            raise UserError(
                _(
                    "คุณไม่มีสิทธิรับสินค้า กรุณาติดต่อผู้ดูแลเพื่อเพิ่มกลุ่ม "
                    "'ผู้มีสิทธิรับสินค้า'"
                )
            )
        self._check_medicine_shelf_life_certificates()
        result = super().button_validate()
        for picking in self.filtered(
            lambda record: record.picking_type_code == "incoming"
            and record.state == "done"
            and not record.receipt_validated_at
        ):
            picking.write({
                "receipt_validated_by_id": self.env.user.id,
                "receipt_validated_at": fields.Datetime.now(),
            })
            picking.message_post(
                body=_("รับสินค้าโดย %s") % self.env.user.display_name
            )
            if picking.has_short_shelf_life_drug:
                picking.message_post(
                    body=_(
                        "รับยาอายุต่ำกว่าเกณฑ์จำนวน %s LOT "
                        "โดยมีใบรับรองการเปลี่ยนยาครบถ้วน"
                    )
                    % picking.short_shelf_life_line_count
                )
        return result

    def _check_medicine_shelf_life_certificates(self):
        for picking in self.filtered(
            lambda record: record.picking_type_code == "incoming"
        ):
            controlled_lines = picking.move_line_ids.filtered(
                lambda line: line.quantity > 0
                and line.minimum_receipt_shelf_life_days > 0
            )
            missing_expiration = controlled_lines.filtered(
                lambda line: not line.expiration_date
            )
            if missing_expiration:
                raise UserError(
                    _(
                        "กรุณาระบุวันหมดอายุสำหรับ LOT ยา: %s"
                    )
                    % ", ".join(
                        missing_expiration.mapped(
                            lambda line: line.lot_name
                            or line.lot_id.name
                            or line.product_id.display_name
                        )
                    )
                )
            missing_certificates = controlled_lines.filtered(
                lambda line: line.is_short_shelf_life
                and not line.replacement_certificate
            )
            if missing_certificates:
                details = [
                    _(
                        "%(product)s / LOT %(lot)s: คงเหลือ %(days)s วัน "
                        "(เกณฑ์ %(minimum)s วัน)"
                    )
                    % {
                        "product": line.product_id.display_name,
                        "lot": line.lot_name
                        or line.lot_id.name
                        or "-",
                        "days": line.receipt_shelf_life_days,
                        "minimum": line.minimum_receipt_shelf_life_days,
                    }
                    for line in missing_certificates
                ]
                raise UserError(
                    _(
                        "พบยาอายุต่ำกว่าเกณฑ์ กรุณาแนบใบรับรองการเปลี่ยนยา"
                        "ก่อนยืนยันรับสินค้า:\n%s"
                    )
                    % "\n".join(details)
                )

    def action_cancel(self):
        unauthorized = self.filtered(
            lambda picking: picking.picking_type_code == "incoming"
            and picking.state != "cancel"
            and not picking.can_cancel_receipt
        )
        if unauthorized:
            raise UserError(
                _(
                    "คุณไม่มีสิทธิยกเลิกการรับสินค้า กรุณาติดต่อผู้ดูแลเพื่อเพิ่มกลุ่ม "
                    "'ผู้มีสิทธิยกเลิกการรับสินค้า'"
                )
            )
        result = super().action_cancel()
        for picking in self.filtered(
            lambda record: record.picking_type_code == "incoming"
            and record.state == "cancel"
            and not record.receipt_cancelled_at
        ):
            picking.write({
                "receipt_cancelled_by_id": self.env.user.id,
                "receipt_cancelled_at": fields.Datetime.now(),
            })
            picking.message_post(
                body=_("ยกเลิกการรับสินค้าโดย %s")
                % self.env.user.display_name
            )
        return result
