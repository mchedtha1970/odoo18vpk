# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import formatLang, format_datetime


_BILL_TYPES = ("in_invoice", "in_refund")
_BILL_STATES = ("draft", "posted")
_PO_STATES = ("purchase", "done")


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    @api.model
    def get_work_acceptance_dashboard(self):
        """Central board for committee inspection after warehouse receipt or vendor bill."""
        company = self.env.company
        now = fields.Datetime.now()
        goods_rows, goods_count = self._dashboard_goods_rows(company)
        service_rows, service_count = self._dashboard_service_rows(company)
        draft_was = self.search(
            [
                ("state", "=", "draft"),
                ("company_id", "=", company.id),
            ]
        )
        accepted_domain = [
            ("state", "=", "accept"),
            ("company_id", "=", company.id),
            ("date_accept", ">=", fields.Datetime.subtract(now, days=7)),
        ]
        accepted_7d = self.search_count(accepted_domain)
        draft_action = self._dashboard_wa_list_action(
            _("ใบตรวจรับฉบับร่าง"),
            [("state", "=", "draft"), ("company_id", "=", company.id)],
        )
        accepted_action = self._dashboard_wa_list_action(
            _("ตรวจรับแล้ว 7 วัน"), accepted_domain
        )
        all_action = self._dashboard_wa_list_action(
            _("รายการตรวจรับมอบงาน"),
            [("company_id", "=", company.id)],
        )
        return {
            "updated_at": self._dashboard_format_dt(now),
            "all_action": all_action,
            "kpis": [
                {
                    "id": "goods",
                    "label": "สินค้าพร้อมตรวจรับ",
                    "hint": "คลัง QC และรับเข้าคลังแล้ว รอกรรมการตรวจรับ",
                    "value": str(goods_count),
                    "tone": "navy" if goods_count else "muted",
                },
                {
                    "id": "services",
                    "label": "บริการพร้อมตรวจรับ",
                    "hint": "มีใบแจ้งหนี้จากผู้ขายแล้ว รอกรรมการตรวจรับ",
                    "value": str(service_count),
                    "tone": "gold" if service_count else "muted",
                },
                {
                    "id": "draft",
                    "label": "ใบตรวจรับฉบับร่าง",
                    "hint": "สร้างแล้ว ยังไม่กดตรวจรับ",
                    "value": str(len(draft_was)),
                    "tone": "warn" if draft_was else "muted",
                    "action": draft_action,
                },
                {
                    "id": "accepted",
                    "label": "ตรวจรับแล้ว 7 วัน",
                    "hint": "ใบตรวจรับที่กรรมการรับงานแล้ว",
                    "value": str(accepted_7d),
                    "tone": "ok",
                    "action": accepted_action,
                },
            ],
            "goods": {
                "title": "สินค้าที่รับเข้าคลังแล้ว",
                "empty": "ยังไม่มีสินค้าที่คลังรับเข้าและรอตรวจรับ",
                "rows": goods_rows,
            },
            "services": {
                "title": "บริการที่มีใบแจ้งหนี้ส่งมา",
                "empty": "ยังไม่มีบริการที่มีใบแจ้งหนี้และรอตรวจรับ",
                "rows": service_rows,
            },
            "drafts": {
                "title": "ใบตรวจรับฉบับร่าง",
                "empty": "ยังไม่มีใบตรวจรับฉบับร่าง",
                "rows": [self._dashboard_wa_row(wa) for wa in draft_was[:20]],
            },
        }

    @api.model
    def action_open_dashboard_item(self, key):
        """Open the related WA, or create one from the purchase order."""
        if not key or ":" not in str(key):
            return False
        kind, rec_id = str(key).split(":", 1)
        if not rec_id.isdigit():
            return False
        rec_id = int(rec_id)
        if kind == "wa":
            return self._dashboard_form_action("work.acceptance", rec_id)
        if kind == "picking":
            return self._dashboard_form_action("stock.picking", rec_id)
        if kind == "bill":
            return self._dashboard_form_action("account.move", rec_id)
        if kind == "qc":
            return self._dashboard_form_action("vpk.stock.qc", rec_id)
        if kind == "po":
            order = self.env["purchase.order"].browse(rec_id).exists()
            if not order:
                return False
            return self._dashboard_open_or_create_wa(order)
        return False

    def _dashboard_wa_list_action(self, name, domain):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "work.acceptance",
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "domain": domain,
        }

    def _dashboard_open_or_create_wa(self, order):
        drafts = order.wa_ids.filtered(lambda wa: wa.state == "draft")
        if len(drafts) == 1:
            return self._dashboard_form_action("work.acceptance", drafts.id)
        if drafts:
            return {
                "type": "ir.actions.act_window",
                "name": _("ใบตรวจรับมอบงาน"),
                "res_model": "work.acceptance",
                "view_mode": "list,form",
                "domain": [("id", "in", drafts.ids)],
                "context": {"default_purchase_id": order.id},
            }
        return order.with_context(create_wa=True).action_view_wa()

    def _dashboard_form_action(self, model, rec_id):
        return {
            "type": "ir.actions.act_window",
            "res_model": model,
            "res_id": rec_id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def _dashboard_goods_rows(self, company):
        Picking = self.env["stock.picking"]
        pickings = Picking.search(
            [
                ("state", "=", "done"),
                ("picking_type_code", "=", "incoming"),
                ("purchase_id", "!=", False),
                ("company_id", "=", company.id),
            ],
            order="date_done desc",
            limit=400,
        )
        latest = {}
        for picking in pickings:
            order = picking.purchase_id
            if order.id not in latest:
                latest[order.id] = picking
        rows = []
        for order_id, picking in latest.items():
            order = picking.purchase_id
            if order.state not in _PO_STATES:
                continue
            pending_qty, pending_amount = self._dashboard_goods_pending(order)
            if (
                float_compare(pending_qty, 0.0, precision_rounding=0.0001) <= 0
            ):
                continue
            qc = order._vpk_latest_receipt_qc()
            rows.append(
                self._dashboard_po_row(
                    order,
                    source="goods",
                    source_label=picking.name,
                    source_key=f"picking:{picking.id}",
                    when=self._dashboard_format_dt(picking.date_done),
                    pending_qty=pending_qty,
                    pending_amount=pending_amount,
                    qc=qc,
                )
            )
        return rows[:20], len(rows)

    def _dashboard_service_rows(self, company):
        Move = self.env["account.move"]
        bills = Move.search(
            [
                ("move_type", "in", _BILL_TYPES),
                ("state", "in", _BILL_STATES),
                ("company_id", "=", company.id),
                ("invoice_line_ids.purchase_line_id", "!=", False),
            ],
            order="invoice_date desc, id desc",
            limit=400,
        )
        latest = {}
        for bill in bills:
            po_ids = bill.invoice_line_ids.purchase_line_id.order_id
            for order in po_ids:
                if order.id not in latest:
                    latest[order.id] = bill
        rows = []
        for order_id, bill in latest.items():
            order = self.env["purchase.order"].browse(order_id)
            if order.state not in _PO_STATES:
                continue
            pending_qty, pending_amount = self._dashboard_service_pending(order)
            if (
                float_compare(pending_qty, 0.0, precision_rounding=0.0001) <= 0
            ):
                continue
            rows.append(
                self._dashboard_po_row(
                    order,
                    source="service",
                    source_label=bill.name if bill.name not in (False, "/") else _("ใบแจ้งหนี้ฉบับร่าง"),
                    source_key=f"bill:{bill.id}",
                    when=self._dashboard_format_date(bill.invoice_date),
                    pending_qty=pending_qty,
                    pending_amount=pending_amount,
                )
            )
        return rows[:20], len(rows)

    def _dashboard_goods_pending(self, order):
        qty = 0.0
        amount = 0.0
        for line in order.order_line:
            if line.display_type or self._dashboard_is_service_line(line):
                continue
            pending = max((line.qty_received or 0.0) - (line.qty_accepted or 0.0), 0.0)
            if float_compare(pending, 0.0, precision_rounding=line.product_uom.rounding or 0.01) <= 0:
                continue
            qty += pending
            amount += pending * (line.price_unit or 0.0)
        return qty, amount

    def _dashboard_service_pending(self, order):
        qty = 0.0
        amount = 0.0
        for line in order.order_line:
            if line.display_type or not self._dashboard_is_service_line(line):
                continue
            pending = max((line.product_qty or 0.0) - (line.qty_accepted or 0.0), 0.0)
            if float_compare(pending, 0.0, precision_rounding=line.product_uom.rounding or 0.01) <= 0:
                continue
            qty += pending
            amount += pending * (line.price_unit or 0.0)
        return qty, amount

    def _dashboard_is_service_line(self, line):
        nature = getattr(line.order_id, "procurement_nature", "buy") or "buy"
        if nature in ("hire", "lease"):
            return line.product_id.type == "service" or not line.product_id.is_storable
        return line.product_id.type == "service"

    def _dashboard_po_row(
        self,
        order,
        source,
        source_label,
        source_key,
        when,
        pending_qty,
        pending_amount,
        qc=False,
    ):
        drafts = order.wa_ids.filtered(lambda wa: wa.state == "draft")
        accepted = order.wa_ids.filtered(lambda wa: wa.state == "accept")
        if drafts:
            status = "draft"
            status_label = _("มีใบร่าง")
        elif accepted:
            status = "partial"
            status_label = _("ตรวจรับบางส่วน")
        else:
            status = "ready"
            status_label = _("รอสร้างใบตรวจรับ")
        wa = drafts[:1] or accepted[:1]
        row = {
            "key": f"po:{order.id}",
            "source": source,
            "po_name": order.name,
            "vendor": order.partner_id.display_name,
            "committee": self._dashboard_committee_label(order),
            "source_label": source_label,
            "source_key": source_key,
            "when": when,
            "qty": self._dashboard_format_qty(pending_qty),
            "amount": self._dashboard_format_money(pending_amount, order.currency_id),
            "status": status,
            "status_label": status_label,
            "wa_key": f"wa:{wa.id}" if wa else False,
            "wa_name": wa.name if wa else False,
        }
        row.update(self._dashboard_qc_fields(qc))
        return row

    def _dashboard_wa_row(self, wa):
        qc = wa.qc_id or (
            wa.purchase_id._vpk_latest_receipt_qc() if wa.purchase_id else False
        )
        row = {
            "key": f"wa:{wa.id}",
            "source": "draft",
            "po_name": wa.purchase_id.name or "-",
            "vendor": wa.partner_id.display_name,
            "committee": self._dashboard_committee_label(wa.purchase_id),
            "source_label": wa.name,
            "source_key": f"wa:{wa.id}",
            "when": self._dashboard_format_dt(wa.date_due or wa.date_receive),
            "qty": self._dashboard_format_qty(sum(wa.wa_line_ids.mapped("product_qty"))),
            "amount": "",
            "status": "draft",
            "status_label": _("ฉบับร่าง"),
            "wa_key": f"wa:{wa.id}",
            "wa_name": wa.name,
        }
        row.update(self._dashboard_qc_fields(qc))
        return row

    def _dashboard_qc_fields(self, qc):
        if not qc:
            return {"qc_label": "", "qc_key": False}
        return {
            "qc_label": qc.name,
            "qc_key": f"qc:{qc.id}",
        }

    def _dashboard_committee_label(self, order):
        if not order:
            return ""
        names = []
        seen = set()

        def add_members(members):
            for member in members:
                if getattr(member, "confirm_state", False) == "declined":
                    continue
                name = member.name or (
                    member.employee_id.display_name if member.employee_id else ""
                )
                if not name or name in seen:
                    continue
                seen.add(name)
                if member.approve_role == "chairman":
                    names.insert(0, name)
                else:
                    names.append(name)

        for request in order._vpk_linked_purchase_requests():
            if "work_acceptance_committee_ids" in request._fields:
                add_members(request.work_acceptance_committee_ids)
        for requisition in order._vpk_linked_requisitions():
            if "work_acceptance_committee_ids" in requisition._fields:
                add_members(requisition.work_acceptance_committee_ids)
        return " · ".join(names[:4])

    def _dashboard_format_money(self, amount, currency):
        return formatLang(self.env, amount or 0.0, currency_obj=currency)

    def _dashboard_format_qty(self, qty):
        return formatLang(self.env, qty or 0.0, digits=2)

    def _dashboard_format_dt(self, value):
        if not value:
            return ""
        return format_datetime(self.env, value, tz="Asia/Bangkok", dt_format="dd/MM/yyyy HH:mm")

    def _dashboard_format_date(self, value):
        if not value:
            return ""
        return value.strftime("%d/%m/%Y")
