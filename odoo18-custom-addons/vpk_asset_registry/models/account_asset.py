# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    fiscal_year = fields.Char(
        string="ปีงบประมาณ",
        index=True,
        tracking=True,
    )
    asset_description = fields.Text(
        string="คำอธิบายรายการสินทรัพย์",
    )
    acquisition_date = fields.Date(
        string="วันที่ได้มาของสินทรัพย์",
        related="date_start",
        readonly=False,
        store=True,
    )
    vendor_code = fields.Char(
        string="รหัสผู้ขาย",
        related="partner_id.ref",
        store=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า/ครุภัณฑ์ต้นทาง",
        tracking=True,
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="เลขที่เอกสารสั่งซื้อ",
        tracking=True,
        index=True,
    )
    purchase_order_date = fields.Date(
        string="วันที่สั่งซื้อ",
        compute="_compute_purchase_source_information",
        store=True,
    )
    vendor_bill_id = fields.Many2one(
        comodel_name="account.move",
        string="ใบแจ้งหนี้",
        domain="[('move_type', 'in', ('in_invoice', 'in_refund'))]",
        tracking=True,
        index=True,
    )
    vendor_bill_reference = fields.Char(
        string="เลขที่ใบแจ้งหนี้ผู้ขาย",
        related="vendor_bill_id.ref",
        store=True,
    )
    vendor_bill_date = fields.Date(
        string="วันที่ใบแจ้งหนี้",
        related="vendor_bill_id.invoice_date",
        store=True,
    )
    gfmis_document_number = fields.Char(
        string="เลขรหัส GFMIS",
        related="purchase_order_id.gfmis_document_number",
        store=True,
    )
    gfmis_commitment_number = fields.Char(
        string="เลขที่ผูกพัน GFMIS",
        related="purchase_order_id.gfmis_commitment_number",
        store=True,
    )
    vcr_number = fields.Char(
        string="เลขรหัส VCR",
        tracking=True,
        index=True,
    )
    vcr_date = fields.Date(
        string="วันที่เอกสาร VCR",
        tracking=True,
    )
    owner_department_code = fields.Char(
        string="รหัสหน่วยงานที่เป็นเจ้าของ",
        related="owning_analytic_account_id.code",
        store=True,
    )
    project_code = fields.Char(
        string="รหัสโครงการ",
        tracking=True,
        index=True,
    )
    project_name = fields.Char(
        string="ชื่อโครงการ",
        tracking=True,
    )
    budget_id = fields.Many2one(
        comodel_name="budget.budget",
        string="งบประมาณ",
        tracking=True,
    )
    fund_source_id = fields.Many2one(
        comodel_name="vpk.budget.fund.source",
        string="แหล่งเงินที่ซื้อ",
        tracking=True,
    )
    custodian_user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ดูแลสินทรัพย์/ครุภัณฑ์",
        tracking=True,
        index=True,
    )
    useful_life_years = fields.Integer(
        string="อายุการใช้งานตามบัญชี (ปี)",
        tracking=True,
    )
    asset_age_years = fields.Float(
        string="อายุการใช้งาน ณ ปัจจุบัน (ปี)",
        compute="_compute_asset_age_years",
        digits=(8, 2),
    )
    registry_note = fields.Text(
        string="หมายเหตุทะเบียนสินทรัพย์",
    )
    maintenance_request_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="asset_id",
        string="ประวัติการซ่อม",
    )
    maintenance_request_count = fields.Integer(
        string="จำนวนประวัติซ่อม",
        compute="_compute_maintenance_summary",
    )
    open_maintenance_count = fields.Integer(
        string="งานซ่อมที่ยังไม่ปิด",
        compute="_compute_maintenance_summary",
    )
    last_maintenance_date = fields.Date(
        string="วันที่แจ้งซ่อมล่าสุด",
        compute="_compute_maintenance_summary",
    )
    last_maintenance_stage_id = fields.Many2one(
        comodel_name="maintenance.stage",
        string="สถานะซ่อมล่าสุด",
        compute="_compute_maintenance_summary",
    )
    total_repair_parts_value = fields.Monetary(
        string="มูลค่าอะไหล่ซ่อมสะสม",
        compute="_compute_maintenance_summary",
        currency_field="currency_id",
    )
    related_contract_ids = fields.One2many(
        comodel_name="asset.related.contract",
        inverse_name="asset_id",
        string="สัญญาที่เกี่ยวข้อง",
    )
    related_contract_count = fields.Integer(
        string="จำนวนสัญญาที่เกี่ยวข้อง",
        compute="_compute_related_contract_summary",
    )
    active_contract_count = fields.Integer(
        string="สัญญาที่มีผลใช้งาน",
        compute="_compute_related_contract_summary",
    )
    component_sequence = fields.Integer(
        string="ลำดับในชุด",
        default=10,
    )
    component_role = fields.Char(
        string="หน้าที่/ความสัมพันธ์ในชุด",
        help="เช่น ตู้ควบคุมหลัก, เครื่องสำรอง, ระบบควบคุมอุณหภูมิ",
        tracking=True,
    )
    component_note = fields.Text(
        string="รายละเอียดส่วนประกอบ",
    )

    @api.depends("purchase_order_id.date_order")
    def _compute_purchase_source_information(self):
        for asset in self:
            asset.purchase_order_date = (
                asset.purchase_order_id.date_order.date()
                if asset.purchase_order_id.date_order
                else False
            )

    @api.depends("acquisition_date")
    def _compute_asset_age_years(self):
        today = fields.Date.context_today(self)
        for asset in self:
            asset.asset_age_years = (
                max((today - asset.acquisition_date).days / 365.25, 0.0)
                if asset.acquisition_date
                else 0.0
            )

    @api.depends(
        "maintenance_request_ids",
        "maintenance_request_ids.request_date",
        "maintenance_request_ids.stage_id",
        "maintenance_request_ids.stage_id.done",
        "maintenance_request_ids.parts_total_value",
        "maintenance_request_ids.archive",
    )
    def _compute_maintenance_summary(self):
        for asset in self:
            requests = asset.maintenance_request_ids.filtered(
                lambda request: not request.archive
            )
            asset.maintenance_request_count = len(requests)
            asset.open_maintenance_count = len(
                requests.filtered(lambda request: not request.stage_id.done)
            )
            latest = requests.sorted(
                key=lambda request: (
                    request.request_date or fields.Date.to_date("1900-01-01"),
                    request.id,
                ),
                reverse=True,
            )[:1]
            asset.last_maintenance_date = latest.request_date
            asset.last_maintenance_stage_id = latest.stage_id
            asset.total_repair_parts_value = sum(
                requests.mapped("parts_total_value")
            )

    @api.depends(
        "related_contract_ids",
        "related_contract_ids.date_start",
        "related_contract_ids.date_end",
    )
    def _compute_related_contract_summary(self):
        today = fields.Date.context_today(self)
        for asset in self:
            contracts = asset.related_contract_ids
            asset.related_contract_count = len(contracts)
            asset.active_contract_count = len(
                contracts.filtered(
                    lambda contract: contract.date_start <= today
                    and (
                        not contract.date_end
                        or contract.date_end >= today
                    )
                )
            )

    @api.onchange("acquisition_date")
    def _onchange_acquisition_date_fiscal_year(self):
        for asset in self:
            if asset.acquisition_date and not asset.fiscal_year:
                year = asset.acquisition_date.year + 543
                if asset.acquisition_date.month >= 10:
                    year += 1
                asset.fiscal_year = str(year)

    @api.onchange("purchase_order_id")
    def _onchange_purchase_order_source(self):
        for asset in self:
            order = asset.purchase_order_id
            if not order:
                continue
            asset.partner_id = order.partner_id
            if len(order.order_line.product_id) == 1:
                asset.product_id = order.order_line.product_id

    @api.onchange("vendor_bill_id")
    def _onchange_vendor_bill_source(self):
        for asset in self:
            bill = asset.vendor_bill_id
            if not bill:
                continue
            asset.partner_id = bill.partner_id
            if bill.invoice_date:
                asset.acquisition_date = bill.invoice_date
            if bill.purchase_id:
                asset.purchase_order_id = bill.purchase_id
            products = bill.invoice_line_ids.product_id
            if len(products) == 1:
                asset.product_id = products

    def action_sync_purchase_source(self):
        for asset in self:
            source_lines = asset.account_move_line_ids.filtered(
                lambda line: line.move_id.move_type
                in ("in_invoice", "in_refund")
            )
            bill = source_lines.move_id[:1]
            purchase_orders = (
                source_lines.purchase_line_id.order_id
                or bill.purchase_id
            )
            products = source_lines.product_id
            values = {}
            if bill:
                values.update({
                    "vendor_bill_id": bill.id,
                    "partner_id": bill.partner_id.id,
                })
                if bill.invoice_date:
                    values["date_start"] = bill.invoice_date
            if purchase_orders:
                values["purchase_order_id"] = purchase_orders[:1].id
            if len(products) == 1:
                values["product_id"] = products.id
            if values:
                asset.write(values)
                asset._set_fiscal_year_if_missing()
                asset.message_post(
                    body=_("อัปเดตแหล่งที่มาของสินทรัพย์จากเอกสารจัดซื้อแล้ว")
                )
        return True

    def action_view_maintenance_history(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ประวัติการซ่อม: %s") % self.display_name,
            "res_model": "maintenance.request",
            "view_mode": "list,form",
            "domain": [("asset_id", "=", self.id)],
            "context": {
                "default_equipment_id": self.equipment_id.id,
            },
        }

    def action_view_related_contracts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("สัญญาที่เกี่ยวข้อง: %s") % self.display_name,
            "res_model": "asset.related.contract",
            "view_mode": "list,form",
            "domain": [("asset_id", "=", self.id)],
            "context": {
                "default_asset_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }

    def _set_fiscal_year_if_missing(self):
        for asset in self.filtered(
            lambda record: record.acquisition_date
            and not record.fiscal_year
        ):
            year = asset.acquisition_date.year + 543
            if asset.acquisition_date.month >= 10:
                year += 1
            asset.fiscal_year = str(year)


class AccountAssetParent(models.Model):
    _inherit = "account.asset.parent"

    set_type = fields.Selection(
        selection=[
            ("electrical", "งานระบบไฟฟ้า"),
            ("air_conditioning", "งานระบบปรับอากาศ"),
            ("building_improvement", "งานปรับปรุงอาคาร"),
            ("plumbing", "งานระบบประปา"),
            ("medical", "ชุดระบบเครื่องมือแพทย์"),
            ("it", "งานระบบเทคโนโลยีสารสนเทศ"),
            ("other", "อื่น ๆ"),
        ],
        string="ประเภทสินทรัพย์ชุด",
        required=True,
        default="other",
        index=True,
    )
    location = fields.Char(
        string="สถานที่ติดตั้ง/พื้นที่ใช้งาน",
    )
    responsible_user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้รับผิดชอบชุดสินทรัพย์",
    )
    owning_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงานเจ้าของ",
    )
    project_code = fields.Char(
        string="รหัสโครงการ",
        index=True,
    )
    description = fields.Text(
        string="รายละเอียดขอบเขตสินทรัพย์ชุด",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )
    component_count = fields.Integer(
        string="จำนวนส่วนประกอบ",
        compute="_compute_asset_set_summary",
    )
    active_component_count = fields.Integer(
        string="ส่วนประกอบที่ใช้งาน",
        compute="_compute_asset_set_summary",
    )
    total_purchase_value = fields.Monetary(
        string="มูลค่าซื้อรวม",
        compute="_compute_asset_set_summary",
        currency_field="currency_id",
    )
    total_residual_value = fields.Monetary(
        string="มูลค่าคงเหลือรวม",
        compute="_compute_asset_set_summary",
        currency_field="currency_id",
    )

    @api.depends(
        "asset_ids",
        "asset_ids.state",
        "asset_ids.purchase_value",
        "asset_ids.value_residual",
    )
    def _compute_asset_set_summary(self):
        for asset_set in self:
            asset_set.component_count = len(asset_set.asset_ids)
            asset_set.active_component_count = len(
                asset_set.asset_ids.filtered(
                    lambda asset: asset.state != "removed"
                )
            )
            asset_set.total_purchase_value = sum(
                asset_set.asset_ids.mapped("purchase_value")
            )
            asset_set.total_residual_value = sum(
                asset_set.asset_ids.mapped("value_residual")
            )
