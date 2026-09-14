# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class HisBatch(models.Model):
    _name = "vpk.his.batch"
    _description = "HIS Staging Batch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "business_date desc, id desc"
    _check_company_auto = True
    _rec_name = "name"

    name = fields.Char(required=True, copy=False, default=lambda self: _("New"))
    external_id = fields.Char(required=True, index=True, tracking=True)
    source_system = fields.Char(required=True, index=True, tracking=True)
    batch_type = fields.Selection(
        [
            ("revenue", "Revenue"),
            ("stock_issue", "Stock Issue"),
            ("stock_requisition", "Stock Requisition"),
            ("reversal", "Reversal"),
        ],
        required=True,
        tracking=True,
    )
    original_external_id = fields.Char(
        help="สำหรับ reversal: external_id ของชุดที่ผ่านแล้ว",
    )
    original_batch_id = fields.Many2one(
        "vpk.his.batch",
        ondelete="restrict",
        index=True,
    )
    business_date = fields.Date(required=True, index=True, tracking=True)
    shift = fields.Char()
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready", "Ready"),
            ("error", "Error"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    sale_line_ids = fields.One2many("vpk.his.sale.line", "batch_id")
    payment_line_ids = fields.One2many("vpk.his.payment.line", "batch_id")
    stock_line_ids = fields.One2many("vpk.his.stock.line", "batch_id")
    requisition_line_ids = fields.One2many("vpk.his.requisition.line", "batch_id")
    source_warehouse_code = fields.Char()
    source_warehouse_id = fields.Many2one("stock.warehouse", ondelete="set null")
    source_location_id = fields.Many2one("stock.location", ondelete="set null")
    dest_warehouse_code = fields.Char()
    dest_warehouse_id = fields.Many2one("stock.warehouse", ondelete="set null")
    dest_location_code = fields.Char()
    dest_location_id = fields.Many2one("stock.location", ondelete="set null")
    department_code = fields.Char()
    control_sales_total = fields.Monetary()
    control_payments_total = fields.Monetary()
    control_qty_total = fields.Float(digits="Product Unit of Measure")
    sales_total = fields.Monetary(compute="_compute_totals", store=True)
    payments_total = fields.Monetary(compute="_compute_totals", store=True)
    stock_qty_total = fields.Float(
        compute="_compute_totals", store=True, digits="Product Unit of Measure"
    )
    requisition_qty_total = fields.Float(
        compute="_compute_totals", store=True, digits="Product Unit of Measure"
    )
    error_message = fields.Text()
    invoice_ids = fields.Many2many(
        "account.move",
        "vpk_his_batch_account_move_rel",
        "batch_id",
        "move_id",
        string="Invoices",
    )
    payment_ids = fields.Many2many(
        "account.payment",
        "vpk_his_batch_account_payment_rel",
        "batch_id",
        "payment_id",
        string="Payments",
    )
    picking_ids = fields.Many2many(
        "stock.picking",
        "vpk_his_batch_stock_picking_rel",
        "batch_id",
        "picking_id",
        string="Pickings",
    )
    scrap_ids = fields.Many2many(
        "stock.scrap",
        "vpk_his_batch_stock_scrap_rel",
        "batch_id",
        "scrap_id",
        string="Scraps",
    )
    invoice_count = fields.Integer(compute="_compute_doc_counts")
    payment_count = fields.Integer(compute="_compute_doc_counts")
    picking_count = fields.Integer(compute="_compute_doc_counts")
    line_error_count = fields.Integer(compute="_compute_line_error_count")

    _sql_constraints = [
        (
            "uniq_source_external_company",
            "unique(source_system, external_id, company_id)",
            "A HIS batch with this source_system and external_id already exists.",
        ),
    ]

    @api.depends(
        "sale_line_ids.amount_total",
        "payment_line_ids.amount",
        "stock_line_ids.qty",
        "requisition_line_ids.qty",
    )
    def _compute_totals(self):
        for rec in self:
            rec.sales_total = sum(rec.sale_line_ids.mapped("amount_total"))
            rec.payments_total = sum(rec.payment_line_ids.mapped("amount"))
            rec.stock_qty_total = sum(rec.stock_line_ids.mapped("qty"))
            rec.requisition_qty_total = sum(rec.requisition_line_ids.mapped("qty"))

    @api.depends("invoice_ids", "payment_ids", "picking_ids")
    def _compute_doc_counts(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)
            rec.payment_count = len(rec.payment_ids)
            rec.picking_count = len(rec.picking_ids)

    @api.depends(
        "sale_line_ids.line_state",
        "payment_line_ids.line_state",
        "stock_line_ids.line_state",
        "requisition_line_ids.line_state",
    )
    def _compute_line_error_count(self):
        for rec in self:
            rec.line_error_count = (
                len(rec.sale_line_ids.filtered(lambda l: l.line_state == "error"))
                + len(rec.payment_line_ids.filtered(lambda l: l.line_state == "error"))
                + len(rec.stock_line_ids.filtered(lambda l: l.line_state == "error"))
                + len(
                    rec.requisition_line_ids.filtered(lambda l: l.line_state == "error")
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.his.batch") or _("New")
                )
        return super().create(vals_list)

    def action_validate(self):
        for batch in self:
            if batch.state == "posted":
                raise UserError(_("Posted batches cannot be revalidated."))
            if batch.state == "cancelled":
                raise UserError(_("Cancelled batches cannot be revalidated."))
            batch._validate_batch()
        return True

    def _validate_batch(self):
        self.ensure_one()
        errors = []
        if self.batch_type == "reversal":
            original = self.original_batch_id
            if not original and self.original_external_id:
                original = self.search(
                    [
                        ("source_system", "=", self.source_system),
                        ("external_id", "=", self.original_external_id),
                        ("company_id", "=", self.company_id.id),
                    ],
                    limit=1,
                )
                self.original_batch_id = original.id if original else False
            if not original:
                errors.append(
                    _("Reversal requires original_external_id of a posted batch")
                )
            elif original.state != "posted":
                errors.append(
                    _("Original batch %s is not posted") % original.external_id
                )
            if original and original.batch_type == "reversal":
                errors.append(_("Cannot reverse a reversal batch"))

        if self.batch_type in ("revenue", "reversal"):
            for line in self.sale_line_ids:
                line._validate_line()
            for line in self.payment_line_ids:
                line._validate_line()
            if (
                self.batch_type == "revenue"
                and not self.sale_line_ids
                and not self.payment_line_ids
                and not self.original_external_id
            ):
                errors.append(_("Revenue batch requires sales or payments"))
            if self.control_sales_total and float_compare(
                self.sales_total, self.control_sales_total, precision_digits=2
            ):
                errors.append(
                    _("Sales total %(actual)s does not match control %(control)s")
                    % {
                        "actual": self.sales_total,
                        "control": self.control_sales_total,
                    }
                )
            if self.control_payments_total and float_compare(
                self.payments_total, self.control_payments_total, precision_digits=2
            ):
                errors.append(
                    _("Payments total %(actual)s does not match control %(control)s")
                    % {
                        "actual": self.payments_total,
                        "control": self.control_payments_total,
                    }
                )

        if self.batch_type in ("stock_issue", "reversal"):
            for line in self.stock_line_ids:
                line._validate_line()
            if (
                self.batch_type == "stock_issue"
                and not self.stock_line_ids
                and not self.original_external_id
            ):
                errors.append(_("Stock issue batch requires issues"))
            if self.batch_type == "stock_issue" and self.control_qty_total and float_compare(
                self.stock_qty_total, self.control_qty_total, precision_digits=4
            ):
                errors.append(
                    _("Qty total %(actual)s does not match control %(control)s")
                    % {
                        "actual": self.stock_qty_total,
                        "control": self.control_qty_total,
                    }
                )

        if self.batch_type in ("stock_requisition", "reversal"):
            if self.batch_type == "stock_requisition":
                if not self.source_warehouse_id:
                    errors.append(_("source_warehouse_code is required"))
                if not self.dest_warehouse_id:
                    errors.append(
                        _("dest_warehouse_code or department_code is required")
                    )
                if (
                    self.source_warehouse_id
                    and self.dest_warehouse_id
                    and self.source_warehouse_id == self.dest_warehouse_id
                    and self.source_location_id == self.dest_location_id
                ):
                    errors.append(_("Source and destination must differ"))
            for line in self.requisition_line_ids:
                line._validate_line()
            if (
                self.batch_type == "stock_requisition"
                and not self.requisition_line_ids
                and not self.original_external_id
            ):
                errors.append(_("Stock requisition batch requires lines"))
            if (
                self.batch_type == "stock_requisition"
                and self.control_qty_total
                and float_compare(
                    self.requisition_qty_total,
                    self.control_qty_total,
                    precision_digits=4,
                )
            ):
                errors.append(
                    _("Qty total %(actual)s does not match control %(control)s")
                    % {
                        "actual": self.requisition_qty_total,
                        "control": self.control_qty_total,
                    }
                )

        line_error_count = (
            len(self.sale_line_ids.filtered(lambda l: l.line_state == "error"))
            + len(self.payment_line_ids.filtered(lambda l: l.line_state == "error"))
            + len(self.stock_line_ids.filtered(lambda l: l.line_state == "error"))
            + len(self.requisition_line_ids.filtered(lambda l: l.line_state == "error"))
        )
        if line_error_count:
            errors.append(
                _("%s line(s) failed mapping or validation") % line_error_count
            )

        self.error_message = "\n".join(errors) if errors else False
        self.state = "error" if errors else "ready"
        return self.state == "ready"

    def action_post(self):
        for batch in self:
            batch._check_post_access()
            if batch.state != "ready":
                if batch.state in ("draft", "error"):
                    batch._validate_batch()
                if batch.state != "ready":
                    raise UserError(
                        _("Batch %s is not ready to post: %s")
                        % (batch.name, batch.error_message or batch.state)
                    )
            self.env["vpk.his.posting.service"]._post_batch(batch)
        return True

    def _check_post_access(self):
        self.ensure_one()
        user = self.env.user
        if user.has_group("vpk_his_api.group_his_manager"):
            return
        batch_kind = self.batch_type
        if batch_kind == "reversal" and self.original_batch_id:
            batch_kind = self.original_batch_id.batch_type
        if batch_kind == "revenue" and not user.has_group(
            "vpk_his_api.group_his_accountant"
        ):
            raise UserError(_("Only HIS accountants can post revenue batches."))
        if batch_kind == "stock_issue" and not user.has_group(
            "vpk_his_api.group_his_pharmacist"
        ):
            raise UserError(_("Only HIS pharmacists can post stock issue batches."))
        if batch_kind == "stock_requisition" and not user.has_group(
            "vpk_his_api.group_his_pharmacist"
        ):
            raise UserError(
                _("Only HIS pharmacists can post stock requisition batches.")
            )

    def action_cancel(self):
        for batch in self:
            if batch.state == "posted":
                raise UserError(
                    _("Posted batches cannot be cancelled. Send a reversal batch.")
                )
            batch.state = "cancelled"

    def action_open_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.invoice_ids.ids)],
        }

    def action_open_payments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payments"),
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.payment_ids.ids)],
        }

    def action_open_pickings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Pickings"),
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", self.picking_ids.ids)],
        }

    def to_api_dict(self):
        self.ensure_one()
        errors = []
        for lines in (
            self.sale_line_ids,
            self.payment_line_ids,
            self.stock_line_ids,
            self.requisition_line_ids,
        ):
            for line in lines:
                if line.line_state == "error":
                    errors.append(
                        {
                            "line_external_id": line.line_external_id or False,
                            "message": line.error_message,
                        }
                    )
        if self.error_message:
            errors.append({"line_external_id": False, "message": self.error_message})
        return {
            "ok": True,
            "batch_id": self.id,
            "name": self.name,
            "external_id": self.external_id,
            "source_system": self.source_system,
            "batch_type": self.batch_type,
            "business_date": str(self.business_date) if self.business_date else False,
            "state": self.state,
            "sales_total": self.sales_total,
            "payments_total": self.payments_total,
            "stock_qty_total": self.stock_qty_total,
            "requisition_qty_total": self.requisition_qty_total,
            "source_warehouse_code": self.source_warehouse_code or False,
            "dest_warehouse_code": self.dest_warehouse_code or False,
            "department_code": self.department_code or False,
            "invoice_ids": self.invoice_ids.ids,
            "payment_ids": self.payment_ids.ids,
            "picking_ids": self.picking_ids.ids,
            "errors": errors,
        }
