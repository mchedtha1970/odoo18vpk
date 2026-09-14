from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    product_specification_ids = fields.One2many(
        comodel_name="purchase.product.specification",
        inverse_name="request_id",
        string="รายละเอียดคุณลักษณะพัสดุ",
    )
    product_specification_count = fields.Integer(
        compute="_compute_product_specification_count",
    )

    def _compute_product_specification_count(self):
        Spec = self.env["purchase.product.specification"].sudo()
        counts = dict(
            (row["request_id"][0], row["request_id_count"])
            for row in Spec.read_group(
                [("request_id", "in", self.ids)],
                ["request_id"],
                ["request_id"],
            )
        )
        for rec in self:
            rec.product_specification_count = counts.get(rec.id, 0)

    def action_view_product_specifications(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "รายละเอียดคุณลักษณะพัสดุ",
            "res_model": "purchase.product.specification",
            "view_mode": "list,form",
            "domain": [("request_id", "=", self.id)],
            "context": {"default_request_id": self.id},
        }

    def action_create_product_specification(self):
        """สร้างเอกสารคุณลักษณะและ Auto generate จากบรรทัด PR (ต้องมีสัญญา)"""
        self.ensure_one()
        if not self.contract_id:
            raise UserError(_(
                "สร้างรายละเอียดคุณลักษณะพัสดุได้เฉพาะใบขออนุมัติจัดซื้อที่มีสัญญาเท่านั้น"
            ))
        if not self.line_ids:
            raise UserError(_("ใบขออนุมัติจัดซื้อยังไม่มีรายการพัสดุ"))
        Spec = self.env["purchase.product.specification"]
        existing = Spec.search([
            ("request_id", "=", self.id),
            ("state", "=", "draft"),
        ], limit=1)
        if existing:
            existing.action_generate_from_pr()
            spec = existing
        else:
            spec = Spec.create({
                "request_id": self.id,
                "notes": _(
                    "<p>สร้างอัตโนมัติจากใบขออนุมัติจัดซื้อ %s "
                    "สัญญา %s</p>"
                ) % (self.name, self.contract_id.name),
            })
            spec.action_generate_from_pr()
        return {
            "type": "ir.actions.act_window",
            "name": "รายละเอียดคุณลักษณะพัสดุ",
            "res_model": "purchase.product.specification",
            "res_id": spec.id,
            "view_mode": "form",
            "target": "current",
        }


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    spec_scan_image = fields.Binary(
        string="รูปสแกนคุณลักษณะ",
        attachment=True,
        help="รูปภาพสแกนคุณลักษณะของรายการสินค้านี้",
    )
    spec_scan_filename = fields.Char(string="ชื่อไฟล์สแกน")
    spec_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="purchase_request_line_spec_attachment_rel",
        column1="line_id",
        column2="attachment_id",
        string="เอกสารแนบคุณลักษณะ",
        help="แนบเอกสารหรือรูปภาพคุณลักษณะ (Scan / PDF / รูป) แยกตามรายการสินค้าที่สั่งซื้อ",
    )
    spec_attachment_count = fields.Integer(
        string="จำนวนไฟล์คุณลักษณะ",
        compute="_compute_spec_attachment_count",
    )

    @api.depends("spec_attachment_ids", "spec_scan_image")
    def _compute_spec_attachment_count(self):
        for line in self:
            count = len(line.spec_attachment_ids)
            if line.spec_scan_image:
                count += 1
            line.spec_attachment_count = count

    def action_open_spec_attachments(self):
        """เปิด Viewer ไฟล์แนบคุณลักษณะภายในหน้าจอ Odoo"""
        self.ensure_one()
        attachments = self.spec_attachment_ids
        binary_atts = self.env["ir.attachment"].search([
            ("res_model", "=", "purchase.request.line"),
            ("res_id", "=", self.id),
            ("res_field", "=", "spec_scan_image"),
        ])
        attachments |= binary_atts
        if not attachments and not self.spec_scan_image:
            raise UserError(_("รายการนี้ยังไม่มีไฟล์แนบคุณลักษณะ"))
        return self.env["purchase.spec.attachment.viewer"].action_open_viewer(
            attachments,
            _("ไฟล์คุณลักษณะ — %s")
            % (self.product_id.display_name or self.name),
        )

    def action_open_spec_line_form(self):
        """เปิดฟอร์มรายการเพื่อดู/แนบไฟล์คุณลักษณะ"""
        self.ensure_one()
        view = self.env.ref(
            "vpk_product_specification.view_purchase_request_line_spec_popup",
            raise_if_not_found=False,
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("คุณลักษณะ / ไฟล์แนบ"),
            "res_model": "purchase.request.line",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(view.id, "form")] if view else [(False, "form")],
            "target": "new",
        }
