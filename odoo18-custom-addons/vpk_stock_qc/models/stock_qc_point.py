# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockQcPoint(models.Model):
    _name = "vpk.stock.qc.point"
    _description = "จุดควบคุมคุณภาพสินค้ารับเข้า"
    _order = "sequence, id"

    name = fields.Char(
        string="รหัส",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    sequence = fields.Integer(default=10)
    title = fields.Char(string="หัวข้อตรวจ", required=True)
    active = fields.Boolean(default=True)
    test_type = fields.Selection(
        selection=[
            ("passfail", "ผ่าน/ไม่ผ่าน"),
            ("measure", "วัดค่า"),
        ],
        string="ประเภทการตรวจ",
        required=True,
        default="passfail",
    )
    uom = fields.Char(string="หน่วย")
    tolerance_min = fields.Float(string="ค่าต่ำสุด", digits=(16, 4))
    tolerance_max = fields.Float(string="ค่าสูงสุด", digits=(16, 4))
    product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="vpk_stock_qc_point_product_rel",
        string="สินค้า",
        help="ว่างไว้ใช้กับทุกรายการในใบรับ",
    )
    product_category_ids = fields.Many2many(
        comodel_name="product.category",
        relation="vpk_stock_qc_point_category_rel",
        string="หมวดสินค้า",
        help="ว่างไว้ไม่จำกัดหมวด",
    )
    picking_type_ids = fields.Many2many(
        comodel_name="stock.picking.type",
        relation="vpk_stock_qc_point_picking_type_rel",
        string="ประเภทปฏิบัติการ",
        required=True,
        domain="[('code', '=', 'incoming')]",
    )
    note = fields.Text(string="คำแนะนำ")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    cold_chain = fields.Boolean(
        string="เฉพาะ Cold Chain",
        help="ใช้กับสินค้าที่ติ๊ก Cold Chain เท่านั้น",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.stock.qc.point") or "New"
                )
        return super().create(vals_list)

    def _applies_to(self, product):
        self.ensure_one()
        if self.cold_chain and not product.cold_chain:
            return False
        if not self.product_ids and not self.product_category_ids:
            return True
        if product in self.product_ids:
            return True
        category = product.categ_id
        while category:
            if category in self.product_category_ids:
                return True
            category = category.parent_id
        return False

    @api.model
    def _central_receipt_type(self):
        warehouse = self.env["stock.warehouse"].search([("code", "=", "WH")], limit=1)
        if not warehouse:
            warehouse = self.env["stock.warehouse"].search(
                [("name", "=", "คลังกลาง")], limit=1
            )
        picking_type = warehouse.in_type_id if warehouse else self.env["stock.picking.type"]
        if not picking_type:
            raise UserError(_("ไม่พบประเภทการรับสินค้าของคลังกลาง"))
        return picking_type

    def _limit_to_central_receipt(self, picking_type):
        for point in self:
            if point.picking_type_ids != picking_type:
                point.picking_type_ids = picking_type

    @api.model
    def _ensure_cold_chain_point(self):
        picking_type = self._central_receipt_type()
        point = self.env.ref(
            "vpk_stock_qc.qc_point_cold_chain_truck_temp",
            raise_if_not_found=False,
        )
        if point:
            point._limit_to_central_receipt(picking_type)
            return
        point = self.create({
            "title": "อุณหภูมิรถขนส่ง ณ จุดรับพัสดุ",
            "test_type": "measure",
            "uom": "°C",
            "tolerance_min": 2.0,
            "tolerance_max": 8.0,
            "cold_chain": True,
            "picking_type_ids": [(6, 0, picking_type.ids)],
            "note": (
                "ยากลุ่ม Cold Chain ต้องบันทึกอุณหภูมิรถขนส่งตอนรับพัสดุ "
                "เกณฑ์ 2–8 °C หากอุณหภูมินอกช่วงนี้ รับเข้าคลังไม่ได้"
            ),
        })
        self.env["ir.model.data"].create({
            "module": "vpk_stock_qc",
            "name": "qc_point_cold_chain_truck_temp",
            "model": self._name,
            "res_id": point.id,
            "noupdate": True,
        })

    @api.model
    def _ensure_receipt_checklist_points(self):
        category = self.env["product.category"].search(
            [("complete_name", "=", "กลุ่มวัสดุ / 01. เวชภัณฑ์ ยา")],
            limit=1,
        )
        if not category:
            raise UserError(_("ไม่พบหมวดเวชภัณฑ์ยาสำหรับจุดตรวจรับยา"))
        picking_type = self._central_receipt_type()
        checklist = [
            (
                "qc_point_gr_do",
                110,
                "ใบส่งของ/ใบกำกับภาษี",
                False,
                "ตรวจชื่อบริษัทผู้ขาย ชื่อยา รูปแบบยา ความแรง และจำนวนให้ตรงกับใบสั่งซื้อ",
            ),
            (
                "qc_point_gr_coa",
                120,
                "ใบรับรองวิเคราะห์คุณภาพ (CoA)",
                False,
                "ต้องมี CoA ของล็อตนั้น ตรวจค่า Assay วันหมดอายุ และเลขที่ผลิตให้ตรงกับตัวสินค้า",
            ),
            (
                "qc_point_gr_temp_log",
                130,
                "อุณหภูมิระหว่างการขนส่ง",
                True,
                "ตรวจ Temperature Datalogger หรือ Indicator Chip ว่าไม่มีการแจ้งเตือนอุณหภูมิหลุดเกณฑ์",
            ),
            (
                "qc_point_gr_package",
                140,
                "สภาพกล่อง/ภาชนะบรรจุ",
                False,
                "กล่องต้องสมบูรณ์ ไม่บุบ ฉีกขาด เปียกชื้น หรือมีร่องรอยแกะหรือเทปกาวถูกทำลาย",
            ),
            (
                "qc_point_gr_seal",
                150,
                "ซีลป้องกันการปลอมแปลง",
                False,
                "ซีลหรือรอยพับต้องอยู่ในสภาพสมบูรณ์",
            ),
            (
                "qc_point_gr_label",
                160,
                "ฉลากสินค้า",
                False,
                "ตรวจชื่อยา เลขที่ผลิต วันผลิตและวันหมดอายุ และเลขทะเบียนตำรับยา",
            ),
            (
                "qc_point_gr_content",
                170,
                "สภาพตัวยาภายใน",
                False,
                "สุ่มตรวจยาในกล่อง เช่น ยาน้ำไม่ตกตะกอนหรือเปลี่ยนสี ยาเม็ดและแผงบลิสเตอร์ไม่รั่วพอง",
            ),
        ]
        for xml_name, sequence, title, cold_chain, note in checklist:
            point = self.env.ref(
                f"vpk_stock_qc.{xml_name}", raise_if_not_found=False
            )
            if point:
                point._limit_to_central_receipt(picking_type)
                continue
            point = self.create({
                "title": title,
                "sequence": sequence,
                "test_type": "passfail",
                "cold_chain": cold_chain,
                "product_category_ids": [(6, 0, category.ids)],
                "picking_type_ids": [(6, 0, picking_type.ids)],
                "note": note,
            })
            self.env["ir.model.data"].create({
                "module": "vpk_stock_qc",
                "name": xml_name,
                "model": self._name,
                "res_id": point.id,
                "noupdate": True,
            })

    @api.model
    def _matches(self, products, picking_type):
        if not picking_type or not products:
            return []
        points = self.search([("picking_type_ids", "in", picking_type.id)])
        matches = []
        for point in points:
            for product in products:
                if point._applies_to(product):
                    matches.append((point, product))
        return matches

    def _uses_tolerance(self):
        self.ensure_one()
        return self.test_type == "measure" and (self.tolerance_min or self.tolerance_max)


