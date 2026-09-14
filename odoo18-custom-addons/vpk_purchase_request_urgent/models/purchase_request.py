# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    urgency_level = fields.Selection(
        selection=[
            ("normal", "ปกติ"),
            ("urgent", "เร่งด่วน"),
            ("emergency", "ฉุกเฉิน"),
        ],
        string="ระดับความเร่งด่วน",
        default="normal",
        required=True,
        tracking=True,
        index=True,
        help="ปกติ: ตามขั้นตอนมาตรฐาน\n"
             "เร่งด่วน: ต้องระบุเหตุผล และไฮไลต์ให้เห็นชัดในรายการ\n"
             "ฉุกเฉิน: ต้องระบุเหตุผล และอาจใช้เส้นทางตรวจงบแบบเร่งด่วน (ตั้งค่าใน Settings)",
    )
    urgency_reason = fields.Text(
        string="เหตุผลความเร่งด่วน/ฉุกเฉิน",
        tracking=True,
        help="บังคับกรอกเมื่อเลือกเร่งด่วนหรือฉุกเฉิน",
    )
    urgency_needed_date = fields.Date(
        string="ต้องการภายในวันที่",
        tracking=True,
        help="วันที่ที่ต้องได้ของ/งาน สำหรับกรณีเร่งด่วนหรือฉุกเฉิน",
    )
    is_urgency = fields.Boolean(
        string="เป็นเร่งด่วน/ฉุกเฉิน",
        compute="_compute_is_urgency",
        store=True,
        index=True,
    )

    @api.depends("urgency_level")
    def _compute_is_urgency(self):
        for request in self:
            request.is_urgency = request.urgency_level in ("urgent", "emergency")

    @api.constrains("urgency_level", "urgency_reason")
    def _check_urgency_reason(self):
        for request in self:
            if request.urgency_level in ("urgent", "emergency") and not (
                request.urgency_reason or ""
            ).strip():
                raise ValidationError(
                    _("กรุณาระบุเหตุผลความเร่งด่วน/ฉุกเฉิน สำหรับ PR %(name)s")
                    % {"name": request.display_name}
                )

    @api.onchange("urgency_level")
    def _onchange_urgency_level(self):
        if self.urgency_level == "normal":
            self.urgency_reason = False
            return
        if self.urgency_level == "emergency":
            return {
                "warning": {
                    "title": _("ขอซื้อฉุกเฉิน"),
                    "message": _(
                        "กรุณาระบุเหตุผลฉุกเฉินและวันที่ต้องการของให้ครบ\n"
                        "การขอซื้อฉุกเฉินจะถูกไฮไลต์และติดตามแยกในเมนูพิเศษ"
                    ),
                }
            }
        return {
            "warning": {
                "title": _("ขอซื้อเร่งด่วน"),
                "message": _("กรุณาระบุเหตุผลความเร่งด่วนก่อนส่งอนุมัติ"),
            }
        }

    def _emergency_budget_bypass_enabled(self):
        """อ่านค่าจาก Settings — อนุญาตให้ PR ฉุกเฉินตรวจงบแบบเร่งด่วน."""
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_purchase_request_urgent.emergency_budget_bypass", "False")
            == "True"
        )

    def _has_emergency_bypass_budget(self):
        """PR ฉุกเฉิน (และเปิดตั้งค่า) ใช้เส้นทางตรวจงบเร่งด่วน ไม่จองงบแผ่นดินทันที."""
        self.ensure_one()
        return (
            self.urgency_level == "emergency"
            and self._emergency_budget_bypass_enabled()
            and not getattr(self, "contract_id", False)
        )

    @api.depends("state", "budget_check_state", "urgency_level")
    def _compute_hide_reviews(self):
        super()._compute_hide_reviews()
        for request in self:
            if (
                request.state == "draft"
                and request.urgency_level == "emergency"
                and request._has_emergency_bypass_budget()
                and request.budget_check_state == "enough"
            ):
                request.hide_reviews = False

    def _validate_urgency_before_submit(self):
        for request in self:
            if request.urgency_level in ("urgent", "emergency"):
                if not (request.urgency_reason or "").strip():
                    raise UserError(
                        _("PR %(name)s เป็น%(level)s — ต้องระบุเหตุผลก่อนส่งอนุมัติ")
                        % {
                            "name": request.display_name,
                            "level": dict(request._fields["urgency_level"].selection).get(
                                request.urgency_level
                            ),
                        }
                    )
                if not request.urgency_needed_date:
                    raise UserError(
                        _("PR %(name)s เป็น%(level)s — กรุณาระบุวันที่ต้องการของ/งาน")
                        % {
                            "name": request.display_name,
                            "level": dict(request._fields["urgency_level"].selection).get(
                                request.urgency_level
                            ),
                        }
                    )

    def _apply_emergency_budget_bypass(self):
        for request in self:
            request._validate_urgency_before_submit()
            request.with_context(skip_budget_check_reset=True).write(
                {
                    "budget_check_state": "enough",
                    "budget_check_date": fields.Datetime.now(),
                    "budget_check_message": _(
                        "เส้นทางฉุกเฉิน: อนุญาตดำเนินการก่อนจองงบประมาณแผ่นดิน\n"
                        "เหตุผล: %(reason)s\n"
                        "ต้องการภายใน: %(needed)s\n"
                        "หมายเหตุ: ต้องติดตามตัดงบ/โอนงบย้อนหลังหลังจัดซื้อ"
                    )
                    % {
                        "reason": (request.urgency_reason or "").strip(),
                        "needed": request.urgency_needed_date or "-",
                    },
                }
            )
            request.message_post(
                body=_(
                    "ใช้เส้นทางขอซื้อฉุกเฉิน — ข้ามการจองงบประมาณชั่วคราว "
                    "(ต้องติดตามตัดงบภายหลัง)"
                )
            )

    def action_check_budget_status(self):
        emergency_prs = self.filtered(lambda pr: pr._has_emergency_bypass_budget())
        normal_prs = self - emergency_prs
        emergency_prs._apply_emergency_budget_bypass()
        if emergency_prs and not normal_prs:
            request = emergency_prs[:1]
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("ตรวจงบฉุกเฉิน: ผ่าน (เร่งด่วน)"),
                    "message": _(
                        "PR ฉุกเฉินได้รับอนุญาตดำเนินการก่อนจองงบ — "
                        "อย่าลืมติดตามตัดงบภายหลัง"
                    ),
                    "type": "warning",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": self._name,
                        "res_id": request.id,
                        "view_mode": "form",
                        "views": [(False, "form")],
                        "target": "current",
                    },
                },
            }
        return super(PurchaseRequest, normal_prs).action_check_budget_status()

    def _check_budget_available_before_submit(self):
        emergency_prs = self.filtered(lambda pr: pr._has_emergency_bypass_budget())
        normal_prs = self - emergency_prs
        emergency_prs._apply_emergency_budget_bypass()
        if normal_prs:
            return super(PurchaseRequest, normal_prs)._check_budget_available_before_submit()
        return True

    def button_to_approve(self):
        self._validate_urgency_before_submit()
        return super().button_to_approve()

    def button_approved(self):
        self._validate_urgency_before_submit()
        return super().button_approved()

    def request_validation(self):
        self._validate_urgency_before_submit()
        return super().request_validation()
