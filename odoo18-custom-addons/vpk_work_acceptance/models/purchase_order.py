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

    def _vpk_latest_receipt_picking(self):
        self.ensure_one()
        pickings = self.picking_ids.filtered(
            lambda picking: picking.picking_type_code == "incoming"
            and picking.state == "done"
        )
        return pickings.sorted(
            key=lambda picking: picking.date_done or picking.create_date or picking.id,
            reverse=True,
        )[:1]

    def _vpk_latest_receipt_qc(self):
        self.ensure_one()
        picking = self._vpk_latest_receipt_picking()
        if not picking:
            return self.env["vpk.stock.qc"]
        return picking.qc_id or picking.qc_ids[:1]

    def _vpk_linked_purchase_requests(self):
        """ใบขอซื้อที่ผูกกับใบสั่งซื้อนี้."""
        self.ensure_one()
        Request = self.env["purchase.request"]
        requests = Request.browse()
        if "purchase_request_lines" in self.order_line._fields:
            requests |= self.sudo().order_line.mapped("purchase_request_lines.request_id")
        if "source_request_ids" in self._fields:
            requests |= self.source_request_ids
        contract = self.contract_id
        if contract:
            if "purchase_request_ids" in contract._fields:
                requests |= contract.purchase_request_ids
            if "purchase_request_id" in contract._fields:
                requests |= contract.purchase_request_id
        return requests.sudo()

    def _vpk_linked_requisitions(self):
        """กระบวนการ e-GP ที่ผูกกับใบสั่งซื้อนี้."""
        self.ensure_one()
        Requisition = self.env["purchase.requisition"]
        recs = Requisition.browse()
        for name in ("source_requisition_id", "requisition_id"):
            if name in self._fields and self[name]:
                recs |= self[name]
        if self.contract_id and "requisition_id" in self.contract_id._fields:
            recs |= self.contract_id.requisition_id
        for request in self._vpk_linked_purchase_requests():
            if "egp_requisition_id" in request._fields:
                recs |= request.egp_requisition_id
            if "egp_requisition_ids" in request._fields:
                recs |= request.egp_requisition_ids
        return recs.sudo()

    def _vpk_wa_committee_source_labels(self):
        self.ensure_one()
        labels = []
        for request in self._vpk_linked_purchase_requests():
            if request.work_acceptance_committee_ids:
                labels.append("ใบขอซื้อ %s" % request.name)
        for requisition in self._vpk_linked_requisitions():
            if (
                "work_acceptance_committee_ids" in requisition._fields
                and requisition.work_acceptance_committee_ids
            ):
                labels.append(
                    "e-GP %s"
                    % (
                        requisition.egp_reference
                        or requisition.name
                        or requisition.display_name
                    )
                )
        return labels

    def _committee_member_command(self, member, origin, sequence):
        if getattr(member, "confirm_state", False) == "declined":
            return False
        name = member.name
        if not name and member.employee_id:
            name = member.employee_id.display_name
        if not name:
            return False
        employee = member.employee_id
        user = employee.user_id if employee and employee.user_id else False
        position = ""
        if employee:
            position = employee.job_title or (
                employee.job_id.name if employee.job_id else ""
            )
        note = member.note or ""
        if origin:
            note = " · ".join(part for part in (origin, note) if part)
        return Command.create(
            {
                "sequence": sequence,
                "name": name,
                "position": position,
                "role": self._wa_role(member.approve_role),
                "employee_id": user.id if user else False,
                "origin": origin,
                "note": note,
            }
        )

    def _get_wa_committee_from_pr(self):
        """ดึงรายชื่อคณะกรรมการตรวจรับจากใบขอซื้อ และการแต่งตั้งใน e-GP."""
        self.ensure_one()
        committee_vals = []
        seen = set()
        sequence = 10

        def add_members(members, origin):
            nonlocal sequence
            ordered = members.sorted(
                key=lambda member: (
                    0
                    if member.approve_role == "chairman"
                    else 1
                    if member.approve_role == "secretary"
                    else 2,
                    member.id,
                )
            )
            for member in ordered:
                key = member.employee_id.id if member.employee_id else member.name
                if not key or key in seen:
                    continue
                command = self._committee_member_command(member, origin, sequence)
                if not command:
                    continue
                seen.add(key)
                committee_vals.append(command)
                sequence += 10

        for request in self._vpk_linked_purchase_requests():
            if "work_acceptance_committee_ids" not in request._fields:
                continue
            add_members(
                request.work_acceptance_committee_ids,
                "ใบขอซื้อ %s" % request.name,
            )
        for requisition in self._vpk_linked_requisitions():
            if "work_acceptance_committee_ids" not in requisition._fields:
                continue
            add_members(
                requisition.work_acceptance_committee_ids,
                "e-GP %s"
                % (
                    requisition.egp_reference
                    or requisition.name
                    or requisition.display_name
                ),
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
                if key == "committee_ids":
                    ctx["default_committee_ids"] = [
                        command
                        for command in value
                        if command and command[0] == Command.CREATE
                    ]
                elif value:
                    ctx["default_%s" % key] = value
        result["context"] = ctx
        return result
