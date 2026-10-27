# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EbiddingPlanPublishCodeWizard(models.TransientModel):
    _name = "ebidding.plan.publish.code.wizard"
    _description = "บันทึกรหัสเผยแพร่แผน"

    plan_id = fields.Many2one(
        comodel_name="ebidding.plan",
        string="แผน",
        ondelete="cascade",
    )
    item_ids = fields.One2many(
        comodel_name="ebidding.plan.publish.code.wizard.item",
        inverse_name="wizard_id",
        string="รายการแผน",
    )
    publish_code = fields.Char(
        string="รหัสเผยแพร่แผน",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        if active_model == "ebidding.plan.line" and active_ids:
            lines = self.env["ebidding.plan.line"].browse(active_ids).exists()
            res["plan_id"] = lines[:1].plan_id.id
            res["item_ids"] = [
                (0, 0, {"plan_line_id": line.id, "selected": True})
                for line in lines
            ]
            codes = set(filter(None, lines.mapped("publish_code")))
            if len(codes) == 1:
                res["publish_code"] = codes.pop()
        elif active_model == "ebidding.plan":
            plan = self.env["ebidding.plan"].browse(
                self.env.context.get("active_id")
            ).exists()
            res["plan_id"] = plan.id
            res["item_ids"] = [
                (0, 0, {"plan_line_id": line.id, "selected": False})
                for line in plan.line_ids
            ]
        return res

    def action_select_all(self):
        self.ensure_one()
        self.item_ids.write({"selected": True})
        return self._reopen()

    def action_unselect_all(self):
        self.ensure_one()
        self.item_ids.write({"selected": False})
        return self._reopen()

    def _reopen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("บันทึกรหัสเผยแพร่แผน"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_confirm(self):
        self.ensure_one()
        selected = self.item_ids.filtered("selected")
        if not selected:
            raise UserError(_("กรุณาเลือกรายการแผนอย่างน้อย 1 รายการ"))
        code = (self.publish_code or "").strip()
        if not code:
            raise UserError(_("กรุณาระบุรหัสเผยแพร่แผน"))
        selected.mapped("plan_line_id").write({"publish_code": code})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("บันทึกรหัสเผยแพร่แผนแล้ว"),
                "message": _("อัปเดต %s รายการ") % len(selected),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class EbiddingPlanPublishCodeWizardItem(models.TransientModel):
    _name = "ebidding.plan.publish.code.wizard.item"
    _description = "รายการที่เลือกรหัสเผยแพร่แผน"
    _order = "id"

    wizard_id = fields.Many2one(
        comodel_name="ebidding.plan.publish.code.wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="เลือก", default=False)
    plan_line_id = fields.Many2one(
        comodel_name="ebidding.plan.line",
        string="รายการแผน",
        required=True,
        ondelete="cascade",
    )
    plan_code = fields.Char(
        related="plan_line_id.plan_code",
        string="รหัสแผนการจัดซื้อจัดจ้าง",
    )
    project_name = fields.Char(
        related="plan_line_id.project_name",
        string="ชื่อโครงการ/งานจัดซื้อจัดจ้าง",
    )
    publish_code_current = fields.Char(
        related="plan_line_id.publish_code",
        string="รหัสเผยแพร่แผนปัจจุบัน",
    )
