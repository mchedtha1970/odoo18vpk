# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PROCUREMENT_IN_PROGRESS_STATES = ("to_approve", "approved", "in_progress")
PROCUREMENT_INBOX_STATES = ("sent_to_procurement",) + PROCUREMENT_IN_PROGRESS_STATES


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    sent_to_procurement_date = fields.Datetime(
        string="วันที่ส่งพัสดุ",
        readonly=True,
        copy=False,
        index=True,
        help="วันเวลาที่หน่วยงานกดส่งพัสดุ",
    )
    procurement_owner_id = fields.Many2one(
        "res.users",
        string="ผู้รับงานพัสดุ",
        tracking=True,
        copy=False,
        index=True,
        help="เจ้าหน้าที่พัสดุที่รับใบนี้ไปดำเนินการ",
    )
    procurement_claimed_date = fields.Datetime(
        string="วันที่รับงาน",
        readonly=True,
        copy=False,
    )
    days_waiting_procurement = fields.Integer(
        string="วันค้างที่พัสดุ",
        compute="_compute_days_waiting_procurement",
        store=True,
        help="จำนวนวันนับจากวันที่ส่งพัสดุจนถึงวันนี้ (เฉพาะสถานะส่งพัสดุแล้ว)",
    )
    procurement_inbox_lane = fields.Selection(
        [
            ("unassigned", "ยังไม่มีผู้รับ"),
            ("mine", "ของฉัน"),
            ("others", "มีผู้รับแล้ว"),
        ],
        string="คิวรับงาน",
        compute="_compute_procurement_inbox_lane",
        search="_search_procurement_inbox_lane",
    )
    procurement_inbox_stage = fields.Selection(
        [
            ("waiting", "รอรับงาน"),
            ("claimed", "รับงานแล้ว"),
            ("progress", "กำลังดำเนินการ"),
        ],
        string="สถานะคิวพัสดุ",
        compute="_compute_procurement_inbox_stage",
        store=True,
        index=True,
        group_expand=True,
    )
    is_procurement_overdue = fields.Boolean(
        string="ค้างเกิน 3 วัน",
        compute="_compute_days_waiting_procurement",
        store=True,
    )
    procurement_verified = fields.Boolean(
        string="พัสดุตรวจสอบแล้ว",
        tracking=True,
        copy=False,
        index=True,
    )
    procurement_verified_by = fields.Many2one(
        "res.users",
        string="ผู้ตรวจสอบ (พัสดุ)",
        readonly=True,
        copy=False,
        tracking=True,
    )
    procurement_verified_date = fields.Datetime(
        string="วันที่ตรวจสอบ (พัสดุ)",
        readonly=True,
        copy=False,
    )
    procurement_return_reason = fields.Text(
        string="เหตุผลที่พัสดุส่งกลับให้แก้ไข",
        readonly=True,
        copy=False,
        tracking=True,
    )
    procurement_returned_by = fields.Many2one(
        "res.users",
        string="ผู้ส่งกลับให้แก้ไข",
        readonly=True,
        copy=False,
    )
    procurement_returned_date = fields.Datetime(
        string="วันที่ส่งกลับให้แก้ไข",
        readonly=True,
        copy=False,
    )

    @api.depends("sent_to_procurement_date", "state")
    def _compute_days_waiting_procurement(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.state != "sent_to_procurement" or not rec.sent_to_procurement_date:
                rec.days_waiting_procurement = 0
                rec.is_procurement_overdue = False
                continue
            delta = now - rec.sent_to_procurement_date
            days = max(delta.days, 0)
            rec.days_waiting_procurement = days
            rec.is_procurement_overdue = days >= 3

    @api.depends("procurement_owner_id")
    def _compute_procurement_inbox_lane(self):
        uid = self.env.uid
        for rec in self:
            if not rec.procurement_owner_id:
                rec.procurement_inbox_lane = "unassigned"
            elif rec.procurement_owner_id.id == uid:
                rec.procurement_inbox_lane = "mine"
            else:
                rec.procurement_inbox_lane = "others"

    @api.depends("procurement_owner_id", "state")
    def _compute_procurement_inbox_stage(self):
        for rec in self:
            if rec.state in PROCUREMENT_IN_PROGRESS_STATES:
                rec.procurement_inbox_stage = "progress"
            elif rec.state == "sent_to_procurement":
                rec.procurement_inbox_stage = (
                    "claimed" if rec.procurement_owner_id else "waiting"
                )
            else:
                rec.procurement_inbox_stage = False

    @api.depends("procurement_verified")
    def _compute_can_send_to_egp(self):
        return super()._compute_can_send_to_egp()

    def _search_procurement_inbox_lane(self, operator, value):
        if operator not in ("=", "!="):
            return []
        uid = self.env.uid
        if value == "unassigned":
            domain = [("procurement_owner_id", "=", False)]
        elif value == "mine":
            domain = [("procurement_owner_id", "=", uid)]
        elif value == "others":
            domain = [
                ("procurement_owner_id", "!=", False),
                ("procurement_owner_id", "!=", uid),
            ]
        else:
            return []
        if operator == "!=":
            return ["!"] + domain
        return domain

    def action_send_to_procurement(self):
        res = super().action_send_to_procurement()
        self.write(
            {
                "sent_to_procurement_date": fields.Datetime.now(),
                "procurement_owner_id": False,
                "procurement_claimed_date": False,
                "procurement_verified": False,
                "procurement_verified_by": False,
                "procurement_verified_date": False,
                "procurement_return_reason": False,
                "procurement_returned_by": False,
                "procurement_returned_date": False,
            }
        )
        self._notify_procurement_inbox_updated()
        return res

    def button_draft(self):
        res = super().button_draft()
        vals = {
            "sent_to_procurement_date": False,
            "procurement_owner_id": False,
            "procurement_claimed_date": False,
            "procurement_verified": False,
            "procurement_verified_by": False,
            "procurement_verified_date": False,
        }
        if not self.env.context.get("vpk_keep_return_reason"):
            vals.update(
                {
                    "procurement_return_reason": False,
                    "procurement_returned_by": False,
                    "procurement_returned_date": False,
                }
            )
        self.write(vals)
        self._notify_procurement_inbox_updated()
        return res

    def action_verify_procurement(self):
        """เจ้าหน้าที่พัสดุตรวจสอบความถูกต้องของรายการใบขอซื้อก่อนส่งเข้า e-GP"""
        user = self.env.user
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state not in ("sent_to_procurement", "to_approve", "approved"):
                raise UserError(
                    _("ยืนยันการตรวจสอบได้เฉพาะใบขอซื้อที่ส่งมาให้พัสดุแล้ว")
                )
            active_lines = rec.line_ids.filtered(
                lambda line: not line.cancelled and line.product_qty
            )
            if not active_lines:
                raise UserError(_("ใบขอซื้อไม่มีรายการสินค้าที่ใช้งานอยู่"))
            if (
                "budget_check_state" in rec._fields
                and rec.budget_check_state != "enough"
            ):
                raise UserError(_("ใบขอซื้อต้องผ่านการตรวจสอบงบประมาณก่อน"))
            vals = {
                "procurement_verified": True,
                "procurement_verified_by": user.id,
                "procurement_verified_date": now,
                "procurement_return_reason": False,
                "procurement_returned_by": False,
                "procurement_returned_date": False,
            }
            if not rec.procurement_owner_id:
                vals["procurement_owner_id"] = user.id
                vals["procurement_claimed_date"] = now
            if "verified_by" in rec._fields:
                vals["verified_by"] = user.id
            if "date_verified" in rec._fields:
                vals["date_verified"] = today
            rec.write(vals)
            if "can_send_to_egp" in rec._fields:
                rec.invalidate_recordset(["can_send_to_egp"])
            rec.message_post(
                body=_(
                    "พัสดุตรวจสอบความถูกต้องของรายการใบขอซื้อเรียบร้อยแล้ว โดย %s (พร้อมส่งเข้าระบบ e-GP)"
                )
                % user.display_name
            )
        self._notify_procurement_inbox_updated()
        return True

    def action_open_return_for_revision_wizard(self):
        """เปิดหน้าต่างให้พัสดุระบุเหตุผลในการส่งกลับใบขอซื้อให้หน่วยงานแก้ไข"""
        self.ensure_one()
        if self.state not in ("sent_to_procurement", "to_approve"):
            raise UserError(
                _("ส่งกลับให้แก้ไขได้เฉพาะใบขอซื้อสถานะ ส่งพัสดุแล้ว")
            )
        if hasattr(self, "_get_egp_requisitions") and self._get_egp_requisitions():
            raise UserError(
                _("ไม่สามารถส่งกลับได้ เนื่องจากใบขอซื้อนี้ส่งเข้าระบบ e-GP แล้ว")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("ส่งกลับให้แก้ไข"),
            "res_model": "purchase.request.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
            },
        }

    def _vpk_do_return_for_revision(self, reason):
        """เปลี่ยนสถานะใบขอซื้อกลับเป็น ร่าง พร้อมบันทึกเหตุผลที่พัสดุส่งกลับให้แก้ไข"""
        user = self.env.user
        now = fields.Datetime.now()
        for rec in self:
            if rec.state not in ("sent_to_procurement", "to_approve"):
                raise UserError(
                    _("ส่งกลับให้แก้ไขได้เฉพาะใบขอซื้อสถานะ ส่งพัสดุแล้ว")
                )
            rec.with_context(
                vpk_keep_return_reason=True,
                skip_validation_check=True,
                skip_check_state_condition=True,
            ).button_draft()
            returnVals = {
                "procurement_return_reason": reason,
                "procurement_returned_by": user.id,
                "procurement_returned_date": now,
            }
            if "verified_by" in rec._fields:
                returnVals["verified_by"] = False
            if "date_verified" in rec._fields:
                returnVals["date_verified"] = False
            rec.with_context(
                skip_validation_check=True,
                skip_check_state_condition=True,
                skip_budget_check_reset=True,
            ).write(returnVals)
            rec.message_post(
                body=_(
                    "พัสดุส่งกลับใบขอซื้อให้หน่วยงานแก้ไข โดย %(user)s\nเหตุผล: %(reason)s"
                )
                % {
                    "user": user.display_name,
                    "reason": reason,
                }
            )
        self._notify_procurement_inbox_updated()
        return True

    def action_claim_procurement(self):
        """พัสดุกดรับงาน เพื่อดึงใบมาเป็นของตน"""
        user = self.env.user
        for rec in self:
            if rec.state != "sent_to_procurement":
                raise UserError(_("รับงานได้เฉพาะใบขอซื้อสถานะ ส่งพัสดุแล้ว"))
            if rec.procurement_owner_id and rec.procurement_owner_id != user:
                raise UserError(
                    _("ใบ %(name)s มี %(owner)s รับงานแล้ว")
                    % {
                        "name": rec.name,
                        "owner": rec.procurement_owner_id.display_name,
                    }
                )
        self.write(
            {
                "procurement_owner_id": user.id,
                "procurement_claimed_date": fields.Datetime.now(),
            }
        )
        for rec in self:
            rec.message_post(
                body=_("พัสดุรับงานแล้ว: %s") % user.display_name
            )
        self._notify_procurement_inbox_updated()
        return True

    def action_unclaim_procurement(self):
        """คืนคิวให้พัสดุคนอื่นรับได้"""
        user = self.env.user
        is_manager = user.has_group(
            "purchase_request.group_purchase_request_manager"
        )
        for rec in self:
            if rec.state != "sent_to_procurement":
                raise UserError(_("คืนคิวได้เฉพาะใบขอซื้อสถานะ ส่งพัสดุแล้ว"))
            if (
                rec.procurement_owner_id
                and rec.procurement_owner_id != user
                and not is_manager
            ):
                raise UserError(_("คืนคิวได้เฉพาะใบที่ตนรับไว้ หรือผู้จัดการพัสดุ"))
        self.write(
            {
                "procurement_owner_id": False,
                "procurement_claimed_date": False,
            }
        )
        for rec in self:
            rec.message_post(body=_("คืนคิวใบขอซื้อให้รอรับใหม่"))
        self._notify_procurement_inbox_updated()
        return True

    def action_open_procurement_work(self):
        """เปิดฟอร์มใบขอซื้อเพื่อเริ่มทำงาน"""
        self.ensure_one()
        if (
            self.state == "sent_to_procurement"
            and not self.procurement_owner_id
        ):
            self.action_claim_procurement()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "purchase.request",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _inbox_grouped_rows(self, domain, field_name, empty_label="ไม่ระบุ"):
        rows = self.read_group(
            domain, [field_name, "estimated_cost:sum"], [field_name], lazy=False
        )
        result = []
        for row in rows:
            rec = row.get(field_name)
            rec_id = rec[0] if rec else False
            name = rec[1] if rec else empty_label
            amount = row.get("estimated_cost_sum") or row.get("estimated_cost") or 0.0
            result.append(
                {
                    "id": rec_id,
                    "name": name,
                    "count": row.get("__count", 0),
                    "amount": amount,
                }
            )
        result.sort(key=lambda item: (-item["count"], item["name"] or ""))
        return result[:8]

    @api.model
    def get_procurement_inbox_stats(self):
        """KPI และสรุปมุมมองสำหรับ dashboard พัสดุ"""
        base = [("state", "in", PROCUREMENT_INBOX_STATES)]
        Request = self.env["purchase.request"]
        total = Request.search_count(base)
        in_progress = Request.search_count(
            [("state", "in", PROCUREMENT_IN_PROGRESS_STATES)]
        )
        unassigned = Request.search_count(
            base + [("procurement_owner_id", "=", False)]
        )
        claimed = Request.search_count(
            base + [("procurement_owner_id", "!=", False)]
        )
        mine = Request.search_count(
            base + [("procurement_owner_id", "=", self.env.uid)]
        )
        overdue = Request.search_count(
            base + [("is_procurement_overdue", "=", True)]
        )
        urgent = 0
        if "urgency_level" in self._fields:
            urgent = Request.search_count(
                base
                + [("urgency_level", "in", ("urgent", "emergency"))]
            )
        elif "is_urgency" in self._fields:
            urgent = Request.search_count(base + [("is_urgency", "=", True)])

        amount_rows = Request.read_group(base, ["estimated_cost:sum"], [])
        amount_total = 0.0
        if amount_rows:
            amount_total = (
                amount_rows[0].get("estimated_cost_sum")
                or amount_rows[0].get("estimated_cost")
                or 0.0
            )

        by_owner = self._inbox_grouped_rows(
            base, "procurement_owner_id", empty_label="ยังไม่มีผู้รับ"
        )
        aging = []
        aging_specs = [
            (
                "fresh",
                "ไม่เกิน 2 วัน",
                base
                + [
                    ("state", "=", "sent_to_procurement"),
                    ("days_waiting_procurement", "<", 3),
                ],
            ),
            (
                "warn",
                "ค้าง 3-7 วัน",
                base
                + [
                    ("state", "=", "sent_to_procurement"),
                    ("days_waiting_procurement", ">=", 3),
                    ("days_waiting_procurement", "<=", 7),
                ],
            ),
            (
                "stale",
                "ค้างเกิน 7 วัน",
                base
                + [
                    ("state", "=", "sent_to_procurement"),
                    ("days_waiting_procurement", ">", 7),
                ],
            ),
            (
                "progress",
                "กำลังดำเนินการ",
                [("state", "in", PROCUREMENT_IN_PROGRESS_STATES)],
            ),
        ]
        for key, label, aging_domain in aging_specs:
            aging_rows = Request.read_group(
                aging_domain, ["estimated_cost:sum"], []
            )
            aging_amount = 0.0
            if aging_rows:
                aging_amount = (
                    aging_rows[0].get("estimated_cost_sum")
                    or aging_rows[0].get("estimated_cost")
                    or 0.0
                )
            aging.append(
                {
                    "id": key,
                    "name": label,
                    "count": Request.search_count(aging_domain),
                    "amount": aging_amount,
                }
            )

        return {
            "total": total,
            "in_progress": in_progress,
            "unassigned": unassigned,
            "claimed": claimed,
            "mine": mine,
            "overdue": overdue,
            "urgent": urgent,
            "amount_total": amount_total,
            "has_urgency": bool(
                "urgency_level" in self._fields or "is_urgency" in self._fields
            ),
            "by_department": self._inbox_grouped_rows(
                base, "department_id", empty_label="ไม่ระบุหน่วยงาน"
            ),
            "by_method": self._inbox_grouped_rows(
                base, "procurement_method_id", empty_label="ไม่ระบุวิธี"
            ),
            "by_owner": by_owner,
            "by_aging": aging,
        }

    @api.model
    def get_procurement_inbox_domain(self, filter_name="total", extra=None):
        domain = [("state", "in", PROCUREMENT_INBOX_STATES)]
        if filter_name == "in_progress":
            domain = [("state", "in", PROCUREMENT_IN_PROGRESS_STATES)]
        elif filter_name == "unassigned":
            domain.append(("procurement_owner_id", "=", False))
        elif filter_name == "claimed":
            domain.append(("procurement_owner_id", "!=", False))
        elif filter_name == "mine":
            domain.append(("procurement_owner_id", "=", self.env.uid))
        elif filter_name == "overdue":
            domain.append(("is_procurement_overdue", "=", True))
        elif filter_name == "urgent":
            if "urgency_level" in self._fields:
                domain.append(("urgency_level", "in", ("urgent", "emergency")))
            elif "is_urgency" in self._fields:
                domain.append(("is_urgency", "=", True))

        extra = extra or {}
        kind = extra.get("kind")
        value = extra.get("id")
        if kind == "department":
            domain.append(("department_id", "=", value or False))
        elif kind == "method":
            domain.append(("procurement_method_id", "=", value or False))
        elif kind == "owner":
            domain.append(("procurement_owner_id", "=", value or False))
        elif kind == "aging":
            if value == "fresh":
                domain += [
                    ("state", "=", "sent_to_procurement"),
                    ("days_waiting_procurement", "<", 3),
                ]
            elif value == "warn":
                domain += [
                    ("state", "=", "sent_to_procurement"),
                    ("days_waiting_procurement", ">=", 3),
                    ("days_waiting_procurement", "<=", 7),
                ]
            elif value == "stale":
                domain += [
                    ("state", "=", "sent_to_procurement"),
                    ("days_waiting_procurement", ">", 7),
                ]
            elif value == "progress":
                domain.append(("state", "in", PROCUREMENT_IN_PROGRESS_STATES))
        return domain

    @api.model
    def get_procurement_inbox_count(self):
        """Badge: จำนวนใบที่ยังไม่มีผู้รับงาน"""
        return self.search_count(
            [
                ("state", "=", "sent_to_procurement"),
                ("procurement_owner_id", "=", False),
            ]
        )

    @api.model
    def _cron_recompute_waiting_days(self):
        """รีเฟรชวันค้างทุกวัน (store compute อิงเวลาปัจจุบัน)"""
        cutoff = fields.Datetime.now() - timedelta(days=60)
        recs = self.search(
            [
                ("state", "=", "sent_to_procurement"),
                ("sent_to_procurement_date", "!=", False),
                "|",
                ("sent_to_procurement_date", ">=", cutoff),
                ("is_procurement_overdue", "=", False),
            ]
        )
        recs._compute_days_waiting_procurement()

    def _notify_procurement_inbox_updated(self):
        """บอก dashboard และ badge ของเจ้าหน้าที่พัสดุให้โหลดตัวเลขใหม่"""
        users = self.env["res.users"]
        for xmlid in (
            "purchase_request.group_purchase_request_manager",
            "vpk_tier_validation.group_vpk_procurement_officer",
        ):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                users |= group.users
        bus = self.env["bus.bus"].sudo()
        for partner in users.partner_id:
            bus._sendone(partner, "vpk_procurement_inbox/updated", {})
