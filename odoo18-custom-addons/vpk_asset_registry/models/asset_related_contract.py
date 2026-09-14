# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AssetRelatedContract(models.Model):
    _name = "asset.related.contract"
    _description = "สัญญาที่เกี่ยวข้องกับสินทรัพย์"
    _order = "date_start desc, id desc"

    name = fields.Char(
        string="ชื่อสัญญา",
        required=True,
        index=True,
    )
    contract_number = fields.Char(
        string="เลขที่สัญญา",
        index=True,
    )
    contract_type = fields.Selection(
        selection=[
            ("lease", "สัญญาเช่า"),
            ("maintenance", "สัญญาบำรุงรักษา"),
            ("warranty", "สัญญารับประกัน"),
            ("insurance", "สัญญาประกันภัย"),
            ("service", "สัญญาบริการ"),
            ("other", "อื่น ๆ"),
        ],
        string="ประเภทสัญญา",
        required=True,
        default="maintenance",
        index=True,
    )
    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="สินทรัพย์/ครุภัณฑ์",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="asset_id.company_id",
        store=True,
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="คู่สัญญา/ผู้ให้บริการ",
        index=True,
    )
    date_start = fields.Date(
        string="วันที่เริ่มสัญญา",
        required=True,
        index=True,
    )
    date_end = fields.Date(
        string="วันที่สิ้นสุดสัญญา",
        index=True,
    )
    amount = fields.Monetary(
        string="มูลค่าสัญญา",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="asset_id.currency_id",
    )
    status = fields.Selection(
        selection=[
            ("upcoming", "ยังไม่เริ่ม"),
            ("active", "มีผลใช้งาน"),
            ("expired", "หมดอายุ"),
        ],
        string="สถานะ",
        compute="_compute_status",
    )
    remaining_days = fields.Integer(
        string="จำนวนวันคงเหลือ",
        compute="_compute_status",
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="asset_related_contract_attachment_rel",
        column1="contract_id",
        column2="attachment_id",
        string="ไฟล์สัญญาและเอกสารแนบ",
    )
    attachment_count = fields.Integer(
        string="จำนวนไฟล์",
        compute="_compute_attachment_count",
    )
    note = fields.Text(string="หมายเหตุ")

    @api.depends("date_start", "date_end")
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for contract in self:
            if contract.date_start and contract.date_start > today:
                contract.status = "upcoming"
            elif contract.date_end and contract.date_end < today:
                contract.status = "expired"
            else:
                contract.status = "active"
            contract.remaining_days = (
                (contract.date_end - today).days
                if contract.date_end
                else 0
            )

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for contract in self:
            contract.attachment_count = len(contract.attachment_ids)

    @api.constrains("date_start", "date_end")
    def _check_contract_dates(self):
        for contract in self:
            if (
                contract.date_start
                and contract.date_end
                and contract.date_end < contract.date_start
            ):
                raise ValidationError(
                    "วันที่สิ้นสุดสัญญาต้องไม่น้อยกว่าวันที่เริ่มสัญญา"
                )
