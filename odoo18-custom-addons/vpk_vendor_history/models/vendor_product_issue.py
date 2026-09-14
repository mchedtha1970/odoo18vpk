from odoo import _, api, fields, models


class VendorProductIssue(models.Model):
    _name = "vendor.product.issue"
    _description = "สินค้าที่มีปัญหาของเจ้าหนี้"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "issue_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="เลขที่",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="เจ้าหนี้ / ผู้จำหน่าย",
        required=True,
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า",
        required=True,
        tracking=True,
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ (PO)",
        domain="[('partner_id', '=', partner_id)]",
        tracking=True,
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="ใบรับสินค้า",
        domain="[('partner_id', '=', partner_id)]",
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="ใบแจ้งหนี้",
        domain="[('partner_id', '=', partner_id), ('move_type', '=', 'in_invoice')]",
    )
    issue_date = fields.Date(
        string="วันที่พบปัญหา",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    issue_type = fields.Selection(
        selection=[
            ("quality", "คุณภาพสินค้าไม่ตรงมาตรฐาน"),
            ("damage", "สินค้าชำรุด/เสียหาย"),
            ("expire", "ใกล้หมดอายุ / หมดอายุ"),
            ("shortage", "จำนวนไม่ครบ"),
            ("wrong_item", "สินค้าผิดชนิด/ผิดสเปก"),
            ("late", "จัดส่งล่าช้า"),
            ("document", "เอกสารไม่ถูกต้อง"),
            ("other", "อื่นๆ"),
        ],
        string="ประเภทปัญหา",
        required=True,
        tracking=True,
    )
    severity = fields.Selection(
        selection=[
            ("low", "ต่ำ"),
            ("medium", "ปานกลาง"),
            ("high", "สูง"),
            ("critical", "วิกฤต"),
        ],
        string="ระดับความรุนแรง",
        required=True,
        default="medium",
        tracking=True,
    )
    qty_affected = fields.Float(
        string="จำนวนที่มีปัญหา",
        digits="Product Unit of Measure",
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วยนับ",
        related="product_id.uom_id",
        store=True,
    )
    lot_name = fields.Char(string="LOT / Serial")
    description = fields.Text(
        string="รายละเอียดปัญหา",
        required=True,
    )
    action_taken = fields.Text(string="การดำเนินการ")
    resolution = fields.Selection(
        selection=[
            ("pending", "รอดำเนินการ"),
            ("return", "ส่งคืนผู้ขาย"),
            ("replace", "เปลี่ยนสินค้าใหม่"),
            ("credit", "ลดหนี้ / Credit Note"),
            ("accept", "รับไว้ใช้ (มีเงื่อนไข)"),
            ("scrap", "ทำลาย / Scrap"),
            ("closed", "ปิดเรื่อง"),
        ],
        string="ผลการแก้ไข",
        default="pending",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("open", "เปิด"),
            ("in_progress", "กำลังดำเนินการ"),
            ("resolved", "แก้ไขแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    reported_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้รายงาน",
        default=lambda self: self.env.user,
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vendor.product.issue")
                    or _("New")
                )
        return super().create(vals_list)

    def action_open(self):
        self.write({"state": "open"})

    def action_in_progress(self):
        self.write({"state": "in_progress"})

    def action_resolve(self):
        for rec in self:
            if rec.resolution == "pending":
                rec.resolution = "closed"
            rec.state = "resolved"

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({"state": "draft"})
