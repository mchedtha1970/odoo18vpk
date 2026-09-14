from odoo import api, fields, models
from odoo.exceptions import AccessError

VPK_VENDOR_PAYABLE_CODE = "2101010107.101"

VAT_TYPE_SELECTION = [
    ("vat_registered", "จดทะเบียน VAT (Registered)"),
    ("vat_non_registered", "ไม่จดทะเบียน VAT (Non-Registered)"),
    ("vat_exempt", "ได้รับยกเว้น VAT (Exempt)"),
    ("government", "หน่วยงานราชการ (Government)"),
    ("foreign", "ผู้ขายต่างประเทศ (Foreign)"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    vat_type = fields.Selection(
        selection=VAT_TYPE_SELECTION,
        string="ประเภท VAT",
        tracking=True,
        help="ประเภทการจดทะเบียนภาษีมูลค่าเพิ่มของผู้จำหน่าย\n"
             "- จดทะเบียน VAT: ภาษี 7%\n"
             "- ไม่จดทะเบียน VAT: ภาษี 0%\n"
             "- ได้รับยกเว้น VAT: ภาษี 0% (ยกเว้น)\n"
             "- หน่วยงานราชการ: ภาษี 0%\n"
             "- ต่างประเทศ: ภาษี 0% / ตามข้อตกลง",
    )

    @api.onchange("vat_type")
    def _onchange_vat_type_set_fiscal_position(self):
        """เมื่อเลือกประเภท VAT ให้ set Fiscal Position อัตโนมัติ"""
        if not self.vat_type:
            return
        fp_map = {
            "vat_registered": "vpk_vendor_security.fp_vat_registered",
            "vat_non_registered": "vpk_vendor_security.fp_vat_non_registered",
            "vat_exempt": "vpk_vendor_security.fp_vat_exempt",
            "government": "vpk_vendor_security.fp_government",
            "foreign": "vpk_vendor_security.fp_foreign",
        }
        xmlid = fp_map.get(self.vat_type)
        if xmlid:
            fp = self.env.ref(xmlid, raise_if_not_found=False)
            if fp:
                self.property_account_position_id = fp

    def _vpk_vendor_payable_account(self):
        return self.env["account.account"].sudo().search(
            [
                ("code", "=", VPK_VENDOR_PAYABLE_CODE),
                ("account_type", "=", "liability_payable"),
                ("deprecated", "=", False),
            ],
            limit=1,
        )

    def _vpk_is_vendor_vals(self, vals):
        if vals.get("supplier_rank"):
            return True
        return bool(self.env.context.get("default_supplier_rank"))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "property_account_payable_id" not in fields_list:
            return res
        if res.get("supplier_rank") or self.env.context.get("default_supplier_rank"):
            payable = self._vpk_vendor_payable_account()
            if payable:
                res["property_account_payable_id"] = payable.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        payable = self._vpk_vendor_payable_account()
        if payable:
            for vals in vals_list:
                if self._vpk_is_vendor_vals(vals) and not vals.get("property_account_payable_id"):
                    vals["property_account_payable_id"] = payable.id
        return super().create(vals_list)

    def unlink(self):
        if not self.env.su and not self.env.user.has_group(
            "vpk_vendor_security.group_vendor_admin"
        ):
            raise AccessError(
                self.env._(
                    "คุณไม่มีสิทธิ์ลบข้อมูลผู้จำหน่าย "
                    "กรุณาติดต่อผู้ดูแลระบบผู้จำหน่าย (Vendor Administrator)"
                )
            )
        return super().unlink()

    def write(self, vals):
        if not self.env.su and not self.env.user.has_group(
            "vpk_vendor_security.group_vendor_editor"
        ):
            vendor_fields = {
                "name", "vat", "street", "street2", "city", "zip",
                "country_id", "state_id", "phone", "mobile", "email",
                "website", "supplier_rank", "customer_rank",
                "property_account_payable_id", "property_account_receivable_id",
                "property_payment_term_id", "category_id", "bank_ids",
                "ref", "company_type", "company_registry",
            }
            if vendor_fields & set(vals.keys()):
                raise AccessError(
                    self.env._(
                        "คุณไม่มีสิทธิ์แก้ไขข้อมูลผู้จำหน่าย "
                        "กรุณาติดต่อผู้จัดการข้อมูลผู้จำหน่าย (Vendor Editor)"
                    )
                )
        return super().write(vals)
