# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from dateutil.relativedelta import relativedelta

from odoo import Command, fields, models
from odoo.tools import float_compare


_WA_ROLE = {
    "chairman": "chairman",
    "committee": "member",
    "member": "member",
    "secretary": "secretary",
}


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _wa_role(self, role):
        return _WA_ROLE.get(role, "member")

    def _appointed_committee_lines(self):
        """รายชื่อในคำสั่งแต่งตั้งคณะกรรมการตรวจรับของใบสั่งซื้อนี้.

        ใช้สิทธิ์ระบบอ่านคำสั่งและใบขอซื้อที่ผูกกับใบสั่งซื้อนี้เท่านั้น
        เพราะผู้ตรวจรับเปิดใบตรวจรับได้ แต่กฎสิทธิ์ไม่ให้เปิดใบขอซื้อ
        """
        self.ensure_one()
        if "vpk.official.document" not in self.env:
            return []
        order = self.sudo()
        Document = self.env["vpk.official.document"].sudo()
        requests = order.order_line.mapped("purchase_request_lines.request_id")
        domain = [
            ("document_type", "=", "wa_committee_order"),
            ("state", "!=", "cancelled"),
        ]
        docs = Document.browse()
        if "purchase_id" in Document._fields:
            docs = Document.search(
                domain + [("purchase_id", "=", self.id)], order="id desc"
            )
        if requests:
            docs |= Document.search(
                domain + [("request_id", "in", requests.ids)], order="id desc"
            )
        approved = docs.filtered(lambda document: document.state == "approved")
        chosen = (approved or docs)[:1]
        return chosen.line_ids.sorted(lambda line: (line.sequence, line.id))

    def _get_wa_committee_from_pr(self):
        """ดึงชื่อกรรมการที่แต่งตั้งไว้ ถ้ายังไม่มีคำสั่งใช้รายชื่อบนใบขอซื้อ."""
        self.ensure_one()
        committee_vals = []
        seen = set()
        for member in self._appointed_committee_lines():
            key = member.user_id.id or member.name
            if not key or key in seen:
                continue
            seen.add(key)
            committee_vals.append(
                Command.create(
                    {
                        "name": member.name,
                        "position": member.position or "",
                        "role": self._wa_role(member.role),
                        "employee_id": member.user_id.id or False,
                        "note": member.note or "",
                    }
                )
            )
        if committee_vals:
            return committee_vals
        requests = self.sudo().order_line.mapped("purchase_request_lines.request_id")
        for request in requests:
            if "work_acceptance_committee_ids" not in request._fields:
                continue
            for member in request.work_acceptance_committee_ids:
                key = member.employee_id.id if member.employee_id else member.name
                if not key or key in seen:
                    continue
                seen.add(key)
                user = (
                    member.employee_id.user_id
                    if member.employee_id and member.employee_id.user_id
                    else False
                )
                committee_vals.append(
                    Command.create(
                        {
                            "name": member.name,
                            "position": (
                                member.employee_id.job_title
                                if member.employee_id
                                else ""
                            ),
                            "role": self._wa_role(member.approve_role),
                            "employee_id": user.id if user else False,
                            "note": member.note or "",
                        }
                    )
                )
        return committee_vals

    def _prepare_work_acceptance_lines(self, acceptance=None):
        """บรรทัดใบตรวจรับจากรายการที่ยังตรวจรับไม่ครบ ไม่นับใบตรวจรับใบที่กำลังแก้."""
        self.ensure_one()
        origin_id = False
        if acceptance is not None:
            origin = acceptance._origin
            if origin and isinstance(origin.id, int):
                origin_id = origin.id
        commands = [Command.clear()]
        for line in self.order_line:
            qty = line.product_qty
            for wa_line in line.wa_line_ids:
                if wa_line.wa_id.state == "cancel":
                    continue
                if origin_id and wa_line.wa_id.id == origin_id:
                    continue
                qty -= wa_line.product_qty
            if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
                continue
            commands.append(
                Command.create(
                    {
                        "purchase_line_id": line.id,
                        "name": line.name,
                        "product_uom": line.product_uom.id,
                        "product_id": line.product_id.id,
                        "price_unit": line.price_unit,
                        "product_qty": qty,
                    }
                )
            )
        return commands

    def _prepare_work_acceptance_values(self, acceptance=None):
        """ค่าที่จะใส่ในใบตรวจรับเมื่อเลือกใบสั่งซื้อนี้."""
        self.ensure_one()
        values = {
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "wa_line_ids": self._prepare_work_acceptance_lines(acceptance),
            "committee_ids": [Command.clear(), *self._get_wa_committee_from_pr()],
            "contract_installment_id": False,
            "due_date_contract": False,
            "warranty_end_date": False,
        }
        if self.date_planned:
            values["date_due"] = self.date_planned
        installment = self.sudo().order_line.mapped(
            "purchase_request_lines.contract_installment_id"
        )[:1]
        if installment:
            values["contract_installment_id"] = installment.id
        if self.contract_id and self.contract_id.date_end:
            values["due_date_contract"] = self.contract_id.date_end
        elif (
            "vpk_po_delivery_deadline" in self._fields
            and self.vpk_po_delivery_deadline
        ):
            values["due_date_contract"] = self.vpk_po_delivery_deadline
        if "vpk_po_warranty_months" in self._fields and self.vpk_po_warranty_months:
            base = values["due_date_contract"]
            if not base and self.date_order:
                base = fields.Datetime.to_datetime(self.date_order).date()
            if base:
                values["warranty_end_date"] = base + relativedelta(
                    months=self.vpk_po_warranty_months
                )
        return values

    def action_view_wa(self):
        """Override to include contract/installment defaults and committee."""
        result = super().action_view_wa()
        if not isinstance(result.get("context"), dict):
            return result
        ctx = dict(result["context"])
        if self.env.context.get("create_wa"):
            prepared = self._prepare_work_acceptance_values()
            for key, value in prepared.items():
                if value:
                    ctx["default_%s" % key] = value
        result["context"] = ctx
        return result
