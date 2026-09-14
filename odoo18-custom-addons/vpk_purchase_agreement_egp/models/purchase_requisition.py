# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
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
        string="e-GP Documents",
        copy=False,
    )
    egp_bid_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.bid",
        inverse_name="requisition_id",
        string="ผู้เสนอราคา",
        copy=False,
    )
    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        copy=False,
    )
    purchase_type_id = fields.Many2one(
        comodel_name="purchase.type",
        string="Purchase Type",
        ondelete="restrict",
        copy=False,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        copy=False,
    )
    purchase_request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="การอ้างอิง",
        tracking=True,
        index=True,
        copy=False,
        help="ใบขอซื้อที่เชื่อมกับกระบวนการ e-GP นี้",
    )
    purchase_request_amount_total = fields.Monetary(
        string="วงเงินงบประมาณ",
        currency_field="currency_id",
        related="purchase_request_id.estimated_cost",
        readonly=True,
    )
    is_egp_procurement = fields.Boolean(
        compute="_compute_is_egp_procurement",
    )
    egp_flow_stage = fields.Selection(
        selection="_selection_egp_flow_stage",
        string="e-GP Flow Stage",
        compute="_compute_egp_flow_stage",
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
            ("awarded", _("8. Award Vendor"), _("เลือกผู้ชนะและปิดกระบวนการ")),
            ("done", _("9. Closed"), _("Purchase agreement is completed.")),
        ]

    @api.depends("requisition_type")
    def _compute_is_egp_procurement(self):
        for record in self:
            record.is_egp_procurement = record.requisition_type == "egp_procurement"

    @api.depends(
        "state",
        "requisition_type",
        "egp_document_ids",
        "egp_invitation_ids",
        "egp_invitation_ids.state",
        "egp_bid_ids",
        "egp_bid_ids.is_winner",
        "purchase_ids",
        "purchase_ids.state",
    )
    def _compute_egp_flow_stage(self):
        for record in self:
            if record.requisition_type != "egp_procurement":
                record.egp_flow_stage = False
                continue
            if record.state == "cancel":
                record.egp_flow_stage = "cancel"
                continue
            if record.state == "done":
                record.egp_flow_stage = "done"
                continue
            if record.egp_bid_ids.filtered("is_winner") or record.purchase_ids.filtered(
                lambda po: po.state == "purchase"
            ):
                record.egp_flow_stage = "awarded"
                continue
            if len(record.egp_bid_ids) >= 2:
                record.egp_flow_stage = "compare"
                continue
            if record.egp_bid_ids:
                record.egp_flow_stage = "rfq"
                continue
            if record.egp_invitation_ids:
                record.egp_flow_stage = "rfq"
                continue
            if record.egp_document_ids:
                record.egp_flow_stage = "egp_docs"
                continue
            if record.state == "confirmed":
                record.egp_flow_stage = "confirmed"
                continue
            record.egp_flow_stage = "draft"

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
        return records

    def write(self, vals):
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
                        "ยังไม่สามารถสร้าง RFQ/PO ได้ กรุณาจัดทำและอนุมัติ "
                        "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้างก่อน"
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
            "name": _("สร้าง RFQ/PO สำหรับผู้ชนะ"),
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


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    product_description_variants = fields.Char(
        string="คำอธิบายรายการซื้อใน e-GP",
    )

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
