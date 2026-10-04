# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context


class StockQcCheckWizard(models.TransientModel):
    _name = "vpk.stock.qc.check.wizard"
    _description = "หน้าต่างตรวจตามจุดควบคุม"

    check_ids = fields.Many2many(
        comodel_name="vpk.stock.qc.check",
        relation="vpk_stock_qc_check_wizard_rel",
        required=True,
    )
    current_check_id = fields.Many2one(
        comodel_name="vpk.stock.qc.check",
        required=True,
    )
    nb_checks = fields.Integer(compute="_compute_position")
    position_current_check = fields.Integer(compute="_compute_position")
    is_last_check = fields.Boolean(compute="_compute_position")
    title = fields.Char(related="current_check_id.title")
    product_id = fields.Many2one(related="current_check_id.product_id")
    test_type = fields.Selection(related="current_check_id.test_type")
    note = fields.Text(related="current_check_id.note")
    quality_state = fields.Selection(related="current_check_id.quality_state")
    measure = fields.Float(
        related="current_check_id.measure",
        readonly=False,
        digits=(16, 4),
    )
    tolerance_min = fields.Float(related="current_check_id.tolerance_min")
    tolerance_max = fields.Float(related="current_check_id.tolerance_max")
    uom = fields.Char(related="current_check_id.uom")
    uses_tolerance = fields.Boolean(compute="_compute_uses_tolerance")
    failure_message = fields.Char()

    @api.depends("current_check_id", "check_ids")
    def _compute_position(self):
        for wizard in self:
            ids = wizard.check_ids.ids
            wizard.nb_checks = len(ids)
            if wizard.current_check_id.id in ids:
                wizard.position_current_check = ids.index(wizard.current_check_id.id) + 1
            else:
                wizard.position_current_check = 0
            wizard.is_last_check = wizard.position_current_check == wizard.nb_checks

    @api.depends("current_check_id")
    def _compute_uses_tolerance(self):
        for wizard in self:
            wizard.uses_tolerance = bool(
                wizard.current_check_id and wizard.current_check_id._uses_tolerance()
            )

    def do_pass(self):
        self.current_check_id.do_pass()
        return self._next_window()

    def do_fail(self):
        self.current_check_id.do_fail()
        return self._next_window()

    def do_measure(self):
        self.ensure_one()
        check = self.current_check_id
        if check._measure_passes():
            check.do_pass()
            return self._next_window()
        self.failure_message = _(
            "วัดได้ %(measure)s %(uom)s ต้องอยู่ระหว่าง %(min)s ถึง %(max)s %(uom)s"
        ) % {
            "measure": f"{check.measure:g}",
            "min": f"{check.tolerance_min:g}",
            "max": f"{check.tolerance_max:g}",
            "uom": check.uom or "",
        }
        return {
            "type": "ir.actions.act_window",
            "name": _("ค่าที่วัดไม่ผ่าน"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(
                self.env.ref("vpk_stock_qc.view_qc_check_wizard_failure").id,
                "form",
            )],
            "target": "new",
            "context": {
                "vpk_qc_from_validate": self.env.context.get("vpk_qc_from_validate"),
            },
        }

    def confirm_fail(self):
        self.current_check_id.do_fail()
        return self._next_window()

    def correct_measure(self):
        return {
            "type": "ir.actions.act_window",
            "name": self.current_check_id.title or _("ตรวจคุณภาพ"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(
                self.env.ref("vpk_stock_qc.view_qc_check_wizard").id,
                "form",
            )],
            "target": "new",
            "context": {
                "vpk_qc_from_validate": self.env.context.get("vpk_qc_from_validate"),
            },
        }

    def action_previous(self):
        ids = self.check_ids.ids
        index = ids.index(self.current_check_id.id)
        if index <= 0:
            raise UserError(_("นี่คือรายการแรก"))
        return self._window(self.env["vpk.stock.qc.check"].browse(ids[index - 1]))

    def _next_window(self):
        ids = self.check_ids.ids
        index = ids.index(self.current_check_id.id)
        if index + 1 < len(ids):
            return self._window(self.env["vpk.stock.qc.check"].browse(ids[index + 1]))
        if self.env.context.get("vpk_qc_from_validate"):
            pickings = self.check_ids.qc_id.picking_id
            failed = self.check_ids.filtered(lambda check: check.quality_state == "fail")
            pending = self.check_ids.filtered(lambda check: check.quality_state == "none")
            if not failed and not pending:
                return pickings.with_context(
                    clean_context(self.env.context),
                    skip_qc_wizard=True,
                ).button_validate()
        return {"type": "ir.actions.act_window_close"}

    def _window(self, check):
        return {
            "type": "ir.actions.act_window",
            "name": check.title or _("ตรวจคุณภาพ"),
            "res_model": self._name,
            "view_mode": "form",
            "views": [(
                self.env.ref("vpk_stock_qc.view_qc_check_wizard").id,
                "form",
            )],
            "target": "new",
            "context": {
                "default_check_ids": self.check_ids.ids,
                "default_current_check_id": check.id,
                "vpk_qc_from_validate": self.env.context.get("vpk_qc_from_validate"),
            },
        }
