# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="รหัสสัญญาอ้างอิง",
        tracking=True,
        index=True,
        copy=False,
        domain="['&', ('company_id', 'in', [company_id, False]), '|', ('state', '=', 'confirmed'), '&', ('quantity_policy', '=', 'unlimited'), ('state', '=', 'draft')]",
        help="เลือกสัญญาที่ยืนยันแล้ว หรือสัญญาจะซื้อจะขายไม่จำกัดจำนวนที่สร้างจากผู้ชนะแล้ว เพื่อดึงรายการราคา",
    )
    contract_partner_id = fields.Many2one(
        related="contract_id.partner_id",
        string="คู่ค้าตามสัญญา",
        readonly=True,
    )
    contract_type_id = fields.Many2one(
        related="contract_id.contract_type_id",
        string="ประเภทสัญญา",
        readonly=True,
    )
    contract_egp_control_no = fields.Char(
        related="contract_id.egp_contract_control_no",
        string="เลขคุมสัญญาในระบบ e-GP",
        readonly=True,
    )
    contract_po_number = fields.Char(
        related="contract_id.contract_po_number",
        string="เลขที่สัญญา / ใบสั่งซื้อ",
        readonly=True,
    )
    contract_amount_total = fields.Monetary(
        related="contract_id.amount_total",
        string="มูลค่ารวมสัญญา",
        readonly=True,
        currency_field="currency_id",
    )
    contract_amount_remaining = fields.Monetary(
        related="contract_id.amount_remaining",
        string="มูลค่าคงเหลือสัญญา",
        readonly=True,
        currency_field="currency_id",
    )
    is_unlimited_contract = fields.Boolean(
        string="สัญญาไม่จำกัดจำนวน",
        compute="_compute_is_unlimited_contract",
    )
    price_agreement_only = fields.Boolean(
        string="ใบหาผู้ชนะไม่จำกัดจำนวน",
        copy=False,
        tracking=True,
        help="ใบประกวดราคาที่นำไปสู่สัญญาจะซื้อจะขายไม่จำกัดจำนวน "
        "ไม่จองงบของปริมาณอ้างอิง งบจองเมื่อเปิดใบขอซื้อเพื่อสั่งของจริง",
    )

    @api.depends("contract_id.quantity_policy")
    def _compute_is_unlimited_contract(self):
        for request in self:
            request.is_unlimited_contract = (
                request.contract_id.quantity_policy == "unlimited"
            )

    def _vpk_can_send_to_egp(self):
        self.ensure_one()
        if self.is_unlimited_contract:
            return False
        return super()._vpk_can_send_to_egp()

    @api.depends(
        "state",
        "to_create",
        "contract_id.quantity_policy",
        "line_ids.requisition_lines.requisition_id.state",
        "line_ids.requisition_lines.requisition_id.egp_flow_stage",
    )
    def _compute_egp_flow_stage(self):
        super()._compute_egp_flow_stage()
        for request in self.filtered("is_unlimited_contract"):
            request.is_egp_procurement_flow = False
            request.egp_flow_stage = False
    related_contract_count = fields.Integer(
        compute="_compute_related_contract_count",
    )

    def _get_related_contracts(self):
        self.ensure_one()
        contracts = self.contract_id
        if isinstance(self.id, int) and "requisition_id" in self.env["purchase.contract"]._fields:
            requisitions = self.env["purchase.requisition"]
            if hasattr(self, "_get_related_requisitions"):
                requisitions = self._get_related_requisitions()
            elif hasattr(self, "_get_egp_requisitions"):
                requisitions = self._get_egp_requisitions()
            if requisitions:
                contracts |= self.env["purchase.contract"].search(
                    [("requisition_id", "in", requisitions.ids)]
                )
        return contracts

    @api.depends(
        "contract_id",
        "line_ids.requisition_lines.requisition_id",
    )
    def _compute_related_contract_count(self):
        for rec in self:
            rec.related_contract_count = len(rec._get_related_contracts())

    def action_open_related_contract(self):
        self.ensure_one()
        return self._vpk_action_open_related_readonly(
            self._get_related_contracts(),
            _("สัญญา"),
        )

    def _get_contract_amount(self):
        self.ensure_one()
        return sum(
            line.estimated_cost or 0.0
            for line in self.line_ids.filtered(lambda line: not line.cancelled)
        )

    def _get_contract_covered_by_po_amount(self):
        """มูลค่า PO ที่ยืนยันแล้วซึ่งเชื่อมกับ PR นี้ภายใต้สัญญาเดียวกัน."""
        self.ensure_one()
        if not self.contract_id:
            return 0.0
        orders = self.line_ids.mapped("purchase_lines.order_id").filtered(
            lambda order: order.contract_id == self.contract_id
            and order.state in ("purchase", "done")
        )
        return sum(orders.mapped("amount_untaxed"))

    def _check_contract_balance(self):
        """ขั้นตอนที่ 4-5: Hard Block ก่อนส่งไปตรวจงบประมาณ."""
        for request in self:
            if not request.contract_id:
                continue
            required = request._get_contract_amount()
            if required <= 0:
                raise UserError(
                    _("กรุณาระบุมูลค่ารายการใน PR ก่อนตรวจยอดคงเหลือสัญญา")
                )
            request.contract_id._check_amount_available(
                required_amount=required,
                exclude_requests=request,
            )

    @api.depends("state", "budget_check_state", "contract_id")
    def _compute_hide_reviews(self):
        super()._compute_hide_reviews()
        for request in self:
            if request.contract_id and request.state == "draft":
                request.hide_reviews = False

    def _mark_price_agreement_only(self):
        """ใบ e-bidding ของสัญญาไม่จำกัดจำนวนคืนงบที่กันไว้ และไม่จองซ้ำ."""
        message = _(
            "ใบประกวดราคานี้เป็นสัญญาจะซื้อจะขายไม่จำกัดจำนวน "
            "จึงไม่จองงบของปริมาณอ้างอิง "
            "งบจะถูกจองเมื่อเปิดใบขอซื้อเพื่อสั่งของตามจำนวนจริง"
        )
        for request in self:
            was_holding = bool(request.budget_reservation_active)
            already = bool(request.price_agreement_only)
            if was_holding and hasattr(request, "_release_budget_reservation"):
                request._release_budget_reservation(clear_budget_lines=False)
            if already and not was_holding:
                continue
            vals = {"price_agreement_only": True}
            if "budget_check_state" in request._fields:
                vals.update(
                    {
                        "budget_check_state": "enough",
                        "budget_check_message": message,
                    }
                )
            request.with_context(skip_budget_check_reset=True).write(vals)
            request.message_post(body=message)

    def _price_agreement_reserved_to_ignore(self, budget_post=None, product=None):
        """ยอดที่ใบประกวดราคาไม่จำกัดจำนวนยังกันไว้ ไม่ให้นับตอนเช็คงบใบสั่งของจริง."""
        self.ensure_one()
        if "price_agreement_only" not in self.env["purchase.request"]._fields:
            return 0.0
        domain = [
            ("id", "not in", self.line_ids.ids or [0]),
            ("request_id.price_agreement_only", "=", True),
            ("request_id.budget_reservation_active", "=", True),
            ("cancelled", "=", False),
        ]
        if product:
            domain.append(("product_id", "=", product.id))
        if budget_post:
            domain.append(("budget_post_id", "=", budget_post.id))
        if self.budget_analytic_account_id:
            domain.append(
                (
                    "budget_analytic_account_id",
                    "=",
                    self.budget_analytic_account_id.id,
                )
            )
        if self.budget_fund_source_id:
            domain.append(
                ("budget_fund_source_id", "=", self.budget_fund_source_id.id)
            )
        lines = self.env["purchase.request.line"].sudo().search(domain)
        return sum(
            line._get_budget_effective_reserved_amount_company() for line in lines
        )

    def _get_other_pr_reserved_amount(self, budget_post):
        amount = super()._get_other_pr_reserved_amount(budget_post)
        held = self._price_agreement_reserved_to_ignore(budget_post=budget_post)
        return max(0.0, amount - held)

    def _get_other_pr_reserved_amount_for_product(self, product):
        amount = super()._get_other_pr_reserved_amount_for_product(product)
        held = self._price_agreement_reserved_to_ignore(product=product)
        return max(0.0, amount - held)

    def _activate_budget_reservation(self):
        price_only = self.filtered("price_agreement_only")
        if price_only:
            price_only._mark_price_agreement_only()
        others = self - price_only
        if others:
            return super(PurchaseRequest, others)._activate_budget_reservation()
        return None

    def _restore_budget_reservation_after_po_change(self):
        return super(
            PurchaseRequest, self.filtered(lambda request: not request.price_agreement_only)
        )._restore_budget_reservation_after_po_change()

    def action_check_budget_status(self):
        self.ensure_one()
        if self.price_agreement_only:
            self._mark_price_agreement_only()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("ไม่จองงบจากใบประกวดราคานี้"),
                    "message": self.budget_check_message,
                    "type": "success",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": self._name,
                        "res_id": self.id,
                        "view_mode": "form",
                        "views": [(False, "form")],
                        "target": "current",
                    },
                },
            }
        return super().action_check_budget_status()

    def _has_contract_bypass_budget(self):
        """PR ที่เบิกงวดจากสัญญาจะตรวจวงเงินสัญญาแทนงบประมาณ.

        สัญญาจะซื้อจะขายไม่จำกัดจำนวนใช้ราคาจากสัญญา แต่ตรวจงบประมาณของใบขอซื้อครั้งนั้น
        """
        self.ensure_one()
        if not self.contract_id or self.contract_id.quantity_policy == "unlimited":
            return False
        return True

    def action_check_budget_status(self):
        contract_prs = self.filtered(lambda pr: pr._has_contract_bypass_budget())
        normal_prs = self - contract_prs
        contract_prs._check_contract_balance()
        for request in contract_prs:
            request.with_context(skip_budget_check_reset=True).write(
                {
                    "budget_check_state": "enough",
                    "budget_check_date": fields.Datetime.now(),
                    "budget_check_message": _(
                        "ตรวจวงเงินผ่านสัญญา %(contract)s แทนงบประมาณแผ่นดิน\n"
                        "ยอดคงเหลือสัญญา: %(remaining)s"
                    )
                    % {
                        "contract": request.contract_id.display_name,
                        "remaining": "{:,.2f}".format(
                            request.contract_id.amount_remaining or 0.0
                        ),
                    },
                }
            )
        if contract_prs and not normal_prs:
            request = contract_prs[:1]
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("ตรวจวงเงินสัญญา: ผ่าน"),
                    "message": _(
                        "PR นี้ตรวจวงเงินจากสัญญา %(contract)s แทนงบประมาณแผ่นดิน"
                    )
                    % {"contract": request.contract_id.display_name},
                    "type": "success",
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
        contract_prs = self.filtered(lambda pr: pr._has_contract_bypass_budget())
        normal_prs = self - contract_prs
        contract_prs._check_contract_balance()
        for request in contract_prs:
            request.with_context(skip_budget_check_reset=True).write(
                {
                    "budget_check_state": "enough",
                    "budget_check_date": fields.Datetime.now(),
                    "budget_check_message": _(
                        "ตรวจวงเงินผ่านสัญญา %(contract)s"
                    )
                    % {"contract": request.contract_id.display_name},
                }
            )
        if normal_prs:
            super(PurchaseRequest, normal_prs)._check_budget_available_before_submit()

    def _get_default_product_for_contract(self, contract):
        """ดึงสินค้า/บริการจาก PR ต้นทางของสัญญา (ผ่าน e-GP → PR)."""
        if contract.requisition_id and contract.requisition_id.purchase_request_id:
            source_pr = contract.requisition_id.purchase_request_id
            product = source_pr.line_ids.filtered(
                lambda line: not line.cancelled and line.product_id
            ).mapped("product_id")[:1]
            if product:
                return product
        return self.env["product.product"]

    def _prepare_installment_pr_lines(self, contract, installments):
        """เตรียมค่า PR line จากงวดงานของสัญญา."""
        default_product = self._get_default_product_for_contract(contract)
        line_vals = []
        for inst in installments:
            product = inst.product_id or default_product
            name = inst.name
            if product:
                name = "%s - %s" % (inst.name, product.display_name)
            vals = {
                "product_id": product.id if product else False,
                "name": name,
                "product_qty": 1.0,
                "estimated_cost": inst.amount or 0.0,
                "contract_installment_id": inst.id,
                "date_required": inst.date_planned or fields.Date.context_today(self),
            }
            if product:
                vals["product_uom_id"] = product.uom_id.id
            line_vals.append((0, 0, vals))
        return line_vals

    def _prepare_pr_vals_from_contract_line(self, contract_line, qty=0.0):
        price = contract_line.price_unit or 0.0
        vals = {
            "product_id": contract_line.product_id.id,
            "name": contract_line.name or contract_line.product_id.display_name,
            "product_qty": qty or 0.0,
            "budget_unit_price": price,
            "estimated_cost": (qty or 0.0) * price,
            "contract_line_id": contract_line.id,
            "date_required": fields.Date.context_today(self),
        }
        if contract_line.product_uom_id:
            vals["product_uom_id"] = contract_line.product_uom_id.id
        return vals

    def _get_contract_work_acceptance_committee_source(self):
        """คณะกรรมการตรวจรับจาก e-GP หรือใบขอซื้อต้นทางของสัญญา."""
        self.ensure_one()
        contract = self.contract_id
        if not contract:
            return self.env["procurement.committee"]
        requisition = contract.requisition_id
        if requisition and requisition.work_acceptance_committee_ids:
            return requisition.work_acceptance_committee_ids
        source_pr = requisition.purchase_request_id if requisition else False
        if source_pr and source_pr.work_acceptance_committee_ids:
            return source_pr.work_acceptance_committee_ids
        return self.env["procurement.committee"]

    def _committee_commands_from_members(self, members, committee_type):
        seen = set()
        commands = []
        for member in members:
            employee = member.employee_id
            if not employee or employee.id in seen:
                continue
            seen.add(employee.id)
            commands.append(
                Command.create(
                    {
                        "employee_id": employee.id,
                        "name": member.name or employee.display_name,
                        "approve_role": member.approve_role or "committee",
                        "committee_type": committee_type,
                        "note": member.note,
                    }
                )
            )
        return commands

    def _pull_work_acceptance_committee_from_contract(self):
        """ดึงคณะกรรมการตรวจรับจากสัญญา (e-GP/PR ต้นทาง) ถ้า PR ยังไม่มี."""
        for request in self:
            if (
                not request.contract_id
                or request.contract_id.quantity_policy != "unlimited"
                or "work_acceptance_committee_ids" not in request._fields
                or request.work_acceptance_committee_ids
            ):
                continue
            members = request._get_contract_work_acceptance_committee_source()
            commands = request._committee_commands_from_members(
                members, "work_acceptance"
            )
            if commands:
                request.work_acceptance_committee_ids = commands

    def _pull_unlimited_contract_lines(self):
        """ดึงรายการราคาจากสัญญาไม่จำกัดจำนวน โดยคงจำนวนที่ใส่ไว้แล้ว."""
        self.ensure_one()
        contract = self.contract_id
        contract._ensure_open_for_calloff()
        if self.state != "draft":
            raise UserError(_("ดึงรายการได้เฉพาะใบขอซื้อสถานะร่าง"))
        stale = self.line_ids.filtered(
            lambda line: line.contract_line_id
            and line.contract_line_id.contract_id != contract
        )
        if stale:
            stale.unlink()
        existing = {
            line.contract_line_id.id: line
            for line in self.line_ids
            if line.contract_line_id
        }
        commands = []
        for contract_line in contract.line_ids:
            current = existing.get(contract_line.id)
            qty = current.product_qty if current else 0.0
            vals = self._prepare_pr_vals_from_contract_line(contract_line, qty=qty)
            if current:
                current.write(vals)
            else:
                commands.append((0, 0, vals))
        if commands:
            self.write({"line_ids": commands})
        self._pull_work_acceptance_committee_from_contract()

    def action_pull_contract_price_list(self):
        """หน่วยงานดึงรายการราคาจากสัญญา แล้วใส่จำนวนที่ต้องการซื้อเอง."""
        for request in self:
            request._pull_unlimited_contract_lines()
        request = self[:1]
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("ดึงรายการราคาแล้ว"),
                "message": _(
                    "ดึงราคาจากสัญญา %(contract)s แล้ว "
                    "ใส่จำนวนเฉพาะรายการที่ต้องการซื้อ ลบรายการที่ไม่ต้องการ "
                    "จากนั้นตรวจสอบงบประมาณและส่งพัสดุ"
                )
                % {"contract": request.contract_id.display_name},
                "type": "success",
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

    def _onchange_unlimited_contract(self):
        contract = self.contract_id
        try:
            contract._ensure_open_for_calloff()
        except UserError as error:
            return {
                "warning": {
                    "title": _("ดึงรายการราคาไม่ได้"),
                    "message": error.args[0],
                }
            }
        commands = [
            (
                0,
                0,
                self._prepare_pr_vals_from_contract_line(line, qty=0.0),
            )
            for line in contract.line_ids
        ]
        self.line_ids = [(5, 0, 0)] + commands
        for line in self.line_ids:
            if line.contract_line_id:
                price = line.contract_line_id.price_unit or 0.0
                line.budget_unit_price = price
                line.product_qty = 0.0
                line.estimated_cost = 0.0
        committee_count = 0
        if (
            "work_acceptance_committee_ids" in self._fields
            and not self.work_acceptance_committee_ids
        ):
            committee_cmds = self._committee_commands_from_members(
                self._get_contract_work_acceptance_committee_source(),
                "work_acceptance",
            )
            if committee_cmds:
                self.work_acceptance_committee_ids = committee_cmds
                committee_count = len(committee_cmds)
        message = _(
            "ดึง %(count)s รายการจากสัญญา %(contract)s คู่ค้า %(partner)s\n"
            "ราคาต่อหน่วยถูกล็อกตามสัญญา กรุณาใส่จำนวนที่ต้องการซื้อ "
            "และลบรายการที่ไม่ต้องการ แล้วตรวจสอบงบประมาณก่อนส่งพัสดุ"
        ) % {
            "count": len(contract.line_ids),
            "contract": contract.display_name,
            "partner": contract.partner_id.display_name or "-",
        }
        if committee_count:
            message = _(
                "%(base)s\nดึงคณะกรรมการตรวจรับ %(committee)s คนจากสัญญา/โครงการต้นทางแล้ว"
            ) % {
                "base": message,
                "committee": committee_count,
            }
        return {
            "warning": {
                "title": _("ดึงรายการราคาแล้ว"),
                "message": message,
            }
        }

    def write(self, vals):
        res = super().write(vals)
        if vals.get("contract_id"):
            self.filtered(
                lambda request: request.contract_id.quantity_policy == "unlimited"
            )._pull_work_acceptance_committee_from_contract()
        return res

    @api.onchange("contract_id")
    def _onchange_contract_id(self):
        if not self.contract_id:
            return
        if self.contract_id.quantity_policy == "unlimited":
            return self._onchange_unlimited_contract()
        contract = self.contract_id
        if not contract.installment_ids:
            if contract.partner_id:
                return {
                    "warning": {
                        "title": _("ผูกสัญญาแล้ว"),
                        "message": _(
                            "สัญญา %(contract)s คู่ค้า %(partner)s "
                            "ยอดคงเหลือ %(remaining)s\n"
                            "สัญญานี้ไม่มีงวดงาน — กรุณาเพิ่มรายการ PR เอง"
                        )
                        % {
                            "contract": contract.display_name,
                            "partner": contract.partner_id.display_name,
                            "remaining": "{:,.2f}".format(
                                contract.amount_remaining or 0.0
                            ),
                        },
                    }
                }
            return

        available = contract.installment_ids.filtered(
            lambda inst: not inst.is_used
        ).sorted("sequence")
        if not available:
            return {
                "warning": {
                    "title": _("ไม่มีงวดว่าง"),
                    "message": _(
                        "สัญญา %(contract)s ไม่มีงวดงานที่ยังไม่ถูกใช้ "
                        "กรุณาตรวจสอบงวดงานในสัญญาหรือเพิ่มรายการ PR เอง"
                    )
                    % {"contract": contract.display_name},
                }
            }

        existing_installment_ids = set(
            self.line_ids.mapped("contract_installment_id").ids
        )
        next_installment = available.filtered(
            lambda inst: inst.id not in existing_installment_ids
        )[:1]
        if not next_installment:
            return

        new_lines = self._prepare_installment_pr_lines(contract, next_installment)
        self.update({"line_ids": new_lines})

        return {
            "warning": {
                "title": _("ดึงงวดงานแล้ว"),
                "message": _(
                    "ดึง \"%(installment)s\" จากสัญญา %(contract)s\n"
                    "มูลค่างวด: %(amount)s\n"
                    "คู่ค้า: %(partner)s / ยอดคงเหลือสัญญา: %(remaining)s"
                )
                % {
                    "installment": next_installment.name,
                    "contract": contract.display_name,
                    "amount": "{:,.2f}".format(next_installment.amount or 0.0),
                    "partner": (contract.partner_id.display_name or "-"),
                    "remaining": "{:,.2f}".format(
                        contract.amount_remaining or 0.0
                    ),
                },
            }
        }


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    contract_line_id = fields.Many2one(
        comodel_name="purchase.contract.line",
        string="รายการในสัญญา",
        index=True,
        copy=False,
        help="รายการราคาที่ดึงจากสัญญาจะซื้อจะขายไม่จำกัดจำนวน",
    )
    contract_installment_id = fields.Many2one(
        comodel_name="purchase.contract.installment",
        string="งวดงานสัญญา",
        index=True,
        copy=False,
        help="อ้างอิงงวดงานจากสัญญาหลักที่ PR นี้เบิก",
    )
    contract_installment_name = fields.Char(
        related="contract_installment_id.name",
        string="ชื่องวด",
        readonly=True,
    )

    @api.depends(
        "request_id",
        "request_id.procurement_type_id",
        "request_id.procurement_type_id.product_id",
        "contract_line_id",
        "contract_line_id.product_id",
    )
    def _compute_default_product_id(self):
        """รายการที่ดึงจากสัญญาใช้สินค้า master ของสัญญานั้น ไม่ใช้สินค้าของประเภทพัสดุ."""
        contract_lines = self.filtered("contract_line_id.product_id")
        super(PurchaseRequestLine, self - contract_lines)._compute_default_product_id()
        for line in contract_lines:
            line.product_id = line.contract_line_id.product_id

    def _sync_contract_unit_price(self):
        if self.env.context.get("vpk_keep_contract_price"):
            return
        for line in self.filtered("contract_line_id"):
            price = line.contract_line_id.price_unit or 0.0
            qty = line.product_qty or 0.0
            expected = qty * price
            if (
                abs((line.budget_unit_price or 0.0) - price) <= 1e-6
                and abs((line.estimated_cost or 0.0) - expected) <= 1e-6
            ):
                continue
            line.with_context(vpk_keep_contract_price=True).write(
                {
                    "budget_unit_price": price,
                    "estimated_cost": expected,
                    "budget_reserved_amount": expected,
                }
            )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sync_contract_unit_price()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("vpk_keep_contract_price"):
            self._sync_contract_unit_price()
        return res

    def _onchange_product_id_set_budget_unit_price(self):
        locked = self.filtered("contract_line_id")
        super(
            PurchaseRequestLine, self - locked
        )._onchange_product_id_set_budget_unit_price()
        for line in locked:
            price = line.contract_line_id.price_unit or 0.0
            line.budget_unit_price = price
            line.estimated_cost = (line.product_qty or 0.0) * price
            line.budget_reserved_amount = line.estimated_cost or 0.0
