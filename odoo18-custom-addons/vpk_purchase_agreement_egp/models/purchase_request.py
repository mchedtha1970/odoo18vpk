# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    egp_requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="เอกสาร e-GP",
        compute="_compute_egp_requisition_id",
    )
    egp_project_reference = fields.Char(
        string="เลขที่โครงการ (e-GP)",
        related="egp_requisition_id.egp_reference",
        readonly=True,
    )
    egp_project_name = fields.Char(
        string="ชื่อโครงการ",
        related="egp_requisition_id.egp_project_name",
        readonly=True,
    )
    can_create_egp_rfq = fields.Boolean(
        compute="_compute_egp_requisition_id",
    )
    can_send_to_egp = fields.Boolean(
        compute="_compute_can_send_to_egp",
    )
    egp_flow_stage = fields.Selection(
        selection="_selection_egp_flow_stage",
        string="e-GP Flow Stage",
        compute="_compute_egp_flow_stage",
    )
    is_egp_procurement_flow = fields.Boolean(
        compute="_compute_egp_flow_stage",
    )
    egp_flow_html = fields.Html(
        string="e-GP Workflow",
        compute="_compute_egp_flow_html",
        sanitize=False,
    )

    @api.model
    def _selection_egp_flow_stage(self):
        return self.env["purchase.requisition"]._selection_egp_flow_stage()

    def _get_egp_requisitions(self):
        self.ensure_one()
        from_lines = self.mapped("line_ids.requisition_lines.requisition_id").filtered(
            lambda record: record.requisition_type == "egp_procurement"
        )
        from_link = self.env["purchase.requisition"].search(
            [
                ("purchase_request_id", "=", self.id),
                ("requisition_type", "=", "egp_procurement"),
            ]
        )
        return from_lines | from_link

    def _get_egp_requisition_for_rfq(self):
        self.ensure_one()
        requisitions = self._get_egp_requisitions()
        confirmed = requisitions.filtered(lambda record: record.state == "confirmed")
        return confirmed[:1] or requisitions[:1]

    @api.depends(
        "state",
        "to_create",
        "line_ids.requisition_lines.requisition_id",
        "line_ids.requisition_lines.requisition_id.state",
        "line_ids.requisition_lines.requisition_id.egp_bid_ids.is_winner",
        "line_ids.requisition_lines.requisition_id.award_report_ids.state",
    )
    def _compute_egp_requisition_id(self):
        for request in self:
            requisition = request._get_egp_requisition_for_rfq()
            request.egp_requisition_id = requisition
            request.can_create_egp_rfq = (
                request.to_create == "purchase_agreement"
                and request.state in ("approved", "in_progress")
                and bool(requisition)
                and requisition.state == "confirmed"
                and bool(requisition.egp_bid_ids.filtered("is_winner"))
                and requisition.egp_award_approved
            )

    def action_open_create_rfq_wizard(self):
        self.ensure_one()
        requisition = self._get_egp_requisition_for_rfq()
        if not requisition:
            raise UserError(
                _("Please create a Purchase Agreement from this request first.")
            )
        if requisition.state != "confirmed":
            raise UserError(
                _("Please confirm Purchase Agreement %(agreement)s before creating RFQs.")
                % {"agreement": requisition.display_name}
            )
        return requisition.action_open_create_rfq_wizard()

    @api.depends(
        "state",
        "to_create",
        "line_ids.requisition_lines.requisition_id.state",
        "line_ids.requisition_lines.requisition_id.egp_flow_stage",
    )
    def _compute_egp_flow_stage(self):
        for request in self:
            if request.to_create != "purchase_agreement":
                request.is_egp_procurement_flow = False
                request.egp_flow_stage = False
                continue
            request.is_egp_procurement_flow = True
            requisitions = request.mapped("line_ids.requisition_lines.requisition_id").filtered(
                lambda record: record.requisition_type == "egp_procurement"
            )
            if requisitions:
                request.egp_flow_stage = requisitions[0].egp_flow_stage
                continue
            if request.state in ("draft", "to_approve", "rejected"):
                request.egp_flow_stage = "pr_submit"
            elif request.state in ("approved", "in_progress"):
                request.egp_flow_stage = "pr_approved"
            elif request.state == "done":
                request.egp_flow_stage = "done"
            else:
                request.egp_flow_stage = "pr_submit"

    @api.depends("egp_flow_stage", "is_egp_procurement_flow")
    def _compute_egp_flow_html(self):
        Requisition = self.env["purchase.requisition"]
        steps = Requisition._get_egp_flow_step_definitions()
        order = Requisition.EGP_FLOW_STAGE_ORDER
        for request in self:
            if not request.is_egp_procurement_flow:
                request.egp_flow_html = False
                continue
            current = request.egp_flow_stage or "pr_submit"
            if current == "cancel":
                current_index = len(order)
            elif current in order:
                current_index = order.index(current)
            else:
                current_index = 0
            items = []
            for code, title, help_text in steps:
                step_index = order.index(code)
                if current == "cancel":
                    status = "cancelled"
                elif current == "done" or step_index < current_index:
                    status = "done"
                elif step_index == current_index:
                    status = "current"
                else:
                    status = "pending"
                items.append((status, title, help_text))
            request.egp_flow_html = Requisition._render_egp_flow_html(items)

    @api.depends(
        "state",
        "to_create",
        "line_ids",
        "line_ids.product_qty",
        "line_ids.cancelled",
        "line_ids.requisition_lines.requisition_id",
    )
    def _compute_can_send_to_egp(self):
        for request in self:
            request.can_send_to_egp = request._vpk_can_send_to_egp()

    def _vpk_can_send_to_egp(self):
        self.ensure_one()
        if not isinstance(self.id, int):
            return False
        if self.to_create != "purchase_agreement":
            return False
        if self.state not in ("approved", "to_approve", "sent_to_procurement"):
            return False
        if not self.line_ids.filtered(lambda line: not line.cancelled and line.product_qty):
            return False
        if self._get_egp_requisitions():
            return False
        if not hasattr(self, "_vpk_related_documents_all_approved"):
            return self.state == "approved"
        return self._vpk_related_documents_all_approved()

    def action_send_to_egp(self):
        self.ensure_one()
        if not self._vpk_can_send_to_egp():
            raise UserError(
                _(
                    "ส่งเข้าระบบ e-GP ได้เมื่อเอกสารที่เกี่ยวข้องอนุมัติครบทุกฉบับ "
                    "และใบขอซื้อยังไม่มีกระบวนการ e-GP"
                )
            )
        if self.state != "approved":
            self.sudo().with_user(self.env.user).with_context(
                skip_validation_check=True
            ).button_approved()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "purchase_request_to_requisition.action_purchase_request_make_purchase_requisition"
        )
        action["context"] = {
            **dict(self.env.context),
            "active_id": self.id,
            "active_ids": self.ids,
            "active_model": "purchase.request",
        }
        return action
