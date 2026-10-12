from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class VpkBudgetMaterialAllocationWizard(models.TransientModel):
    _name = "vpk.budget.material.allocation.wizard"
    _description = "Allocate Material Budget"

    request_id = fields.Many2one(
        comodel_name="departmental.budget.request",
        string="คำของบ",
        required=True,
        readonly=True,
    )
    target = fields.Selection(
        selection=[
            ("material", "วัสดุ"),
            ("asset", "ครุภัณฑ์"),
        ],
        string="แบบฟอร์ม",
        required=True,
        default="material",
        readonly=True,
    )
    available_budget_post_ids = fields.Many2many(
        comodel_name="account.budget.post",
        compute="_compute_available_budget_post_ids",
    )
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        domain="[('id', 'in', available_budget_post_ids)]",
        help="ไม่เลือก หมายถึงจัดสรรทุกรายการในคำของบนี้",
    )
    mode = fields.Selection(
        selection=[
            ("equal", "เท่ากับที่ขอ"),
            ("increase", "เพิ่มจากที่ขอ"),
            ("decrease", "ลดจากที่ขอ"),
        ],
        string="วิธีจัดสรร",
        required=True,
        default="equal",
    )
    percent = fields.Float(
        string="เปอร์เซ็นต์",
        digits=(16, 2),
        help="เพิ่ม 10 คือได้ 110% ของยอดที่ขอ ลด 10 คือได้ 90%",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        request_id = self.env.context.get("default_request_id") or self.env.context.get(
            "active_id"
        )
        if request_id and self.env.context.get("active_model") in (
            None,
            "departmental.budget.request",
        ):
            res["request_id"] = request_id
        target = self.env.context.get("default_target")
        if target in ("material", "asset"):
            res["target"] = target
        return res

    @api.depends(
        "request_id",
        "target",
        "request_id.material_detail_ids.budget_post_id",
        "request_id.asset_line_ids.budget_post_id",
    )
    def _compute_available_budget_post_ids(self):
        for wizard in self:
            lines = wizard._source_lines()
            wizard.available_budget_post_ids = lines.mapped("budget_post_id")

    def _source_lines(self):
        self.ensure_one()
        request = self.request_id
        if self.target == "asset":
            return request.asset_line_ids
        return request.material_detail_ids

    @api.constrains("mode", "percent")
    def _check_percent(self):
        for wizard in self:
            if wizard.mode == "equal":
                continue
            if wizard.percent < 0:
                raise ValidationError(_("เปอร์เซ็นต์ต้องไม่ติดลบ"))
            if wizard.mode == "decrease" and wizard.percent > 100:
                raise ValidationError(_("ลดได้ไม่เกิน 100% ของยอดที่ขอ"))

    def _allocation_factor(self):
        self.ensure_one()
        if self.mode == "increase":
            return 1.0 + (self.percent or 0.0) / 100.0
        if self.mode == "decrease":
            return max(0.0, 1.0 - (self.percent or 0.0) / 100.0)
        return 1.0

    def _rule_label(self):
        self.ensure_one()
        basis = _("งบประมาณที่ขอ") if self.target == "asset" else _("ปริมาณที่ขอ")
        if self.mode == "increase":
            return _("เพิ่ม %s%% จาก%s") % (self._format_percent(), basis)
        if self.mode == "decrease":
            return _("ลด %s%% จาก%s") % (self._format_percent(), basis)
        return _("เท่ากับ%s") % basis

    def _format_percent(self):
        percent = self.percent or 0.0
        if percent == int(percent):
            return str(int(percent))
        return ("%s" % percent).rstrip("0").rstrip(".")

    def action_apply(self):
        self.ensure_one()
        request = self.request_id
        if not request:
            raise UserError(_("ไม่พบคำของบ"))
        if request.state != "draft" and not request.can_edit_allocation:
            raise ValidationError(_("ไม่สามารถระบุยอดจัดสรรในสถานะปัจจุบันได้"))
        lines = self._source_lines()
        if self.budget_post_id:
            lines = lines.filtered(
                lambda line: line.budget_post_id == self.budget_post_id
            )
        if not lines:
            raise UserError(_("ไม่มีรายการในหมวดที่เลือก"))

        factor = self._allocation_factor()
        if self.target == "asset":
            self._apply_asset_allocation(lines, factor)
        else:
            self._apply_material_allocation(lines, factor)
        scope = self.budget_post_id.display_name or _("ทุกรายการ")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("จัดสรรงบประมาณ"),
                "message": _("จัดสรร %s แล้ว %s รายการ (%s)")
                % (self._rule_label(), len(lines), scope),
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def _apply_material_allocation(self, details, factor):
        self.env.cr.execute(
            """
            UPDATE departmental_budget_request_material_detail
               SET allocated_qty = ROUND((quantity * %s)::numeric, 2),
                   allocated_amount = ROUND((quantity * %s)::numeric, 2) * unit_price,
                   write_date = (now() at time zone 'UTC'),
                   write_uid = %s
             WHERE id IN %s
            """,
            (factor, factor, self.env.uid, tuple(details.ids)),
        )
        details.invalidate_recordset(
            ["allocated_qty", "allocated_amount", "write_date", "write_uid"]
        )
        self.request_id._sync_material_allocation_from_details()

    def _apply_asset_allocation(self, lines, factor):
        for line in lines:
            requested = line.total_amount or 0.0
            line.write({"allocated_budget_amount": round(requested * factor, 2)})
