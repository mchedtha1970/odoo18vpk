# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


STORAGE_METHODS = [
    ("room", "อุณหภูมิห้อง"),
    ("cold", "ห้องเย็น"),
]

NED_GROUPS = [
    ("a", "บัญชี ก"),
    ("b", "บัญชี ข"),
    ("c", "บัญชี ค"),
    ("d", "บัญชี ง"),
    ("e", "บัญชี จ"),
    ("non_ed", "นอกบัญชียาหลักแห่งชาติ"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    egp_purchase_name = fields.Text(
        string="ชื่อสำหรับซื้อใน e-GP",
        help="ชื่อสินค้าที่ใช้ตอนจัดซื้อในระบบ e-GP "
        "จะถูกดึงไปแสดงในรายการใบขอซื้อ (PR) และใบสั่งซื้อ (PO) เมื่อเลือกสินค้า",
        copy=True,
    )
    # TOR 2.1.1 — ข้อมูลยา/เวชภัณฑ์/วัสดุ/ครุภัณฑ์/วัสดุวิทยาศาสตร์
    generic_name = fields.Char(string="ชื่อสามัญ", index=True, copy=True)
    trade_name = fields.Char(string="ชื่อการค้า", index=True, copy=True)
    manufacturer_name = fields.Char(string="ชื่อผู้ผลิต", copy=True)
    distributor_name = fields.Char(string="ชื่อตัวแทนจำหน่าย", copy=True)
    packaging_type = fields.Char(
        string="ชนิดการบรรจุ",
        help="เช่น แผง ขวด ซอง หลอด กล่อง",
        copy=True,
    )
    pack_size = fields.Char(
        string="ขนาดบรรจุ",
        help="เช่น 10 เม็ด/แผง, 100 เม็ด/กล่อง",
        copy=True,
    )
    storage_method = fields.Selection(
        selection=STORAGE_METHODS,
        string="วิธีการเก็บรักษา",
        index=True,
        copy=True,
        help="อุณหภูมิห้อง หรือ ห้องเย็น",
    )
    drug_category = fields.Char(string="Drug Category", copy=True)
    ned_group = fields.Selection(
        selection=NED_GROUPS,
        string="กลุ่มบัญชียาหลักแห่งชาติ",
        index=True,
        copy=True,
    )
    pharmaco_group = fields.Char(string="กลุ่ม Pharmaco", copy=True)
    generic_code = fields.Char(string="Generic Code", index=True, copy=True)
    # TOR 2.1.2 — รหัสมาตรฐาน
    tmt_tpu = fields.Char(string="TMT TPU", index=True, copy=True)
    tmt_fsn = fields.Char(string="TMT FSN", copy=True)
    tmt_gpu = fields.Char(string="TMT GPU", index=True, copy=True)
    gmu_name = fields.Char(string="GMU Name", copy=True)
    manufacturer_market_code = fields.Char(
        string="รหัสผู้ผลิต/ผู้ทำการตลาด",
        copy=True,
    )
    vendor_product_code = fields.Char(
        string="รหัสสินค้าผู้จำหน่าย",
        index=True,
        copy=True,
    )
    drug_code_24 = fields.Char(
        string="รหัสยา 24 หลัก",
        size=24,
        index=True,
        copy=True,
        help="รหัสยามาตรฐาน 24 หลัก เป็นตัวเลขเท่านั้น",
    )

    def action_open_uom_change_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Change Product UoM"),
            "res_model": "vpk.product.uom.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
            },
        }

    @api.constrains("drug_code_24")
    def _check_drug_code_24(self):
        for product in self:
            code = (product.drug_code_24 or "").strip()
            if code and not (len(code) == 24 and code.isdigit()):
                raise ValidationError(
                    _("รหัสยา 24 หลักของ %s ต้องเป็นตัวเลข 24 หลัก")
                    % (product.display_name,)
                )

    @api.onchange("storage_method")
    def _onchange_storage_method(self):
        if "cold_chain" in self._fields and self.storage_method in ("room", "cold"):
            self.cold_chain = self.storage_method == "cold"

    @api.onchange("ned_group")
    def _onchange_ned_group(self):
        if "drug_list_type" in self._fields and self.ned_group:
            self.drug_list_type = (
                "non_ed" if self.ned_group == "non_ed" else "ed"
            )

    def _link_item_master_fields(self, vals):
        """Keep cold-chain and ED/Non-ED aligned with the TOR master fields."""
        vals = dict(vals)
        code = vals.get("drug_code_24")
        if isinstance(code, str):
            vals["drug_code_24"] = code.strip()
        storage = vals.get("storage_method")
        if (
            storage in ("room", "cold")
            and "cold_chain" in self._fields
            and "cold_chain" not in vals
        ):
            vals["cold_chain"] = storage == "cold"
        ned = vals.get("ned_group")
        if ned and "drug_list_type" in self._fields and "drug_list_type" not in vals:
            vals["drug_list_type"] = "non_ed" if ned == "non_ed" else "ed"
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._link_item_master_fields(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        """Allow base UoM change when wizard sets context flag.

        Stock's write() blocks uom_id if any stock.move exists. The wizard
        converts related quantities first, then writes with this flag.
        """
        vals = self._link_item_master_fields(vals)
        if self.env.context.get("vpk_allow_uom_change") and "uom_id" in vals:
            uom_id = vals.pop("uom_id")
            res = True
            if vals:
                res = super().write(vals)
            if self.ids:
                self.env.cr.execute(
                    "UPDATE product_template SET uom_id = %s WHERE id IN %s",
                    (uom_id, tuple(self.ids)),
                )
                self.invalidate_recordset(["uom_id", "uom_name", "uom_category_id"])
            return res
        return super().write(vals)
