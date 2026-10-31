# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from markupsafe import Markup


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    EGP_FLOW_STAGE_ORDER = (
        "pr_submit",
        "pr_approved",
        "draft",
        "confirmed",
        "egp_docs",
        "rfq",
        "compare",
        "awarded",
        "done",
    )

    requisition_type = fields.Selection(
        selection_add=[("egp_procurement", "e-GP Procurement")],
        ondelete={"egp_procurement": "set default"},
    )
    egp_reference = fields.Char(
        string="e-GP Project Reference",
        tracking=True,
        help="Main e-GP project or tender reference used on RFQs.",
    )
    egp_project_name = fields.Char(
        string="Project Name",
        tracking=True,
        help="Project name for this e-GP procurement.",
    )
    egp_document_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.document",
        inverse_name="requisition_id",
        string="เอกสารที่เปิดในระบบ e-GP",
        copy=False,
    )
    egp_bid_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.bid",
        inverse_name="requisition_id",
        string="ผู้เสนอราคา",
        copy=False,
    )
    egp_bid_line_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.bid.line",
        inverse_name="requisition_id",
        string="รายการเปรียบเทียบราคา",
        copy=False,
    )
    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="ประเภทการสั่งซื้อ",
        ondelete="restrict",
        copy=False,
    )
    purchase_type_id = fields.Many2one(
        comodel_name="purchase.type",
        string="ระเบียบ",
        ondelete="restrict",
        copy=False,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="ซื้อด้วยวิธีการ",
        ondelete="restrict",
        copy=False,
    )
    procurement_nature = fields.Selection(
        selection=[
            ("buy", "ซื้อ"),
            ("hire", "จ้าง"),
            ("lease", "เช่า"),
        ],
        string="ประเภทการจัดหา",
        tracking=True,
        copy=True,
        default="buy",
    )
    egp_item_kind = fields.Selection(
        selection=[
            ("material", "วัสดุ"),
            ("asset", "ครุภัณฑ์"),
            ("project", "โครงการ"),
            ("construction", "ก่อสร้าง"),
        ],
        string="พัสดุที่จัดหา",
        tracking=True,
        copy=True,
    )
    egp_disbursement_type = fields.Selection(
        selection=[
            ("gfmis", "ผ่าน GFMIS"),
            ("non_gfmis", "ไม่ผ่าน GFMIS"),
        ],
        string="การเบิกจ่ายเงิน",
        tracking=True,
        copy=True,
    )
    egp_consideration_type = fields.Selection(
        selection=[
            ("total", "ราคารวม"),
            ("line", "ราคาต่อรายการ"),
            ("unit", "ราคาต่อหน่วย"),
        ],
        string="การพิจารณา",
        tracking=True,
        copy=True,
        default="total",
    )
    purchase_request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="การอ้างอิง",
        tracking=True,
        index=True,
        copy=False,
        required=False,
        help="ใบขอซื้อ (ถ้ามี) กระบวนการ e-bidding จากแผนไม่ต้องมีใบขอซื้อก่อนหาผู้ชนะ",
    )
    purchase_request_amount_total = fields.Monetary(
        string="งบประมาณโครงการ",
        currency_field="currency_id",
        compute="_compute_purchase_request_amount_total",
        store=True,
        readonly=True,
    )
    price_mid_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="requisition_id",
        string="คณะกรรมการจัดทำรายละเอียดคุณลักษณะของพัสดุและกำหนดราคากลาง",
        domain=[("committee_type", "=", "price_mid")],
        copy=True,
    )
    procurement_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="requisition_id",
        string="คณะกรรมการจัดซื้อจัดจ้าง",
        domain=[("committee_type", "=", "procurement")],
        copy=True,
    )
    work_acceptance_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="requisition_id",
        string="คณะกรรมการตรวจรับ",
        domain=[("committee_type", "=", "work_acceptance")],
        copy=True,
    )
    is_egp_procurement = fields.Boolean(
        compute="_compute_is_egp_procurement",
    )
    egp_flow_stage = fields.Selection(
        selection="_selection_egp_flow_stage",
        string="e-GP Flow Stage",
        compute="_compute_egp_flow_stage",
        store=True,
        readonly=False,
        copy=False,
    )
    egp_flow_stage_manual = fields.Boolean(
        string="e-GP Flow Stage Set Manually",
        copy=False,
        help="ติดเมื่อผู้ใช้กดแถบขั้นตอนเอง จากนั้นระบบจะไม่ทับค่านั้น",
    )
    egp_flow_html = fields.Html(
        string="e-GP Workflow",
        compute="_compute_egp_flow_html",
        sanitize=False,
    )

    @api.model
    def _selection_egp_flow_stage(self):
        return [
            ("pr_submit", "Submit PR"),
            ("pr_approved", "PR Approved"),
            ("draft", "Draft PA"),
            ("confirmed", "Confirm PA"),
            ("egp_docs", "e-GP Documents"),
            ("rfq", "เชิญและรับข้อเสนอ"),
            ("compare", "Compare Prices"),
            ("awarded", "Award Vendor"),
            ("done", "Closed"),
            ("cancel", "Cancelled"),
        ]

    @api.model
    def _get_egp_flow_step_definitions(self):
        return [
            ("pr_submit", _("1. Submit PR"), _("Create purchase request and submit for approval.")),
            ("pr_approved", _("2. PR Approved"), _("Create Purchase Agreement from approved PR.")),
            ("draft", _("3. Draft PA"), _("Review products and confirm purchase agreement.")),
            ("confirmed", _("4. Confirm PA"), _("Start e-GP procurement on the agreement.")),
            ("egp_docs", _("5. e-GP Documents"), _("Record announcements, TOR, and contract in e-GP tab.")),
            (
                "rfq",
                _("6. Invite / Collect Bids"),
                _("ออกใบเชิญเสนอราคา รับข้อเสนอ และบันทึกราคาในกระบวนการ eGP"),
            ),
            ("compare", _("7. Compare Prices"), _("เปรียบเทียบราคาและเลือกผู้ชนะ")),
            ("awarded", _("8. Award Vendor"), _("มีคำสั่งซื้อที่ยืนยันแล้วของผู้ชนะ")),
            ("done", _("9. Closed"), _("ปิดข้อตกลงจากปุ่มปิดข้อตกลง หรือเมื่อคำสั่งซื้อถูกยืนยัน")),
        ]

    @api.depends("requisition_type")
    def _compute_is_egp_procurement(self):
        for record in self:
            record.is_egp_procurement = record.requisition_type == "egp_procurement"

    def _egp_project_budget_amount(self):
        self.ensure_one()
        return self.purchase_request_id.estimated_cost or 0.0

    @api.depends("purchase_request_id", "purchase_request_id.estimated_cost")
    def _compute_purchase_request_amount_total(self):
        for record in self:
            record.purchase_request_amount_total = record._egp_project_budget_amount()

    def _suggested_egp_flow_stage(self):
        self.ensure_one()
        if self.requisition_type != "egp_procurement":
            return False
        if self.state == "cancel":
            return "cancel"
        if self.state == "done":
            return "done"
        if self.purchase_ids.filtered(lambda po: po.state == "purchase"):
            return "awarded"
        if self.egp_bid_ids or len(self.purchase_ids) >= 2:
            return "compare"
        if self.egp_invitation_ids or self.purchase_ids:
            return "rfq"
        if self.egp_document_ids:
            return "egp_docs"
        if self.state == "confirmed":
            return "confirmed"
        return "draft"

    @api.depends(
        "state",
        "requisition_type",
        "egp_document_ids",
        "egp_invitation_ids",
        "egp_invitation_ids.state",
        "egp_bid_ids",
        "purchase_ids",
        "purchase_ids.state",
        "egp_flow_stage_manual",
    )
    def _compute_egp_flow_stage(self):
        manual = self.filtered("egp_flow_stage_manual")
        for record in self - manual:
            origin = record._origin
            if (
                origin
                and origin.egp_flow_stage_manual
                and not self.env.context.get("egp_flow_auto")
            ):
                record.egp_flow_stage = (
                    origin.egp_flow_stage or record._suggested_egp_flow_stage()
                )
            else:
                record.egp_flow_stage = record._suggested_egp_flow_stage()
        if not manual:
            return
        persisted = manual.filtered(lambda record: isinstance(record.id, int))
        stored = {}
        if persisted:
            self.env.cr.execute(
                """
                SELECT id, egp_flow_stage
                  FROM purchase_requisition
                 WHERE id IN %s
                """,
                [tuple(persisted.ids)],
            )
            stored = dict(self.env.cr.fetchall())
        for record in manual:
            origin = record._origin
            if origin and origin.egp_flow_stage and record.id != origin.id:
                record.egp_flow_stage = origin.egp_flow_stage
                continue
            record.egp_flow_stage = stored.get(record.id) or record._suggested_egp_flow_stage()

    @api.depends("egp_flow_stage", "requisition_type")
    def _compute_egp_flow_html(self):
        steps = self._get_egp_flow_step_definitions()
        for record in self:
            if record.requisition_type != "egp_procurement":
                record.egp_flow_html = False
                continue
            current = record.egp_flow_stage or "draft"
            if current == "cancel":
                current_index = len(self.EGP_FLOW_STAGE_ORDER)
            elif current in self.EGP_FLOW_STAGE_ORDER:
                current_index = self.EGP_FLOW_STAGE_ORDER.index(current)
            else:
                current_index = 0
            items = []
            for code, title, help_text in steps:
                step_index = self.EGP_FLOW_STAGE_ORDER.index(code)
                if current == "cancel":
                    status = "cancelled"
                elif code in ("pr_submit", "pr_approved"):
                    status = "done"
                elif current == "done" or step_index < current_index:
                    status = "done"
                elif step_index == current_index:
                    status = "current"
                else:
                    status = "pending"
                items.append((status, title, help_text))
            record.egp_flow_html = self._render_egp_flow_html(items)

    @api.model
    def _render_egp_flow_html(self, items):
        rows = ['<div class="vpk_egp_flow">']
        for status, title, help_text in items:
            rows.append(
                '<div class="vpk_egp_flow_step vpk_egp_flow_%s">'
                '<div class="vpk_egp_flow_title">%s</div>'
                '<div class="vpk_egp_flow_help">%s</div>'
                "</div>"
                % (status, title, help_text)
            )
        rows.append("</div>")
        return Markup("".join(rows))

    def _committee_commands_from_request(self, request, committee_type, source_field):
        members = getattr(request, source_field, self.env["procurement.committee"])
        return [
            Command.create(
                {
                    "employee_id": member.employee_id.id,
                    "name": member.name,
                    "approve_role": member.approve_role,
                    "committee_type": committee_type,
                    "note": member.note,
                    "confirm_state": member.confirm_state,
                    "confirm_request_date": member.confirm_request_date,
                    "confirm_reply_date": member.confirm_reply_date,
                    "confirm_note": member.confirm_note,
                    "confirm_requested_by": member.confirm_requested_by.id,
                }
            )
            for member in members
        ]

    def _copy_committees_from_purchase_request(self):
        for record in self:
            request = record.purchase_request_id
            if not request:
                continue
            vals = {}
            if not record.price_mid_committee_ids and "price_mid_committee_ids" in request._fields:
                vals["price_mid_committee_ids"] = self._committee_commands_from_request(
                    request, "price_mid", "price_mid_committee_ids"
                )
            if not record.procurement_committee_ids:
                vals["procurement_committee_ids"] = self._committee_commands_from_request(
                    request, "procurement", "procurement_committee_ids"
                )
            if not record.work_acceptance_committee_ids:
                vals["work_acceptance_committee_ids"] = self._committee_commands_from_request(
                    request, "work_acceptance", "work_acceptance_committee_ids"
                )
            if vals:
                record.write(vals)

    @api.onchange("purchase_request_id")
    def _onchange_purchase_request_id(self):
        for record in self:
            if record.purchase_request_id:
                record.reference = record.purchase_request_id.name
                if record.purchase_request_id.procurement_type_id:
                    record.procurement_type_id = record.purchase_request_id.procurement_type_id
                if record.purchase_request_id.purchase_type_id:
                    record.purchase_type_id = record.purchase_request_id.purchase_type_id
                if record.purchase_request_id.procurement_method_id:
                    record.procurement_method_id = record.purchase_request_id.procurement_method_id
                if record.purchase_request_id.procurement_nature:
                    record.procurement_nature = record.purchase_request_id.procurement_nature
                if (
                    "budget_section_key" in record.purchase_request_id._fields
                    and record.purchase_request_id.budget_section_key
                ):
                    record.egp_item_kind = record.purchase_request_id.budget_section_key
                if not record.price_mid_committee_ids:
                    record.price_mid_committee_ids = self._committee_commands_from_request(
                        record.purchase_request_id, "price_mid", "price_mid_committee_ids"
                    )
                if not record.procurement_committee_ids:
                    record.procurement_committee_ids = self._committee_commands_from_request(
                        record.purchase_request_id, "procurement", "procurement_committee_ids"
                    )
                if not record.work_acceptance_committee_ids:
                    record.work_acceptance_committee_ids = self._committee_commands_from_request(
                        record.purchase_request_id,
                        "work_acceptance",
                        "work_acceptance_committee_ids",
                    )

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(["requisition_type", "company_id"])
        for vals in vals_list:
            requisition_type = vals.get("requisition_type", defaults.get("requisition_type"))
            company_id = vals.get("company_id", defaults.get("company_id"))
            if requisition_type == "egp_procurement":
                vals["name"] = self.env["ir.sequence"].with_company(company_id).next_by_code(
                    "purchase.requisition.egp.procurement"
                )
            pr_id = vals.get("purchase_request_id")
            if pr_id and not vals.get("reference"):
                pr = self.env["purchase.request"].browse(pr_id)
                vals["reference"] = pr.name
        records = super().create(vals_list)
        for record in records.filtered(lambda rec: rec.requisition_type == "egp_procurement"):
            record.name = self.env["ir.sequence"].with_company(record.company_id).next_by_code(
                "purchase.requisition.egp.procurement"
            )
        records._copy_committees_from_purchase_request()
        return records

    def write(self, vals):
        if "egp_flow_stage" in vals and not self.env.context.get("egp_flow_auto"):
            vals = dict(vals, egp_flow_stage_manual=True)
        if vals.get("purchase_request_id") and "reference" not in vals:
            pr = self.env["purchase.request"].browse(vals["purchase_request_id"])
            vals = dict(vals, reference=pr.name)
        requisitions_to_rename = self.env["purchase.requisition"]
        if "requisition_type" in vals or "company_id" in vals:
            requisitions_to_rename = self.filtered(
                lambda record: record.requisition_type
                != vals.get("requisition_type", record.requisition_type)
                or record.company_id.id != vals.get("company_id", record.company_id.id)
            )
        res = super().write(vals)
        if vals.get("purchase_request_id"):
            self._copy_committees_from_purchase_request()
        for requisition in requisitions_to_rename:
            if requisition.state != "draft":
                raise UserError(
                    _("You cannot change the Agreement Type or Company of a not draft purchase agreement.")
                )
            if requisition.requisition_type in ("purchase_template", "egp_procurement"):
                requisition.date_start = requisition.date_end = False
            if requisition.requisition_type == "blanket_order":
                code = "purchase.requisition.blanket.order"
            elif requisition.requisition_type == "purchase_template":
                code = "purchase.requisition.purchase.template"
            else:
                code = "purchase.requisition.egp.procurement"
            requisition.name = self.env["ir.sequence"].with_company(requisition.company_id).next_by_code(code)
        if any(key in vals for key in ("egp_bid_ids", "egp_bid_line_ids")):
            self._summarize_offered_totals()
        return res

    def action_confirm(self):
        egp_requisitions = self.filtered(lambda record: record.requisition_type == "egp_procurement")
        other_requisitions = self - egp_requisitions
        for requisition in egp_requisitions:
            if not requisition.line_ids:
                raise UserError(
                    _(
                        "You cannot confirm agreement '%(agreement)s' because it does not contain any product lines.",
                        agreement=requisition.name,
                    )
                )
            for line in requisition.line_ids:
                if line.product_qty <= 0.0:
                    raise UserError(
                        _("You cannot confirm an e-GP agreement with lines missing a quantity.")
                    )
        if other_requisitions:
            super(PurchaseRequisition, other_requisitions).action_confirm()
        if egp_requisitions:
            egp_requisitions.write({"state": "confirmed"})
            egp_requisitions._purchase_request_confirm_message()
        return True

    def _update_egp_reference_from_documents(self):
        for requisition in self.filtered(lambda record: record.requisition_type == "egp_procurement"):
            invitation = requisition.egp_document_ids.filtered(
                lambda doc: doc.document_type_id.code == "invitation" and doc.egp_reference
            )[:1]
            if invitation:
                requisition.egp_reference = invitation.egp_reference

    def _get_rfq_origin(self, egp_bid_reference=None):
        self.ensure_one()
        parts = [part for part in [self.egp_reference, self.name, egp_bid_reference] if part]
        return ", ".join(parts)

    def _get_rfq_source_pr_lines(self):
        """PR lines used to build RFQ products."""
        self.ensure_one()
        if not self.purchase_request_id:
            return self.env["purchase.request.line"]
        return self.purchase_request_id.line_ids.filtered(
            lambda line: not line.cancelled and line.product_id and line.product_qty > 0
        )

    def _get_egp_winner_bid(self):
        self.ensure_one()
        return self.egp_bid_ids.filtered("is_winner")[:1]

    def _split_winner_line_amounts(self, source_lines):
        """Allocate winner bid amount across RFQ source lines."""
        self.ensure_one()
        if not source_lines:
            return []
        winner = self._get_egp_winner_bid()
        amount_total = winner.amount_total if winner else 0.0
        if not amount_total:
            return [0.0] * len(source_lines)
        if len(source_lines) == 1:
            return [amount_total]
        weights = []
        for line in source_lines:
            weight = getattr(line, "estimated_cost", None) or 0.0
            if not weight:
                weight = line.product_qty or 0.0
            weights.append(weight)
        weight_sum = sum(weights)
        if weight_sum:
            return [amount_total * (weight / weight_sum) for weight in weights]
        share = amount_total / len(source_lines)
        return [share] * len(source_lines)

    def _rfq_price_unit_from_amount(self, line_amount, product_qty):
        """Unit price so line subtotal matches allocated winner amount."""
        self.ensure_one()
        if not line_amount:
            return 0.0
        if not product_qty:
            return self.currency_id.round(line_amount)
        return self.currency_id.round(line_amount / product_qty)

    def _prepare_rfq_order_line_values_from_pr(self, partner):
        """Build RFQ lines from linked Purchase Request lines (qty/UoM as on PR)."""
        self.ensure_one()
        order_lines = []
        FiscalPosition = self.env["account.fiscal.position"]
        fpos = FiscalPosition.with_company(self.company_id)._get_fiscal_position(partner)
        pr_lines = self._get_rfq_source_pr_lines()
        line_amounts = self._split_winner_line_amounts(pr_lines)
        for line, line_amount in zip(pr_lines, line_amounts):
            product_lang = line.product_id.with_context(
                lang=partner.lang or self.env.user.lang,
                partner_id=partner.id,
            )
            name = line.name or product_lang.display_name
            if product_lang.description_purchase:
                name += "\n" + product_lang.description_purchase
            taxes_ids = fpos.map_tax(
                line.product_id.supplier_taxes_id.filtered(
                    lambda tax: tax.company_id in self.company_id.parent_ids
                )
            ).ids
            # Keep quantity and UoM exactly as defined on the PR.
            product_uom = line.product_uom_id or line.product_id.uom_po_id
            product_qty = line.product_qty
            if line_amount:
                price_unit = self._rfq_price_unit_from_amount(line_amount, product_qty)
            elif line.estimated_cost and product_qty:
                price_unit = self.currency_id.round(line.estimated_cost / product_qty)
            elif line.estimated_cost:
                price_unit = line.estimated_cost
            else:
                price_unit = 0.0
            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "name": name,
                        "product_qty": product_qty,
                        "product_uom": product_uom.id if product_uom else False,
                        "price_unit": price_unit,
                        "taxes_id": [(6, 0, taxes_ids)],
                        "date_planned": fields.Datetime.now(),
                        "purchase_request_lines": [(4, line.id)],
                    },
                )
            )
        return order_lines

    def _prepare_rfq_order_line_values(self, partner):
        self.ensure_one()
        if self.purchase_request_id and self._get_rfq_source_pr_lines():
            return self._prepare_rfq_order_line_values_from_pr(partner)
        order_lines = []
        FiscalPosition = self.env["account.fiscal.position"]
        fpos = FiscalPosition.with_company(self.company_id)._get_fiscal_position(partner)
        agreement_lines = self.line_ids
        line_amounts = self._split_winner_line_amounts(agreement_lines)
        for line, line_amount in zip(agreement_lines, line_amounts):
            product_lang = line.product_id.with_context(
                lang=partner.lang or self.env.user.lang,
                partner_id=partner.id,
            )
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += "\n" + product_lang.description_purchase
            taxes_ids = fpos.map_tax(
                line.product_id.supplier_taxes_id.filtered(
                    lambda tax: tax.company_id in self.company_id.parent_ids
                )
            ).ids
            product_uom = line.product_uom_id or line.product_id.uom_po_id
            product_qty = line.product_qty
            price_unit = self._rfq_price_unit_from_amount(line_amount, product_qty)
            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "name": name,
                        "product_qty": product_qty,
                        "product_uom": product_uom.id if product_uom else False,
                        "price_unit": price_unit,
                        "taxes_id": [(6, 0, taxes_ids)],
                        "date_planned": fields.Datetime.now(),
                    },
                )
            )
        return order_lines

    def _prepare_rfq_vals(self, partner, egp_bid_reference=None):
        self.ensure_one()
        payment_term = partner.property_supplier_payment_term_id
        FiscalPosition = self.env["account.fiscal.position"]
        fpos = FiscalPosition.with_company(self.company_id)._get_fiscal_position(partner)
        origin_parts = [
            part
            for part in [
                self.purchase_request_id.name,
                self.egp_reference,
                self.name,
                egp_bid_reference,
            ]
            if part
        ]
        return {
            "requisition_id": self.id,
            "partner_id": partner.id,
            "fiscal_position_id": fpos.id,
            "payment_term_id": payment_term.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "origin": ", ".join(origin_parts),
            "partner_ref": egp_bid_reference or False,
            "egp_bid_reference": egp_bid_reference or False,
            "notes": self.description,
            "picking_type_id": (
                self.purchase_request_id.picking_type_id.id
                if self.purchase_request_id and self.purchase_request_id.picking_type_id
                else self.picking_type_id.id
            ),
            "order_line": self._prepare_rfq_order_line_values(partner),
        }

    def action_open_create_rfq_wizard(self):
        self.ensure_one()
        if self.requisition_type == "egp_procurement":
            if self.state not in ("confirmed", "done"):
                raise UserError(
                    _("Please confirm the e-GP process before creating RFQs.")
                )
            if not self.purchase_request_id and not self.line_ids:
                raise UserError(
                    _("Please link a Purchase Request or add product lines before creating RFQ.")
                )
            if self.purchase_request_id and not self._get_rfq_source_pr_lines():
                raise UserError(
                    _("The linked Purchase Request has no product lines to create RFQ.")
                )
            winner = self.egp_bid_ids.filtered("is_winner")[:1]
            if not winner:
                raise UserError(
                    _(
                        "ยังไม่สามารถสร้าง RFQ/PO ได้ กรุณาสร้างใบเชิญเสนอราคา "
                        "รับข้อเสนอ เปรียบเทียบราคา และเลือกผู้ชนะในกระบวนการ eGP ก่อน"
                    )
                )
            if not self.egp_award_approved:
                raise UserError(
                    _(
                        "ยังไม่สามารถสร้าง PO ได้ กรุณาแนบและลงนาม "
                        "รายงานผลการพิจารณา และมีประกาศผู้ชนะในแท็บเอกสาร e-GP ก่อน"
                    )
                )
        elif self.state != "confirmed":
            raise UserError(_("Please confirm the purchase agreement before creating RFQs."))
        winner = self.egp_bid_ids.filtered("is_winner")[:1]
        context = {
            "default_requisition_id": self.id,
            "default_partner_id": (winner.partner_id or self.vendor_id).id,
            "default_egp_bid_reference": winner.egp_bid_reference if winner else False,
        }
        return {
            "name": _("สร้าง PO"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.requisition.create.rfq",
            "view_mode": "form",
            "target": "new",
            "context": context,
        }

    def action_compare_rfqs(self):
        self.ensure_one()
        rfqs = self.purchase_ids.filtered(lambda po: po.state in ("draft", "sent", "to approve"))
        if not rfqs:
            raise UserError(_("There are no RFQs to compare for this agreement."))
        main_rfq = rfqs[0]
        if len(rfqs) == 1 and not main_rfq.has_alternatives:
            raise UserError(_("Create at least two RFQs or alternatives before comparing prices."))
        return main_rfq.action_compare_alternative_lines()

    def action_done(self):
        res = super().action_done()
        closed = self.filtered(
            lambda requisition: requisition.requisition_type == "egp_procurement"
            and requisition.state == "done"
        )
        if closed:
            closed.with_context(egp_flow_auto=True).write({"egp_flow_stage": "done"})
        return res

    def _summarize_offered_totals(self):
        for requisition in self:
            if requisition.egp_consideration_type not in ("line", "unit"):
                continue
            totals = {}
            for line in requisition.egp_bid_line_ids:
                if not line.bid_id or not line.product_id:
                    continue
                totals[line.bid_id] = totals.get(line.bid_id, 0.0) + (
                    line.price_subtotal or 0.0
                )
            for bid in requisition.egp_bid_ids:
                bid.amount_total = totals.get(bid, 0.0)

    def action_summarize_offered_totals(self):
        self._summarize_offered_totals()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("สรุปราคารวมที่เสนอ"),
                "message": _(
                    "คำนวณราคารวมจากรายการสินค้าในตารางเปรียบเทียบราคาแล้ว"
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def action_close_after_award(self):
        self.ensure_one()
        if self.requisition_type == "egp_procurement":
            if not self.egp_bid_ids.filtered("is_winner"):
                raise UserError(
                    _("Please select a winning bidder before closing the agreement.")
                )
            self.action_done()
            return True
        open_rfqs = self.purchase_ids.filtered(
            lambda po: po.state in ("draft", "sent", "to approve")
        )
        if open_rfqs:
            raise UserError(
                _(
                    "To close this purchase agreement, cancel or confirm all related RFQs first."
                )
            )
        self.action_done()

    def action_print_contract_essence(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_purchase_agreement_egp.action_report_contract_essence"
        ).report_action(self)

    def _format_essence_amount(self, amount):
        return "{:,.2f}".format(amount or 0.0)

    def _format_essence_date(self, date_value):
        if not date_value:
            return "-"
        return "%02d/%02d/%04d" % (
            date_value.day,
            date_value.month,
            date_value.year + 543,
        )

    def _essence_item_name(self, line):
        return (
            line.name
            or getattr(line, "product_description_variants", False)
            or (line.product_id.display_name if line.product_id else "-")
        )

    def _essence_offer_lines(self):
        self.ensure_one()
        winning = self.egp_bid_line_ids.filtered(
            lambda line: line.is_winner and line.product_id
        )
        if winning:
            return winning
        if self.egp_consideration_type == "total":
            winner = self.egp_bid_ids.filtered("is_winner")[:1]
            if winner and winner.line_ids:
                return winner.line_ids.filtered("product_id")
        return self.egp_bid_line_ids.filtered("product_id")

    def _essence_contracts_for_partner(self, partner):
        if "contract_ids" not in self._fields or not partner:
            return self.env["purchase.contract"]
        return self.contract_ids.filtered(
            lambda contract: contract.partner_id == partner
            and contract.state != "cancel"
        )

    def _get_contract_essence_values(self):
        self.ensure_one()
        offer_lines = self._essence_offer_lines()
        unique_products = offer_lines.mapped("product_id")
        budget_by_product = {}
        for line in offer_lines:
            if line.product_id and line.budget_amount and line.product_id.id not in budget_by_product:
                budget_by_product[line.product_id.id] = line.budget_amount
        budget = self.purchase_request_amount_total or sum(budget_by_product.values())
        offer_rows = []
        for index, line in enumerate(offer_lines, start=1):
            partner = line.partner_id
            offer_rows.append(
                {
                    "seq": index,
                    "item": self._essence_item_name(line),
                    "vat": partner.vat or "-",
                    "vendor": partner.display_name or "-",
                    "amount": self._format_essence_amount(line.price_subtotal),
                }
            )
        if not offer_rows:
            for index, bid in enumerate(self.egp_bid_ids, start=1):
                offer_rows.append(
                    {
                        "seq": index,
                        "item": self.egp_project_name or self.name or "-",
                        "vat": bid.partner_id.vat or "-",
                        "vendor": bid.partner_id.display_name or "-",
                        "amount": self._format_essence_amount(bid.amount_total),
                    }
                )
        winner_partners = offer_lines.filtered("is_winner").mapped("partner_id")
        if not winner_partners:
            winner_partners = self.egp_bid_ids.filtered("is_winner").mapped("partner_id")
        winner_rows = []
        for index, partner in enumerate(winner_partners, start=1):
            partner_lines = offer_lines.filtered(lambda line: line.partner_id == partner)
            amount = sum(partner_lines.mapped("price_subtotal"))
            bid = self.egp_bid_ids.filtered(lambda rec: rec.partner_id == partner)[:1]
            if not amount and bid:
                amount = bid.amount_total
            contracts = self._essence_contracts_for_partner(partner)
            contract = contracts[:1]
            orders = self.purchase_ids.filtered(
                lambda order: order.partner_id == partner and order.state != "cancel"
            )
            official_no = False
            if contract and "contract_po_number" in contract._fields:
                official_no = contract.contract_po_number
            contract_no = official_no or " / ".join(
                part
                for part in [
                    contract.name if contract else False,
                    orders[:1].name if orders else False,
                ]
                if part
            ) or "-"
            egp_control = "-"
            if contract and "egp_contract_control_no" in contract._fields:
                egp_control = contract.egp_contract_control_no or "-"
            state_label = "-"
            if contract:
                state_label = dict(contract._fields["state"].selection).get(
                    contract.state, contract.state
                )
            winner_rows.append(
                {
                    "seq": index,
                    "vat": partner.vat or "-",
                    "vendor": partner.display_name or "-",
                    "egp_control": egp_control,
                    "contract_no": contract_no,
                    "contract_date": self._format_essence_date(
                        contract.date_start if contract else False
                    ),
                    "amount": self._format_essence_amount(
                        contract.amount_total if contract else amount
                    ),
                    "status": state_label,
                    "reason": (bid.notes if bid and bid.notes else "-"),
                }
            )
        method_name = self.procurement_method_id.display_name if self.procurement_method_id else ""
        project_name = self.egp_project_name or ""
        if not project_name and unique_products:
            project_name = "จำนวน %s รายการ" % len(unique_products)
            if method_name:
                project_name = "%s ด้วยวิธี%s" % (project_name, method_name)
        consideration_label = dict(
            self._fields["egp_consideration_type"].selection
        ).get(self.egp_consideration_type or "", "")
        return {
            "agency": self.company_id.display_name or "-",
            "project_no": self.egp_reference or "-",
            "project_name": project_name or self.name or "-",
            "consideration": consideration_label or "-",
            "budget": self._format_essence_amount(budget),
            "median": self._format_essence_amount(budget),
            "offer_rows": offer_rows,
            "winner_rows": winner_rows,
        }


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    product_description_variants = fields.Char(
        string="คำอธิบายรายการซื้อใน e-GP",
    )
    currency_id = fields.Many2one(
        related="requisition_id.currency_id",
        store=True,
    )
    budget_amount = fields.Monetary(
        string="งบประมาณ",
        currency_field="currency_id",
    )

    @api.onchange("product_qty", "price_unit")
    def _onchange_budget_amount_from_price(self):
        if self.price_unit:
            self.budget_amount = (self.product_qty or 0.0) * self.price_unit

    @api.depends(
        "product_id",
        "company_id",
        "requisition_id.date_start",
        "product_qty",
        "product_uom_id",
        "requisition_id.vendor_id",
        "requisition_id.requisition_type",
    )
    def _compute_price_unit(self):
        egp_lines = self.filtered(
            lambda line: line.requisition_id.requisition_type == "egp_procurement"
        )
        super(PurchaseRequisitionLine, self - egp_lines)._compute_price_unit()
