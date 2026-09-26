# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
    is_procurement_overdue = fields.Boolean(
        string="ค้างเกิน 3 วัน",
        compute="_compute_days_waiting_procurement",
        store=True,
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
            }
        )
        return res

    def button_draft(self):
        res = super().button_draft()
        self.write(
            {
                "sent_to_procurement_date": False,
                "procurement_owner_id": False,
                "procurement_claimed_date": False,
            }
        )
        return res

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
    def get_procurement_inbox_stats(self):
        """KPI สำหรับ dashboard พัสดุ"""
        base = [("state", "=", "sent_to_procurement")]
        Request = self.env["purchase.request"]
        total = Request.search_count(base)
        unassigned = Request.search_count(
            base + [("procurement_owner_id", "=", False)]
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
        return {
            "total": total,
            "unassigned": unassigned,
            "mine": mine,
            "overdue": overdue,
            "urgent": urgent,
            "has_urgency": bool(
                "urgency_level" in self._fields or "is_urgency" in self._fields
            ),
        }

    @api.model
    def get_procurement_inbox_domain(self, filter_name="total"):
        domain = [("state", "=", "sent_to_procurement")]
        if filter_name == "unassigned":
            domain.append(("procurement_owner_id", "=", False))
        elif filter_name == "mine":
            domain.append(("procurement_owner_id", "=", self.env.uid))
        elif filter_name == "overdue":
            domain.append(("is_procurement_overdue", "=", True))
        elif filter_name == "urgent":
            if "urgency_level" in self._fields:
                domain.append(("urgency_level", "in", ("urgent", "emergency")))
            elif "is_urgency" in self._fields:
                domain.append(("is_urgency", "=", True))
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
