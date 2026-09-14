from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    vendor_trade_group = fields.Selection(
        selection=[
            ("regular", "ผู้ค้าปกติ"),
            ("unselected_bidder", "ผู้เสนอราคาที่ไม่ได้รับการคัดเลือก"),
        ],
        string="กลุ่มผู้ค้า",
        default="regular",
        tracking=True,
        index=True,
        help="แยกกลุ่มผู้ค้าปกติ และผู้เสนอราคาที่ไม่ได้รับการคัดเลือกจากการเปรียบเทียบราคา e-GP",
    )
    vendor_issue_ids = fields.One2many(
        comodel_name="vendor.product.issue",
        inverse_name="partner_id",
        string="สินค้าที่มีปัญหา",
    )
    vendor_issue_count = fields.Integer(
        compute="_compute_vendor_issue_stats",
        string="จำนวนปัญหา",
    )
    vendor_issue_open_count = fields.Integer(
        compute="_compute_vendor_issue_stats",
        string="ปัญหายังไม่ปิด",
    )
    purchase_order_total = fields.Monetary(
        compute="_compute_vendor_purchase_totals",
        string="มูลค่าซื้อสะสม",
        currency_field="currency_id",
    )
    vendor_bill_total = fields.Monetary(
        compute="_compute_vendor_purchase_totals",
        string="มูลค่าตั้งหนี้สะสม",
        currency_field="currency_id",
    )
    purchase_line_count = fields.Integer(
        compute="_compute_vendor_purchase_totals",
        string="รายการสินค้าที่เคยซื้อ",
    )

    def _get_vendor_trade_category(self, group):
        xmlid = {
            "regular": "vpk_vendor_history.partner_category_regular_vendor",
            "unselected_bidder": "vpk_vendor_history.partner_category_unselected_bidder",
        }.get(group)
        if not xmlid:
            return self.env["res.partner.category"]
        return self.env.ref(xmlid, raise_if_not_found=False) or self.env[
            "res.partner.category"
        ]

    def _sync_vendor_trade_category(self):
        """Sync partner tags ตามกลุ่มผู้ค้า"""
        cat_regular = self._get_vendor_trade_category("regular")
        cat_unselected = self._get_vendor_trade_category("unselected_bidder")
        trade_cats = cat_regular | cat_unselected
        for partner in self:
            commands = []
            for cat in trade_cats:
                if cat in partner.category_id:
                    commands.append((3, cat.id))
            target = (
                cat_regular
                if partner.vendor_trade_group == "regular"
                else cat_unselected
            )
            if target:
                commands.append((4, target.id))
            if commands:
                partner.with_context(skip_vendor_trade_sync=True).write(
                    {"category_id": commands}
                )

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners.filtered("supplier_rank")._sync_vendor_trade_category()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_vendor_trade_sync"):
            return res
        if "vendor_trade_group" in vals or "supplier_rank" in vals:
            self.filtered(
                lambda p: p.supplier_rank > 0 and not p.parent_id
            )._sync_vendor_trade_category()
        return res

    def _mark_as_unselected_bidder(self):
        """ตั้งเป็นผู้เสนอราคาที่ไม่ได้รับการคัดเลือก (ถ้ายังไม่เคยเป็นผู้ชนะ)"""
        Bid = (
            self.env["purchase.requisition.egp.bid"]
            if "purchase.requisition.egp.bid" in self.env
            else None
        )
        for partner in self:
            if Bid is not None:
                ever_won = Bid.search_count([
                    ("partner_id", "=", partner.id),
                    ("is_winner", "=", True),
                ])
                if ever_won:
                    continue
            if partner.vendor_trade_group != "unselected_bidder":
                partner.write({"vendor_trade_group": "unselected_bidder"})

    def _mark_as_regular_vendor(self):
        """ตั้งเป็นผู้ค้าปกติ (เช่น เมื่อได้รับคัดเลือกเป็นผู้ชนะ)"""
        for partner in self:
            if partner.vendor_trade_group != "regular":
                partner.write({"vendor_trade_group": "regular"})

    def _compute_vendor_issue_stats(self):
        Issue = self.env["vendor.product.issue"]
        for partner in self:
            issues = Issue.search([("partner_id", "child_of", partner.id)])
            partner.vendor_issue_count = len(issues)
            partner.vendor_issue_open_count = len(
                issues.filtered(lambda i: i.state in ("draft", "open", "in_progress"))
            )

    def _compute_vendor_purchase_totals(self):
        PO = self.env["purchase.order"]
        POL = self.env["purchase.order.line"]
        Move = self.env["account.move"]
        for partner in self:
            pos = PO.search([
                ("partner_id", "child_of", partner.id),
                ("state", "in", ("purchase", "done")),
            ])
            bills = Move.search([
                ("partner_id", "child_of", partner.id),
                ("move_type", "=", "in_invoice"),
                ("state", "=", "posted"),
            ])
            lines = POL.search([
                ("order_id.partner_id", "child_of", partner.id),
                ("order_id.state", "in", ("purchase", "done")),
                ("display_type", "=", False),
            ])
            partner.purchase_order_total = sum(pos.mapped("amount_total"))
            partner.vendor_bill_total = sum(bills.mapped("amount_total"))
            partner.purchase_line_count = len(lines)

    def action_view_vendor_issues(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "สินค้าที่มีปัญหา",
            "res_model": "vendor.product.issue",
            "view_mode": "list,form",
            "domain": [("partner_id", "child_of", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def action_view_vendor_purchase_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "ประวัติใบสั่งซื้อ",
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "child_of", self.id),
                ("state", "in", ("purchase", "done", "cancel")),
            ],
            "context": {"default_partner_id": self.id},
        }

    def action_view_vendor_purchase_lines(self):
        """เปิดประวัติการซื้อแบบรายสินค้า (per item) ของเจ้าหนี้นี้"""
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": "ประวัติซื้อรายสินค้า — %s" % self.display_name,
            "res_model": "purchase.order.line",
            "view_mode": "list,form",
            "domain": [
                ("order_id.partner_id", "child_of", self.id),
                ("order_id.state", "in", ("purchase", "done")),
                ("display_type", "=", False),
            ],
            "context": {
                "default_partner_id": self.id,
                "search_default_group_product": 1,
            },
        }
        list_view = self.env.ref(
            "vpk_vendor_history.view_purchase_order_line_vendor_history_list",
            raise_if_not_found=False,
        )
        search_view = self.env.ref(
            "vpk_vendor_history.view_purchase_order_line_vendor_history_search",
            raise_if_not_found=False,
        )
        if list_view:
            action["views"] = [(list_view.id, "list"), (False, "form")]
        if search_view:
            action["search_view_id"] = (search_view.id,)
        return action

    def action_view_vendor_bills(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "ประวัติใบแจ้งหนี้",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "child_of", self.id),
                ("move_type", "=", "in_invoice"),
            ],
            "context": {
                "default_partner_id": self.id,
                "default_move_type": "in_invoice",
            },
        }
