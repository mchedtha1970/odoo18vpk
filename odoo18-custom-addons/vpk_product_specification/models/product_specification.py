from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseProductSpecification(models.Model):
    _name = "purchase.product.specification"
    _description = "รายละเอียดคุณลักษณะพัสดุ"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่เอกสาร",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    date = fields.Date(
        string="วันที่",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขออนุมัติจัดซื้อ",
        required=True,
        tracking=True,
        index=True,
        domain="[('contract_id', '!=', False)]",
        help="เลือกได้เฉพาะใบขอซื้อ/จ้าง/เช่าที่มีสัญญา",
    )
    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="สัญญา",
        related="request_id.contract_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        related="contract_id.partner_id",
        string="คู่สัญญา",
        store=True,
    )
    department_id = fields.Many2one(
        related="request_id.department_id",
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("confirmed", "ยืนยัน"),
            ("cancelled", "ยกเลิก"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="purchase.product.specification.line",
        inverse_name="specification_id",
        string="รายการคุณลักษณะพัสดุ",
        copy=True,
    )
    line_count = fields.Integer(compute="_compute_line_count")
    notes = fields.Html(string="หมายเหตุ")
    auto_generated = fields.Boolean(
        string="สร้างอัตโนมัติจาก PR",
        readonly=True,
        copy=False,
    )

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "purchase.product.specification"
                    )
                    or _("New")
                )
        return super().create(vals_list)

    @api.onchange("request_id")
    def _onchange_request_id(self):
        if self.request_id and not self.request_id.contract_id:
            raise UserError(_(
                "ใบขออนุมัติจัดซื้อนี้ไม่มีสัญญา — "
                "ระบบสร้างรายละเอียดคุณลักษณะพัสดุได้เฉพาะใบที่มีสัญญาเท่านั้น"
            ))
        if self.request_id:
            self._generate_lines_from_request()

    def action_generate_from_pr(self):
        """Auto generate รายการพัสดุจากบรรทัดใบขออนุมัติจัดซื้อ"""
        for rec in self:
            if not rec.request_id:
                raise UserError(_("กรุณาเลือกใบขออนุมัติจัดซื้อ"))
            if not rec.request_id.contract_id:
                raise UserError(_(
                    "ใบขออนุมัติจัดซื้อนี้ไม่มีสัญญา — "
                    "สร้างรายละเอียดคุณลักษณะได้เฉพาะใบที่มีสัญญา"
                ))
            if not rec.request_id.line_ids:
                raise UserError(_("ใบขออนุมัติจัดซื้อไม่มีรายการพัสดุ"))
            rec._generate_lines_from_request()
            rec.auto_generated = True
            rec.message_post(
                body=_("Auto generate รายการคุณลักษณะจาก %s (%s รายการ)")
                % (rec.request_id.name, len(rec.line_ids)),
                message_type="notification",
            )
        return True

    def _generate_lines_from_request(self):
        self.ensure_one()
        pr = self.request_id
        commands = [(5, 0, 0)]
        seq = 10
        for pr_line in pr.line_ids.filtered(lambda l: not l.cancelled):
            product = pr_line.product_id
            specs = (pr_line.specifications or "").strip() if hasattr(pr_line, "specifications") else ""
            if not specs and product:
                specs = (
                    (product.description_purchase or "").strip()
                    or (product.description or "").strip()
                    or (product.product_tmpl_id.description_purchase or "").strip()
                    or ""
                )
            if not specs:
                specs = _(
                    "คุณลักษณะตามรายละเอียดในใบขอซื้อเลขที่ %s รายการ: %s"
                ) % (pr.name, pr_line.name or (product.display_name if product else "-"))
            # คัดลอกไฟล์แนบ/สแกนจากบรรทัด PR (สร้าง attachment ใหม่ผูกกับบรรทัด SPEC)
            attach_commands = []
            for att in pr_line.spec_attachment_ids:
                new_att = att.copy({
                    "res_model": "purchase.product.specification.line",
                    "res_id": 0,
                })
                attach_commands.append((4, new_att.id))
            scan_image = pr_line.spec_scan_image
            scan_filename = pr_line.spec_scan_filename
            commands.append((0, 0, {
                "sequence": seq,
                "request_line_id": pr_line.id,
                "product_id": product.id if product else False,
                "name": pr_line.name or (product.display_name if product else _("รายการพัสดุ")),
                "product_qty": pr_line.product_qty,
                "uom_id": pr_line.product_uom_id.id if pr_line.product_uom_id else False,
                "estimated_cost": pr_line.estimated_cost,
                "specifications": specs,
                "spec_attachment_ids": attach_commands,
                "spec_scan_image": scan_image,
                "spec_scan_filename": scan_filename,
            }))
            seq += 10
        self.line_ids = commands
        # ผูก res_id ของไฟล์แนบที่คัดลอกให้ตรงกับบรรทัด SPEC ที่เพิ่งสร้าง
        for line in self.line_ids:
            if line.spec_attachment_ids:
                line.spec_attachment_ids.write({
                    "res_model": "purchase.product.specification.line",
                    "res_id": line.id,
                })

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("ยังไม่มีรายการคุณลักษณะพัสดุ — กด Auto Generate ก่อน"))
            if not rec.contract_id:
                raise UserError(_("เอกสารนี้ต้องอ้างอิงใบขอซื้อที่มีสัญญา"))
            rec.state = "confirmed"
        return True

    def action_draft(self):
        self.write({"state": "draft"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_product_specification.action_report_product_specification"
        ).report_action(self)


class PurchaseProductSpecificationLine(models.Model):
    _name = "purchase.product.specification.line"
    _description = "รายการคุณลักษณะพัสดุ"
    _order = "sequence, id"

    specification_id = fields.Many2one(
        comodel_name="purchase.product.specification",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    request_line_id = fields.Many2one(
        comodel_name="purchase.request.line",
        string="บรรทัดใบขอซื้อ",
        ondelete="set null",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="พัสดุ/สินค้า",
    )
    name = fields.Char(string="รายการ", required=True)
    product_qty = fields.Float(
        string="จำนวน",
        digits="Product Unit of Measure",
        default=1.0,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วย",
    )
    estimated_cost = fields.Float(string="วงเงินโดยประมาณ")
    specifications = fields.Text(
        string="รายละเอียดคุณลักษณะ",
        required=True,
    )
    spec_scan_image = fields.Binary(
        string="รูปสแกนคุณลักษณะ",
        attachment=True,
        help="รูปภาพสแกนคุณลักษณะของรายการนี้",
    )
    spec_scan_filename = fields.Char(string="ชื่อไฟล์สแกน")
    spec_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="purchase_spec_line_attachment_rel",
        column1="line_id",
        column2="attachment_id",
        string="เอกสารแนบคุณลักษณะ",
        help="แนบไฟล์เอกสารหรือรูปภาพคุณลักษณะ (Scan / PDF / รูป) แยกตามรายการสินค้า",
    )
    attachment_count = fields.Integer(
        string="จำนวนไฟล์แนบ",
        compute="_compute_attachment_count",
    )
    company_id = fields.Many2one(
        related="specification_id.company_id",
        store=True,
    )

    @api.depends("spec_attachment_ids", "spec_scan_image")
    def _compute_attachment_count(self):
        for line in self:
            count = len(line.spec_attachment_ids)
            if line.spec_scan_image:
                count += 1
            line.attachment_count = count

    def action_open_spec_attachments(self):
        self.ensure_one()
        attachments = self.spec_attachment_ids
        binary_atts = self.env["ir.attachment"].search([
            ("res_model", "=", "purchase.product.specification.line"),
            ("res_id", "=", self.id),
            ("res_field", "=", "spec_scan_image"),
        ])
        attachments |= binary_atts
        if not attachments and not self.spec_scan_image:
            raise UserError(_("รายการนี้ยังไม่มีไฟล์แนบคุณลักษณะ"))
        return self.env["purchase.spec.attachment.viewer"].action_open_viewer(
            attachments,
            _("ไฟล์คุณลักษณะ — %s") % (self.name or ""),
        )

    def action_open_line_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการคุณลักษณะ / ไฟล์แนบ"),
            "res_model": "purchase.product.specification.line",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