class StockQcCheck(models.Model):
    _name = "vpk.stock.qc.check"
    _description = "รายการตรวจตามจุดควบคุม"
    _order = "id"

    qc_id = fields.Many2one(
        comodel_name="vpk.stock.qc",
        required=True,
        ondelete="cascade",
        index=True,
    )
    line_id = fields.Many2one(
        comodel_name="vpk.stock.qc.line",
        ondelete="cascade",
        index=True,
    )
    point_id = fields.Many2one(
        comodel_name="vpk.stock.qc.point",
        string="จุดควบคุม",
        required=True,
        ondelete="restrict",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า",
        required=True,
    )
    title = fields.Char(string="หัวข้อตรวจ", required=True)
    test_type = fields.Selection(
        selection=[
            ("passfail", "ผ่าน/ไม่ผ่าน"),
            ("measure", "วัดค่า"),
        ],
        string="ประเภทการตรวจ",
        required=True,
    )
    measure = fields.Float(string="ค่าที่วัด", digits=(16, 4))
    tolerance_min = fields.Float(related="point_id.tolerance_min")
    tolerance_max = fields.Float(related="point_id.tolerance_max")
    uom = fields.Char(related="point_id.uom", string="หน่วย")
    note = fields.Text(related="point_id.note")
    quality_state = fields.Selection(
        selection=[
            ("none", "รอตรวจ"),
            ("pass", "ผ่าน"),
            ("fail", "ไม่ผ่าน"),
        ],
        string="ผล",
        default="none",
        required=True,
        copy=False,
    )
    user_id = fields.Many2one(comodel_name="res.users", string="ผู้ตรวจ", copy=False)
    control_date = fields.Datetime(string="วันที่ตรวจ", copy=False)
    picking_id = fields.Many2one(related="qc_id.picking_id", store=True)

    def _uses_tolerance(self):
        self.ensure_one()
        return self.point_id._uses_tolerance()

    def _measure_passes(self):
        self.ensure_one()
        return self.tolerance_min <= self.measure <= self.tolerance_max

    def _ensure_draft(self):
        locked = self.filtered(lambda check: check.qc_id.state != "draft")
        if locked:
            raise UserError(_("ใบที่บันทึกผลแล้ว แก้ได้หลังกดตรวจใหม่"))

    def do_pass(self):
        self._ensure_draft()
        self.write({
            "quality_state": "pass",
            "user_id": self.env.uid,
            "control_date": fields.Datetime.now(),
        })
        self.line_id._refresh_result_from_checks()
        return True

    def do_fail(self):
        self._ensure_draft()
        self.write({
            "quality_state": "fail",
            "user_id": self.env.uid,
            "control_date": fields.Datetime.now(),
        })
        self.line_id._refresh_result_from_checks()
        for check in self:
            check.qc_id.message_post(
                body=_("ไม่ผ่านจุดควบคุม %(title)s ของ %(product)s")
                % {"title": check.title, "product": check.product_id.display_name}
            )
        return True

    def do_measure(self):
        self.ensure_one()
        if self._measure_passes():
            return self.do_pass()
        return self.do_fail()

    def action_open_wizard(self, current_check_id=None):
        checks = self.sorted("id")
        current = self.browse(current_check_id) if current_check_id else checks[:1]
        return {
            "type": "ir.actions.act_window",
            "name": current.title or _("ตรวจคุณภาพ"),
            "res_model": "vpk.stock.qc.check.wizard",
            "view_mode": "form",
            "views": [(
                self.env.ref("vpk_stock_qc.view_qc_check_wizard").id,
                "form",
            )],
            "target": "new",
            "context": {
                "default_check_ids": checks.ids,
                "default_current_check_id": current.id,
                "vpk_qc_from_validate": self.env.context.get("vpk_qc_from_validate"),
            },
        }
