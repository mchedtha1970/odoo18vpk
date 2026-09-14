from odoo import api, fields, models


HOSPITAL_ITEM_TYPES = [
    ("medicine", "ยา"),
    ("medical_supply", "เวชภัณฑ์ทางการแพทย์"),
    ("material", "วัสดุ"),
    ("equipment", "ครุภัณฑ์"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    hospital_item_type = fields.Selection(
        selection=HOSPITAL_ITEM_TYPES,
        string="ประเภทพัสดุโรงพยาบาล",
        index=True,
        help="ใช้จำแนกรายการสำหรับการจัดซื้อของโรงพยาบาล",
    )

    @api.onchange("categ_id")
    def _onchange_categ_id_hospital_item_type(self):
        category_name = (self.categ_id.complete_name or "").lower()
        if "เวชภัณฑ์ ยา" in category_name:
            self.hospital_item_type = "medicine"
        elif "เวชภัณฑ์มิใช่ยา" in category_name or "วัสดุการแพทย์" in category_name:
            self.hospital_item_type = "medical_supply"
        elif "ครุภัณฑ์" in category_name:
            self.hospital_item_type = "equipment"
        elif self.categ_id:
            self.hospital_item_type = "material"


class ProductProduct(models.Model):
    _inherit = "product.product"

    hospital_item_type = fields.Selection(
        related="product_tmpl_id.hospital_item_type",
        string="ประเภทพัสดุโรงพยาบาล",
        store=True,
        readonly=True,
        index=True,
    )


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    hospital_item_type = fields.Selection(
        related="product_id.hospital_item_type",
        string="ประเภทพัสดุ",
        store=True,
        readonly=True,
    )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    hospital_item_type = fields.Selection(
        related="product_id.hospital_item_type",
        string="ประเภทพัสดุ",
        store=True,
        readonly=True,
    )
    is_free_item = fields.Boolean(
        string="ของแถม",
        default=False,
        index=True,
        help="รายการนี้รับมอบและตรวจรับตามปกติ แต่ไม่มีมูลค่าในใบสั่งซื้อ",
    )
    free_item_source_line_id = fields.Many2one(
        comodel_name="purchase.order.line",
        string="แถมจากรายการ",
        domain="[('order_id', '=', order_id), ('is_free_item', '=', False)]",
        copy=False,
    )
    free_item_note = fields.Char(string="เงื่อนไขของแถม")

    @api.onchange("is_free_item")
    def _onchange_is_free_item(self):
        if self.is_free_item:
            self.price_unit = 0.0
            self.discount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_free_item"):
                vals.update({"price_unit": 0.0, "discount": 0.0})
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("is_free_item"):
            vals.update({"price_unit": 0.0, "discount": 0.0})
        elif "price_unit" in vals or "discount" in vals:
            free_lines = self.filtered("is_free_item")
            paid_lines = self - free_lines
            result = True
            if paid_lines:
                result = super(PurchaseOrderLine, paid_lines).write(vals)
            if free_lines:
                free_vals = dict(vals, price_unit=0.0, discount=0.0)
                result = (
                    super(PurchaseOrderLine, free_lines).write(free_vals)
                    and result
                )
            return result
        return super().write(vals)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    hospital_item_type_summary = fields.Char(
        string="กลุ่มพัสดุในใบสั่งซื้อ",
        compute="_compute_hospital_item_type_summary",
        store=True,
    )
    free_item_count = fields.Integer(
        string="จำนวนรายการของแถม",
        compute="_compute_free_item_and_discount",
        store=True,
    )
    total_discount_amount = fields.Monetary(
        string="ส่วนลดรวม",
        compute="_compute_free_item_and_discount",
        store=True,
        currency_field="currency_id",
    )

    @api.depends("order_line.hospital_item_type")
    def _compute_hospital_item_type_summary(self):
        labels = dict(HOSPITAL_ITEM_TYPES)
        type_order = [item_type for item_type, _label in HOSPITAL_ITEM_TYPES]
        for order in self:
            present_types = set(
                order.order_line.mapped("hospital_item_type")
            )
            order.hospital_item_type_summary = ", ".join(
                labels[item_type]
                for item_type in type_order
                if item_type in present_types
            )

    @api.depends(
        "order_line.is_free_item",
        "order_line.product_qty",
        "order_line.price_unit",
        "order_line.discount",
    )
    def _compute_free_item_and_discount(self):
        for order in self:
            normal_lines = order.order_line.filtered(
                lambda line: not line.display_type and not line.is_free_item
            )
            order.free_item_count = len(
                order.order_line.filtered("is_free_item")
            )
            order.total_discount_amount = sum(
                line.product_qty * line.price_unit * line.discount / 100.0
                for line in normal_lines
            )
