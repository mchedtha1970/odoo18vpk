from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


PROCUREMENT_NATURE = [
    ("buy", "ซื้อ"),
    ("hire", "จ้าง"),
    ("lease", "เช่า"),
]

PROCUREMENT_DOCUMENT = [
    ("contract", "สัญญา"),
    ("order", "ใบสั่งซื้อ/ใบสั่งจ้าง"),
]

PROCUREMENT_CATEGORY = [
    ("contract_buy", "จัดซื้อแบบสัญญา"),
    ("order_buy", "จัดซื้อแบบใบสั่งซื้อ"),
    ("contract_hire", "จัดจ้างแบบสัญญา"),
    ("order_hire", "จัดจ้างแบบใบสั่งจ้าง"),
    ("contract_lease", "เช่าแบบสัญญา"),
    ("order_lease", "เช่าแบบใบสั่ง"),
]


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    procurement_nature = fields.Selection(
        selection=PROCUREMENT_NATURE,
        string="ลักษณะการจัดหา",
        default="buy",
        required=True,
        tracking=True,
    )
    procurement_document = fields.Selection(
        selection=PROCUREMENT_DOCUMENT,
        string="รูปแบบเอกสาร",
        default="order",
        required=True,
        tracking=True,
    )
    procurement_category = fields.Selection(
        selection=PROCUREMENT_CATEGORY,
        string="ประเภทการจัดซื้อจัดจ้าง",
        compute="_compute_procurement_category",
        store=True,
        index=True,
    )

    @api.depends("procurement_nature", "procurement_document")
    def _compute_procurement_category(self):
        for request in self:
            if request.procurement_nature and request.procurement_document:
                request.procurement_category = "%s_%s" % (
                    request.procurement_document,
                    request.procurement_nature,
                )
            else:
                request.procurement_category = False

    @api.onchange("contract_id")
    def _onchange_contract_procurement_classification(self):
        if self.contract_id:
            self.procurement_document = "contract"
            self.procurement_nature = self.contract_id.contract_kind or "buy"

    def action_create_po_by_latest_vendor(self):
        self.ensure_one()
        if self.state not in ("approved", "in_progress"):
            raise UserError(
                _("PR ต้องอยู่ในสถานะอนุมัติแล้วหรือกำลังดำเนินการ")
            )
        request_lines = self.line_ids.filtered(
            lambda line: line.product_id and line.pending_qty_to_receive > 0
        )
        if not request_lines:
            raise UserError(_("ไม่มีรายการคงเหลือที่สามารถสร้าง PO ได้"))

        lines_by_vendor = {}
        missing_products = self.env["product.product"]
        for line in request_lines:
            latest_line = line._get_latest_vendor_purchase_line()
            if not latest_line:
                missing_products |= line.product_id
                continue
            lines_by_vendor.setdefault(latest_line.partner_id, self.env[
                "purchase.request.line"
            ])
            lines_by_vendor[latest_line.partner_id] |= line

        if missing_products:
            raise UserError(
                _("ไม่พบประวัติผู้จำหน่ายล่าสุดสำหรับสินค้า: %s")
                % ", ".join(missing_products.mapped("display_name"))
            )

        wizard_model = self.env[
            "purchase.request.line.make.purchase.order"
        ]
        purchase_order_ids = []
        for vendor, lines in lines_by_vendor.items():
            item_commands = []
            for line in lines:
                item_values = wizard_model._prepare_item(line)
                latest_line = line._get_latest_vendor_purchase_line()
                latest_net_price = latest_line.price_unit * (
                    1 - latest_line.discount / 100.0
                )
                item_values.update({
                    "estimated_cost": latest_net_price
                    * item_values["product_qty"],
                    "keep_estimated_cost": True,
                })
                item_commands.append((0, 0, item_values))
            wizard = wizard_model.create({
                "supplier_id": vendor.id,
                "item_ids": item_commands,
            })
            action = wizard.make_purchase_order()
            purchase_order_ids += action["domain"][0][2]

        purchase_orders = self.env["purchase.order"].browse(
            list(set(purchase_order_ids))
        )
        self.message_post(
            body=_(
                "สร้าง PO แยกตามผู้จำหน่ายล่าสุดจำนวน %(count)s ใบ: "
                "%(orders)s"
            )
            % {
                "count": len(purchase_orders),
                "orders": ", ".join(purchase_orders.mapped("display_name")),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("PO แยกตามผู้จำหน่ายล่าสุด"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", purchase_orders.ids)],
        }


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    latest_vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จำหน่ายล่าสุด",
        compute="_compute_latest_vendor_information",
    )
    latest_vendor_po_id = fields.Many2one(
        comodel_name="purchase.order",
        string="PO ล่าสุด",
        compute="_compute_latest_vendor_information",
    )
    latest_vendor_price = fields.Monetary(
        string="ราคาซื้อล่าสุด",
        compute="_compute_latest_vendor_information",
        currency_field="currency_id",
    )

    def _get_latest_vendor_purchase_line(self):
        self.ensure_one()
        if not self.product_id:
            return self.env["purchase.order.line"]
        domain = [
            ("product_id", "=", self.product_id.id),
            ("order_id.state", "in", ("purchase", "done")),
            ("order_id.partner_id", "!=", False),
            ("price_unit", ">", 0),
        ]
        if "is_free_item" in self.env["purchase.order.line"]._fields:
            domain.append(("is_free_item", "=", False))
        return self.env["purchase.order.line"].search(
            domain,
            order="date_order desc, id desc",
            limit=1,
        )

    @api.depends("product_id")
    def _compute_latest_vendor_information(self):
        for line in self:
            latest_line = line._get_latest_vendor_purchase_line()
            line.latest_vendor_id = latest_line.partner_id
            line.latest_vendor_po_id = latest_line.order_id
            line.latest_vendor_price = (
                latest_line.price_unit * (1 - latest_line.discount / 100.0)
                if latest_line
                else 0.0
            )


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    procurement_nature = fields.Selection(
        related="purchase_request_id.procurement_nature",
        string="ลักษณะการจัดหา",
        store=True,
        readonly=True,
    )
    procurement_document = fields.Selection(
        related="purchase_request_id.procurement_document",
        string="รูปแบบเอกสาร",
        store=True,
        readonly=True,
    )
    procurement_category = fields.Selection(
        related="purchase_request_id.procurement_category",
        string="ประเภทการจัดซื้อจัดจ้าง",
        store=True,
        readonly=True,
    )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    procurement_nature = fields.Selection(
        selection=PROCUREMENT_NATURE,
        string="ลักษณะการจัดหา",
        compute="_compute_procurement_classification",
        store=True,
    )
    procurement_document = fields.Selection(
        selection=PROCUREMENT_DOCUMENT,
        string="รูปแบบเอกสาร",
        compute="_compute_procurement_classification",
        store=True,
    )
    procurement_category = fields.Selection(
        selection=PROCUREMENT_CATEGORY,
        string="ประเภทการจัดซื้อจัดจ้าง",
        compute="_compute_procurement_classification",
        store=True,
        index=True,
    )
    procurement_term_days = fields.Integer(
        string="ระยะเวลาดำเนินการ (วัน)",
        default=30,
        tracking=True,
        help="จำนวนวันนับจากวันที่ยืนยันเพื่อคำนวณวันครบกำหนดอัตโนมัติ",
    )
    procurement_confirmed_date = fields.Date(
        string="วันที่ยืนยันรายการ",
        readonly=True,
        copy=False,
        tracking=True,
    )
    procurement_due_date = fields.Date(
        string="วันที่ครบกำหนด",
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    procurement_urgency = fields.Selection(
        selection=[
            ("normal", "ปกติ"),
            ("urgent", "เร่งด่วน"),
            ("emergency", "ฉุกเฉิน"),
        ],
        string="ระดับความเร่งด่วน",
        default="normal",
        required=True,
        tracking=True,
        index=True,
    )
    urgency_reason = fields.Text(
        string="เหตุผลความเร่งด่วน",
        tracking=True,
    )
    emergency_notified = fields.Boolean(
        string="แจ้งเตือนซื้อฉุกเฉินแล้ว",
        default=False,
        copy=False,
        readonly=True,
    )
    pr_purchase_type_id = fields.Many2one(
        comodel_name="purchase.type",
        string="ประเภทการซื้อจาก PR",
        compute="_compute_pr_purchase_information",
        store=True,
        readonly=True,
    )
    pr_procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="ประเภทการจัดหาจาก PR",
        compute="_compute_pr_purchase_information",
        store=True,
        readonly=True,
    )
    pr_procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="วิธีจัดซื้อจัดจ้างจาก PR",
        compute="_compute_pr_purchase_information",
        store=True,
        readonly=True,
    )
    procurement_fulfillment_status = fields.Selection(
        selection=[
            ("preparing", "กำลังจัดทำ/รอยืนยัน"),
            ("awaiting_receipt", "ยังไม่ได้รับพัสดุ/งาน"),
            ("partial_receipt", "รับพัสดุ/งานบางส่วน"),
            ("received", "รับพัสดุ/งานเรียบร้อยแล้ว"),
            ("awaiting_payment", "รอการจ่ายชำระ"),
            ("paid", "จ่ายชำระแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะติดตามคำสั่งซื้อ",
        compute="_compute_procurement_fulfillment_status",
        store=True,
        index=True,
    )

    @api.depends(
        "contract_id",
        "contract_id.contract_kind",
        "requisition_id",
        "requisition_id.procurement_nature",
        "order_line.purchase_request_lines.request_id.procurement_nature",
        "order_line.purchase_request_lines.request_id.procurement_document",
    )
    def _compute_procurement_classification(self):
        for order in self:
            source_request = order.order_line.mapped(
                "purchase_request_lines.request_id"
            )[:1]
            if order.contract_id:
                document = "contract"
                nature = order.contract_id.contract_kind or "buy"
            elif order.requisition_id and order.requisition_id.procurement_nature:
                document = order.requisition_id.procurement_document or "order"
                nature = order.requisition_id.procurement_nature
            elif source_request:
                document = source_request.procurement_document or "order"
                nature = source_request.procurement_nature or "buy"
            else:
                document = "order"
                nature = "buy"
            order.procurement_document = document
            order.procurement_nature = nature
            order.procurement_category = "%s_%s" % (document, nature)

    @api.depends(
        "order_line.purchase_request_lines.request_id.purchase_type_id",
        "order_line.purchase_request_lines.request_id.procurement_type_id",
        "order_line.purchase_request_lines.request_id.procurement_method_id",
    )
    def _compute_pr_purchase_information(self):
        for order in self:
            requests = order.order_line.mapped(
                "purchase_request_lines.request_id"
            )
            purchase_types = requests.mapped("purchase_type_id")
            procurement_types = requests.mapped("procurement_type_id")
            procurement_methods = requests.mapped("procurement_method_id")
            order.pr_purchase_type_id = (
                purchase_types if len(purchase_types) == 1 else False
            )
            order.pr_procurement_type_id = (
                procurement_types if len(procurement_types) == 1 else False
            )
            order.pr_procurement_method_id = (
                procurement_methods if len(procurement_methods) == 1 else False
            )

    @api.depends(
        "state",
        "receipt_status",
        "invoice_ids.state",
        "invoice_ids.payment_state",
        "invoice_ids.amount_residual",
    )
    def _compute_procurement_fulfillment_status(self):
        for order in self:
            if order.state == "cancel":
                status = "cancelled"
            elif order.state not in ("purchase", "done"):
                status = "preparing"
            else:
                posted_bills = order.invoice_ids.filtered(
                    lambda bill: bill.state == "posted"
                )
                if posted_bills and all(
                    bill.payment_state in ("paid", "in_payment", "reversed")
                    for bill in posted_bills
                ):
                    status = "paid"
                elif posted_bills:
                    status = "awaiting_payment"
                elif order.receipt_status == "full":
                    status = "received"
                elif order.receipt_status == "partial":
                    status = "partial_receipt"
                else:
                    status = "awaiting_receipt"
            order.procurement_fulfillment_status = status

    @api.onchange("procurement_nature")
    def _onchange_procurement_nature_term(self):
        default_days = {"buy": 30, "hire": 90, "lease": 365}
        if self.procurement_nature:
            self.procurement_term_days = default_days[self.procurement_nature]

    @api.constrains("procurement_urgency", "urgency_reason")
    def _check_emergency_reason(self):
        for order in self:
            if (
                order.procurement_urgency == "emergency"
                and not (order.urgency_reason or "").strip()
            ):
                raise ValidationError(
                    _("กรุณาระบุเหตุผลสำหรับใบสั่งซื้อฉุกเฉิน")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("procurement_urgency") in ("urgent", "emergency"):
                vals["priority"] = "1"
        orders = super().create(vals_list)
        if not self.env.context.get("skip_emergency_notification"):
            orders.filtered(
                lambda order: order.procurement_urgency == "emergency"
            )._notify_emergency_purchase()
        return orders

    def write(self, vals):
        emergency_orders = self.browse()
        if vals.get("procurement_urgency") == "emergency":
            emergency_orders = self.filtered(
                lambda order: order.procurement_urgency != "emergency"
                or not order.emergency_notified
            )
            vals["priority"] = "1"
        elif vals.get("procurement_urgency") == "urgent":
            vals["priority"] = "1"
        elif vals.get("procurement_urgency") == "normal":
            vals["priority"] = "0"
            vals["emergency_notified"] = False
        result = super().write(vals)
        if (
            emergency_orders
            and not self.env.context.get("skip_emergency_notification")
        ):
            emergency_orders._notify_emergency_purchase()
        return result

    def _notify_emergency_purchase(self):
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for order in self.filtered(
            lambda record: record.procurement_urgency == "emergency"
            and not record.emergency_notified
        ):
            assigned_user = order.user_id or self.env.user
            order.message_post(
                body=_(
                    "<strong>แจ้งเตือนการซื้อฉุกเฉิน</strong><br/>"
                    "ผู้รับผิดชอบ: %(user)s<br/>เหตุผล: %(reason)s"
                )
                % {
                    "user": assigned_user.display_name,
                    "reason": order.urgency_reason,
                },
                message_type="notification",
            )
            order.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=assigned_user.id,
                summary=_("ตรวจสอบใบสั่งซื้อฉุกเฉิน %s") % order.name,
                note=order.urgency_reason,
                date_deadline=fields.Date.context_today(order),
            )
            order.with_context(skip_emergency_notification=True).write({
                "emergency_notified": True,
            })

    def button_confirm(self):
        result = super().button_confirm()
        for order in self.filtered(
            lambda record: record.state in ("purchase", "done")
        ):
            confirmed_date = fields.Date.to_date(
                order.date_approve or fields.Datetime.now()
            )
            if order.contract_id and order.contract_id.date_end:
                due_date = order.contract_id.date_end
            else:
                due_date = confirmed_date + timedelta(
                    days=max(order.procurement_term_days, 0)
                )
            order.write({
                "procurement_confirmed_date": confirmed_date,
                "procurement_due_date": due_date,
            })
            order.order_line.write({
                "date_planned": fields.Datetime.to_datetime(due_date),
            })
            order.message_post(
                body=_(
                    "คำนวณวันครบกำหนดอัตโนมัติ: %(due)s "
                    "(ยืนยัน %(confirmed)s / ระยะเวลา %(days)s วัน)"
                )
                % {
                    "due": due_date,
                    "confirmed": confirmed_date,
                    "days": order.procurement_term_days,
                }
            )
        return result


class PurchaseContract(models.Model):
    _inherit = "purchase.contract"

    contract_term_days = fields.Integer(
        string="ระยะเวลาสัญญา (วัน)",
        default=365,
        tracking=True,
        help="ใช้คำนวณวันสิ้นสุดสัญญาอัตโนมัติเมื่อยืนยัน",
    )
    confirmed_date = fields.Date(
        string="วันที่ยืนยันสัญญา",
        readonly=True,
        copy=False,
        tracking=True,
    )

    @api.onchange("contract_kind")
    def _onchange_contract_kind_term(self):
        default_days = {"buy": 365, "hire": 180, "lease": 365}
        if self.contract_kind:
            self.contract_term_days = default_days[self.contract_kind]

    def action_confirm(self):
        result = super().action_confirm()
        today = fields.Date.context_today(self)
        for contract in self:
            start_date = contract.date_start or today
            end_date = contract.date_end or (
                start_date + timedelta(days=max(contract.contract_term_days, 0))
            )
            contract.write({
                "date_start": start_date,
                "date_end": end_date,
                "confirmed_date": today,
            })
            contract.message_post(
                body=_(
                    "คำนวณวันครบกำหนดสัญญาอัตโนมัติ: %(end)s "
                    "(เริ่ม %(start)s / ระยะเวลา %(days)s วัน)"
                )
                % {
                    "end": end_date,
                    "start": start_date,
                    "days": contract.contract_term_days,
                }
            )
        return result
