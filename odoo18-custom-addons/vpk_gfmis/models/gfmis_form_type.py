# -*- coding: utf-8 -*-
from odoo import fields, models


class GfmisFormType(models.Model):
    _name = "gfmis.form.type"
    _description = "แบบฟอร์ม GFMIS"
    _order = "sequence, code"

    name = fields.Char(string="ชื่อแบบฟอร์ม", required=True, translate=True)
    code = fields.Char(string="รหัสแบบฟอร์ม", required=True, index=True)
    sap_tcode = fields.Char(string="คำสั่งงาน SAP")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    doc_class = fields.Selection(
        [
            ("request", "ขอเบิกเงิน"),
            ("agency_pay", "ขอจ่ายโดยส่วนราชการ"),
            ("return", "เบิกเกินส่งคืน / ส่งคืนฝากคลัง"),
            ("approve", "อนุมัติรายการ"),
            ("other", "อื่น ๆ"),
        ],
        string="กลุ่มเอกสาร",
        required=True,
        default="request",
    )
    requires_po = fields.Boolean(
        string="ต้องอ้างใบสั่งซื้อสั่งจ้าง (PO)",
        help="ตามคู่มือ: ขบ.01 / ขบ.11 และทข.01 ต้องค้นหาใบสั่งซื้อใน GFMIS",
    )
    fund_type = fields.Selection(
        [
            ("budget", "เงินงบประมาณ"),
            ("extra", "เงินนอกงบประมาณ"),
            ("loan", "เงินกู้"),
            ("allocated", "เงินรายได้จัดสรร"),
            ("any", "ไม่จำกัด"),
        ],
        string="แหล่งเงิน",
        default="any",
        required=True,
    )
    payment_method = fields.Selection(
        [
            ("direct", "จ่ายตรงผู้ขาย"),
            ("through", "จ่ายผ่านส่วนราชการ"),
            ("either", "ได้ทั้งสองวิธี"),
        ],
        string="วิธีการชำระเงิน",
        default="either",
        required=True,
    )
    note = fields.Text(string="หมายเหตุ")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "รหัสแบบฟอร์มซ้ำ"),
    ]
