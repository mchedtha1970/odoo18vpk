# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import timedelta

from odoo import _, api, fields, models


class PurchaseFyHistoryMixin(models.AbstractModel):
    """Mixin: สรุปราคา/ปริมาณที่เคยซื้อในปีงบประมาณ (ต.ค.–ก.ย.)."""

    _name = "vpk.purchase.fy.history.mixin"
    _description = "Purchase Fiscal Year History Mixin"

    @api.model
    def _get_fiscal_period(self, ref_date=None):
        """ปีงบประมาณไทย: 1 ต.ค. → 30 ก.ย. (อ้างอิงแผนประจำปีถ้ามี)."""
        ref_date = fields.Date.to_date(ref_date or fields.Date.context_today(self))
        if ref_date.month >= 10:
            date_from = fields.Date.from_string(f"{ref_date.year}-10-01")
            date_to = fields.Date.from_string(f"{ref_date.year + 1}-09-30")
        else:
            date_from = fields.Date.from_string(f"{ref_date.year - 1}-10-01")
            date_to = fields.Date.from_string(f"{ref_date.year}-09-30")
        Plan = self.env.get("procurement.annual.plan")
        if Plan is not None:
            plan = Plan.search(
                [
                    ("state", "=", "approved"),
                    ("fiscal_year_start", "<=", ref_date),
                    ("fiscal_year_end", ">=", ref_date),
                ],
                limit=1,
                order="fiscal_year_start desc",
            )
            if plan and plan.fiscal_year_start and plan.fiscal_year_end:
                return plan.fiscal_year_start, plan.fiscal_year_end
        return date_from, date_to

    @api.model
    def _format_fiscal_period_label(self, date_from, date_to):
        def _be(d):
            return "%d/%d" % (d.month, d.year + 543)

        return _("ปีงบฯ %s – %s") % (_be(date_from), _be(date_to))

    @api.model
    def _get_fy_purchase_lines(
        self, product, partner=None, ref_date=None, exclude_order_ids=None
    ):
        if not product:
            return self.env["purchase.order.line"]
        date_from, date_to = self._get_fiscal_period(ref_date)
        date_to_exclusive = fields.Datetime.to_datetime(date_to + timedelta(days=1))
        domain = [
            ("product_id", "=", product.id),
            ("display_type", "=", False),
            ("order_id.state", "in", ("purchase", "done")),
            ("order_id.date_order", ">=", fields.Datetime.to_datetime(date_from)),
            ("order_id.date_order", "<", date_to_exclusive),
        ]
        if partner:
            domain.append(
                (
                    "order_id.partner_id",
                    "child_of",
                    partner.commercial_partner_id.id,
                )
            )
        if exclude_order_ids:
            domain.append(("order_id", "not in", list(exclude_order_ids)))
        return self.env["purchase.order.line"].search(
            domain, order="date_order desc, id desc"
        )

    @api.model
    def _compute_fy_purchase_stats(
        self, product, partner=None, ref_date=None, exclude_order_ids=None
    ):
        date_from, date_to = self._get_fiscal_period(ref_date)
        lines = self._get_fy_purchase_lines(
            product,
            partner=partner,
            ref_date=ref_date,
            exclude_order_ids=exclude_order_ids,
        )
        qty = sum(lines.mapped("product_qty"))
        amount = sum(lines.mapped("price_subtotal"))
        prices = [p for p in lines.mapped("price_unit") if p is not None]
        last_line = lines[:1]
        return {
            "date_from": date_from,
            "date_to": date_to,
            "label": self._format_fiscal_period_label(date_from, date_to),
            "qty": qty,
            "amount": amount,
            "count": len(lines),
            "last_price": last_line.price_unit if last_line else 0.0,
            "avg_price": (amount / qty) if qty else 0.0,
            "min_price": min(prices) if prices else 0.0,
            "max_price": max(prices) if prices else 0.0,
            "line_ids": lines.ids,
        }
