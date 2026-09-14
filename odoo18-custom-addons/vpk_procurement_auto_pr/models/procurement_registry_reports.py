# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    egp_report_winner_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้ชนะการเสนอราคา",
        compute="_compute_egp_report_winner",
        store=True,
    )
    egp_report_winner_amount = fields.Monetary(
        string="วงเงินผู้ชนะ",
        compute="_compute_egp_report_winner",
        store=True,
        currency_field="currency_id",
    )
    egp_report_published_date = fields.Datetime(
        string="วันที่ประกาศผู้ชนะ",
        compute="_compute_egp_report_winner",
        store=True,
    )

    @api.depends(
        "winner_announcement_ids.state",
        "winner_announcement_ids.winner_partner_id",
        "winner_announcement_ids.winner_amount",
        "winner_announcement_ids.published_date",
        "winner_announcement_ids.date",
    )
    def _compute_egp_report_winner(self):
        for requisition in self:
            announcements = requisition.winner_announcement_ids.sorted(
                key=lambda announcement: (
                    announcement.published_date
                    or fields.Datetime.to_datetime(announcement.date)
                    or fields.Datetime.to_datetime("1900-01-01")
                ),
                reverse=True,
            )
            announcement = (
                announcements.filtered(
                    lambda record: record.state == "published"
                )[:1]
                or announcements[:1]
            )
            requisition.egp_report_winner_partner_id = (
                announcement.winner_partner_id
            )
            requisition.egp_report_winner_amount = (
                announcement.winner_amount
            )
            requisition.egp_report_published_date = (
                announcement.published_date
            )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    gfmis_document_number = fields.Char(
        string="เลขที่เอกสาร GFMIS",
        index=True,
        tracking=True,
        copy=False,
    )
    gfmis_commitment_number = fields.Char(
        string="เลขที่ผูกพัน GFMIS",
        index=True,
        tracking=True,
        copy=False,
    )
    gfmis_document_date = fields.Date(
        string="วันที่เอกสาร GFMIS",
        tracking=True,
        copy=False,
    )
    gfmis_fiscal_year = fields.Char(
        string="ปีงบประมาณ GFMIS",
        tracking=True,
        copy=False,
    )
    gfmis_status = fields.Selection(
        selection=[
            ("draft", "รอส่งข้อมูล"),
            ("sent", "ส่งข้อมูลแล้ว"),
            ("committed", "ผูกพันแล้ว"),
            ("error", "ข้อมูลผิดพลาด"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ GFMIS",
        default="draft",
        tracking=True,
        copy=False,
    )
    gfmis_sent_at = fields.Datetime(
        string="วันที่ส่ง GFMIS",
        tracking=True,
        copy=False,
    )
    gfmis_note = fields.Text(
        string="หมายเหตุ GFMIS",
        copy=False,
    )
