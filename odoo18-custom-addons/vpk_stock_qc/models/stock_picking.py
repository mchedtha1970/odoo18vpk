# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    qc_ids = fields.One2many(
        comodel_name="vpk.stock.qc",
        inverse_name="picking_id",
        string="ตรวจคุณภาพ",
    )
    qc_id = fields.Many2one(
        comodel_name="vpk.stock.qc",
        string="ใบตรวจคุณภาพ",
        compute="_compute_qc_id",
    )
    qc_state = fields.Selection(
        related="qc_id.state",
        string="ผลตรวจคุณภาพ",
    )
    qc_count = fields.Integer(compute="_compute_qc_id")

    @api.depends("qc_ids", "qc_ids.state")
    def _compute_qc_id(self):
        for picking in self:
            qc = picking.qc_ids[:1]
            picking.qc_id = qc
            picking.qc_count = len(picking.qc_ids)

    def action_open_receipt_qc(self):
        self.ensure_one()
        if self.picking_type_code != "incoming":
            raise UserError(_("ตรวจคุณภาพใช้กับใบรับสินค้าเท่านั้น"))
        qc = self.qc_ids[:1]
        if not qc:
            qc = self.env["vpk.stock.qc"].create({"picking_id": self.id})
        qc._sync_control_checks()
        return {
            "type": "ir.actions.act_window",
            "name": qc.display_name,
            "res_model": "vpk.stock.qc",
            "res_id": qc.id,
            "view_mode": "form",
            "target": "current",
        }

    def _vpk_sync_receipt_qc_checks(self):
        Point = self.env["vpk.stock.qc.point"]
        for picking in self.filtered(
            lambda record: record.picking_type_code == "incoming"
            and record.state not in ("done", "cancel")
        ):
            products = picking.move_ids.filtered(
                lambda move: move.state != "cancel"
            ).product_id
            if not Point._matches(products, picking.picking_type_id) and not picking.qc_ids:
                continue
            qc = picking.qc_ids[:1]
            if not qc:
                qc = self.env["vpk.stock.qc"].create({"picking_id": picking.id})
            qc._sync_control_checks()

    def _check_receipt_qc_passed(self):
        for picking in self.filtered(
            lambda record: record.picking_type_code == "incoming"
            and record.state not in ("done", "cancel")
        ):
            qc = picking.qc_ids[:1]
            checks = qc.check_ids
            if checks:
                failed = checks.filtered(lambda check: check.quality_state == "fail")
                pending = checks.filtered(lambda check: check.quality_state == "none")
                if failed:
                    raise UserError(
                        _("ยังรับเข้าคลังไม่ได้ %s มีจุดควบคุมที่ไม่ผ่าน")
                        % picking.display_name
                    )
                if pending:
                    raise UserError(
                        _("ยังรับเข้าคลังไม่ได้ %s ยังตรวจจุดควบคุมไม่ครบ")
                        % picking.display_name
                    )
                if qc.state == "draft":
                    qc.action_confirm()
                elif qc.state != "passed":
                    raise UserError(
                        _("ยังรับเข้าคลังไม่ได้ ต้องตรวจคุณภาพสินค้าของ %s ให้ผ่านก่อน")
                        % picking.display_name
                    )
            elif not qc or qc.state != "passed":
                raise UserError(
                    _("ยังรับเข้าคลังไม่ได้ ต้องตรวจคุณภาพสินค้าของ %s ให้ผ่านก่อน")
                    % picking.display_name
                )

    def button_validate(self):
        if not self.env.context.get("skip_qc_wizard"):
            incoming = self.filtered(
                lambda record: record.picking_type_code == "incoming"
                and record.state not in ("done", "cancel")
            )
            incoming._vpk_sync_receipt_qc_checks()
            todo = incoming.qc_ids.check_ids.filtered(
                lambda check: check.quality_state == "none" and check.qc_id.state == "draft"
            )
            if todo:
                if not self.env.user.has_group("vpk_stock_qc.group_qc_user"):
                    raise UserError(_("ยังมีจุดควบคุมคุณภาพที่ต้องตรวจก่อนรับเข้าคลัง"))
                return todo.with_context(vpk_qc_from_validate=True).action_open_wizard()
        self._check_receipt_qc_passed()
        return super().button_validate()
