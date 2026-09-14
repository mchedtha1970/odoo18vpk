# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero

from .his_payment_method_map import is_advance_apply_code, is_advance_in_code


class HisPostingService(models.AbstractModel):
    _name = "vpk.his.posting.service"
    _description = "HIS Batch Posting Service"

    @api.model
    def _post_batch(self, batch):
        if batch.batch_type == "reversal":
            self._post_reversal(batch)
        elif batch.batch_type == "revenue":
            self._post_revenue(batch)
        elif batch.batch_type == "stock_issue":
            self._post_stock(batch)
        elif batch.batch_type == "stock_requisition":
            self._post_stock_requisition(batch)
        else:
            raise UserError(_("Unknown batch type %s") % batch.batch_type)
        batch.state = "posted"
        batch.message_post(body=_("Posted HIS batch %s") % batch.external_id)
        return True

    @api.model
    def _post_revenue(self, batch):
        invoices = self.env["account.move"]
        grouped = defaultdict(lambda: self.env["vpk.his.sale.line"])
        for line in batch.sale_line_ids:
            emap = line.entitlement_map_id
            if not emap:
                raise UserError(_("Sale line %s has no entitlement mapping") % line.id)
            grouped[
                (
                    emap.partner_id.id,
                    line.service_type,
                    emap.id,
                    line.ticket_external_id or "",
                )
            ] |= line

        for (_partner_id, _service, _emap_id, _ticket), lines in grouped.items():
            invoice = self._create_invoice(batch, lines)
            invoices |= invoice
            lines.write({"invoice_id": invoice.id})

        payments = self.env["account.payment"]
        for line in batch.payment_line_ids:
            pmap = line.payment_method_map_id
            method = (line.payment_method_code or "").strip().lower()
            if is_advance_in_code(method):
                self._create_advance_receipt(batch, line)
                continue
            if not pmap or not pmap.create_payment or pmap.is_entitlement:
                continue
            payment = self._create_payment(batch, line)
            payments |= payment
            line.payment_id = payment.id

        self._reconcile_payments(invoices, payments)
        batch.invoice_ids = invoices
        batch.payment_ids = payments

    @api.model
    def _get_sale_journal(self, company):
        Journal = self.env["account.journal"].sudo()
        journals = Journal.search(
            [("type", "=", "sale"), ("company_id", "=", company.id)]
        )
        valid = journals.filtered(
            lambda j: j.default_account_id and not j.default_account_id.deprecated
        )
        preferred = valid.filtered(lambda j: j.code == "HINV")
        if preferred:
            return preferred[0]
        if valid:
            return valid[0]
        if journals:
            return journals[0]
        raise UserError(_("No customer invoice journal found"))

    @api.model
    def _create_invoice(self, batch, lines):
        first = lines[0]
        emap = first.entitlement_map_id
        partner = emap.partner_id
        rec_acc = emap.receivable_account_id
        # Odoo only treats asset_receivable as AR (due date required).
        # VPK CoA classifies some payer AR as asset_current — still post there.
        if rec_acc and rec_acc.account_type == "asset_receivable":
            partner.sudo().with_company(batch.company_id).write(
                {"property_account_receivable_id": rec_acc.id}
            )
        invoice_lines = []
        item_labels = dict(
            self.env["vpk.his.sale.line"]._fields["item_type"].selection
        )
        for line in lines:
            amount = line.amount_total
            if float_is_zero(amount, precision_digits=2):
                amount = line.amount_untaxed
            name = _(
                "HIS %(date)s %(entitlement)s %(service)s %(item)s",
                date=batch.business_date,
                entitlement=line.entitlement_code,
                service=(line.service_type or "").upper(),
                item=item_labels.get(line.item_type, line.item_type),
            )
            if line.department_code:
                name = "%s [%s]" % (name, line.department_code)
            invoice_lines.append(
                Command.create(
                    {
                        "name": name,
                        "quantity": 1.0,
                        "price_unit": amount,
                        "tax_ids": [Command.clear()],
                        "account_id": line.income_account_id.id,
                    }
                )
            )
        tickets = ", ".join(
            dict.fromkeys(t for t in lines.mapped("ticket_external_id") if t)
        )
        origin = batch.name
        if tickets:
            origin = "%s / %s" % (batch.name, tickets)
        narration = _("HIS batch %s — entitlement %s (รอเคลียร์ลูกหนี้สิทธิ์)") % (
            batch.name,
            first.entitlement_code,
        )
        if tickets:
            narration = "%s\nPOS ticket: %s" % (narration, tickets)
        journal = self._get_sale_journal(batch.company_id)
        move = (
            self.env["account.move"]
            .sudo()
            .with_company(batch.company_id)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": partner.id,
                    "journal_id": journal.id,
                    "invoice_date": batch.business_date,
                    "invoice_date_due": batch.business_date,
                    "date": batch.business_date,
                    "invoice_origin": origin,
                    "payment_reference": batch.external_id,
                    "narration": narration,
                    "invoice_line_ids": invoice_lines,
                    "company_id": batch.company_id.id,
                    "currency_id": batch.currency_id.id,
                    "ref": tickets or batch.external_id,
                }
            )
        )
        if rec_acc:
            income_ids = set(lines.mapped("income_account_id").ids)
            counterparts = move.line_ids.filtered(
                lambda l: l.account_id.id not in income_ids
            )
            vals = {"account_id": rec_acc.id}
            if rec_acc.account_type != "asset_receivable":
                vals["date_maturity"] = False
            counterparts.write(vals)
        else:
            for aml in move.line_ids:
                if (
                    aml.account_id.account_type != "asset_receivable"
                    and aml.date_maturity
                ):
                    aml.date_maturity = False
        move.action_post()
        return move

    @api.model
    def _create_advance_receipt(self, batch, line):
        """Dr cash / Cr prepaid liability when HIS receives a deposit."""
        mixin = self.env["vpk.his.receipt.journal.mixin"]
        journal = line.journal_id or mixin._ensure_his_cash_journal(batch.company_id)
        cash_acc = journal.default_account_id
        inbound = journal.inbound_payment_method_line_ids.filtered(
            lambda l: l.payment_method_id.code == "manual"
        )[:1]
        if inbound and inbound.payment_account_id:
            cash_acc = inbound.payment_account_id
        if not cash_acc or cash_acc.deprecated:
            cash_acc = mixin._ensure_account(
                batch.company_id,
                "1101010101.101",
                "เงินสด",
                "asset_cash",
                reconcile=False,
            )
        liability = mixin._advance_liability_account(batch.company_id)
        partner = line.entitlement_map_id.partner_id if line.entitlement_map_id else False
        if not partner:
            partner = self.env.ref(
                "vpk_his_api.partner_payer_self_pay_op", raise_if_not_found=False
            )
        amount = line.amount
        label = _("HIS รับเงินล่วงหน้า %s %s") % (
            batch.external_id,
            line.ticket_external_id or line.line_external_id or "",
        )
        move = (
            self.env["account.move"]
            .sudo()
            .with_company(batch.company_id)
            .create(
                {
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": batch.business_date,
                    "ref": label,
                    "company_id": batch.company_id.id,
                    "currency_id": batch.currency_id.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": label,
                                "account_id": cash_acc.id,
                                "debit": amount,
                                "credit": 0.0,
                            }
                        ),
                        Command.create(
                            {
                                "name": label,
                                "account_id": liability.id,
                                "debit": 0.0,
                                "credit": amount,
                                "partner_id": partner.id if partner else False,
                            }
                        ),
                    ],
                }
            )
        )
        move.action_post()
        return move

    @api.model
    def _create_payment(self, batch, line):
        partner = line.entitlement_map_id.partner_id if line.entitlement_map_id else False
        if not partner and batch.sale_line_ids:
            partner = batch.sale_line_ids[0].entitlement_map_id.partner_id
        if not partner:
            partner = self.env.ref(
                "vpk_his_api.partner_payer_self_pay_op", raise_if_not_found=False
            )
        if not partner:
            raise UserError(
                _("Payment line %s has no payer partner") % (line.line_external_id or line.id)
            )
        journal = line.journal_id
        mixin = self.env["vpk.his.receipt.journal.mixin"]
        method = (line.payment_method_code or "").strip().lower()
        if is_advance_apply_code(method):
            journal = mixin._ensure_his_advance_journal(batch.company_id)
            line.journal_id = journal.id
        elif not journal or (
            journal.default_account_id and journal.default_account_id.deprecated
        ):
            journal = mixin._ensure_his_cash_journal(batch.company_id)
            line.journal_id = journal.id
        method_line = journal.inbound_payment_method_line_ids.filtered(
            lambda l: l.payment_method_id.code == "manual"
        )[:1]
        vals = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": partner.id,
            "amount": line.amount,
            "date": batch.business_date,
            "journal_id": journal.id,
            "memo": _("HIS %s %s")
            % (batch.external_id, line.payment_method_code),
            "company_id": batch.company_id.id,
            "currency_id": batch.currency_id.id,
        }
        if method_line:
            vals["payment_method_line_id"] = method_line.id
        payment = (
            self.env["account.payment"]
            .sudo()
            .with_company(batch.company_id)
            .create(vals)
        )
        payment.action_post()
        return payment

    @api.model
    def _reconcile_payments(self, invoices, payments):
        if not invoices or not payments:
            return
        by_partner = defaultdict(lambda: self.env["account.move"])
        for inv in invoices:
            by_partner[inv.partner_id.id] |= inv
        for payment in payments:
            moves = by_partner.get(payment.partner_id.id)
            if not moves:
                continue
            lines = (moves.line_ids + payment.move_id.line_ids).filtered(
                lambda l: l.account_id.account_type == "asset_receivable"
                and not l.reconciled
                and l.partner_id == payment.partner_id
            )
            if lines:
                lines.reconcile()

    @api.model
    def _post_stock(self, batch):
        consumption = self.env.ref(
            "vpk_his_api.stock_location_his_consumption", raise_if_not_found=False
        )
        if not consumption:
            consumption = self.env["stock.location"].search(
                [("name", "=", "HIS Consumption"), ("usage", "=", "inventory")],
                limit=1,
            )
        if not consumption:
            raise UserError(_("HIS Consumption location is missing"))

        pick_lines = batch.stock_line_ids.filtered(lambda l: l.reason != "expired")
        scrap_lines = batch.stock_line_ids.filtered(lambda l: l.reason == "expired")

        pickings = self.env["stock.picking"]
        grouped = defaultdict(lambda: self.env["vpk.his.stock.line"])
        for line in pick_lines:
            grouped[(line.warehouse_id.id, line.location_id.id)] |= line
        for (_wh, _loc), lines in grouped.items():
            picking = self._create_consumption_picking(batch, lines, consumption)
            pickings |= picking
            lines.write({"picking_id": picking.id})

        scraps = self.env["stock.scrap"]
        for line in scrap_lines:
            scrap = self._create_scrap(batch, line)
            scraps |= scrap
            line.scrap_id = scrap.id

        batch.picking_ids = pickings
        batch.scrap_ids = scraps

    @api.model
    def _post_stock_requisition(self, batch):
        lines = batch.requisition_line_ids
        if not lines:
            raise UserError(_("Stock requisition batch has no lines"))
        source_loc = batch.source_location_id
        dest_loc = batch.dest_location_id
        if not source_loc or not dest_loc:
            raise UserError(_("Source or destination location is missing"))
        source_wh = batch.source_warehouse_id
        picking_type = source_wh.int_type_id if source_wh else False
        if not picking_type:
            picking_type = self._get_his_internal_picking_type(source_wh, dest_loc)
        picking = self._create_requisition_picking(
            batch, lines, picking_type, source_loc, dest_loc
        )
        lines.write({"picking_id": picking.id})
        batch.picking_ids = picking

    @api.model
    def _get_his_internal_picking_type(self, warehouse, dest_location):
        PickingType = self.env["stock.picking.type"].sudo()
        existing = PickingType.search(
            [
                ("sequence_code", "=", "HISINT"),
                ("warehouse_id", "=", warehouse.id),
            ],
            limit=1,
        )
        if existing:
            return existing
        return PickingType.create(
            {
                "name": _("HIS Requisition"),
                "code": "internal",
                "sequence_code": "HISINT",
                "warehouse_id": warehouse.id,
                "default_location_src_id": warehouse.lot_stock_id.id,
                "default_location_dest_id": dest_location.id,
                "create_backorder": "never",
                "company_id": warehouse.company_id.id,
            }
        )

    @api.model
    def _create_requisition_picking(self, batch, lines, picking_type, source_loc, dest_loc):
        Move = self.env["stock.move"].sudo()
        picking = (
            self.env["stock.picking"]
            .sudo()
            .create(
                {
                    "picking_type_id": picking_type.id,
                    "location_id": source_loc.id,
                    "location_dest_id": dest_loc.id,
                    "origin": batch.name,
                    "scheduled_date": fields.Datetime.to_datetime(
                        "%s 00:00:00" % batch.business_date
                    ),
                    "company_id": batch.company_id.id,
                }
            )
        )
        line_moves = []
        grouped = defaultdict(lambda: self.env["vpk.his.requisition.line"])
        for line in lines:
            grouped[line.product_id.id] |= line
        for _product_id, product_lines in grouped.items():
            first = product_lines[0]
            vals = {
                "name": first.product_id.display_name,
                "product_id": first.product_id.id,
                "product_uom_qty": sum(product_lines.mapped("qty")),
                "product_uom": first.uom_id.id,
                "picking_id": picking.id,
                "location_id": source_loc.id,
                "location_dest_id": dest_loc.id,
                "company_id": batch.company_id.id,
                "origin": batch.name,
            }
            lots = product_lines.mapped("lot_id")
            if len(lots) == 1 and lots[:1] and "restrict_lot_id" in Move._fields:
                vals["restrict_lot_id"] = lots.id
            move = Move.create(vals)
            for line in product_lines:
                line_moves.append((line, move))
        self._validate_picking(picking, line_moves)
        return picking

    @api.model
    def _get_his_picking_type(self, warehouse, consumption):
        PickingType = self.env["stock.picking.type"].sudo()
        existing = PickingType.search(
            [
                ("sequence_code", "=", "HISOUT"),
                ("warehouse_id", "=", warehouse.id),
            ],
            limit=1,
        )
        if existing:
            return existing
        return PickingType.create(
            {
                "name": _("HIS Consumption"),
                "code": "outgoing",
                "sequence_code": "HISOUT",
                "warehouse_id": warehouse.id,
                "default_location_src_id": warehouse.lot_stock_id.id,
                "default_location_dest_id": consumption.id,
                "create_backorder": "never",
                "company_id": warehouse.company_id.id,
            }
        )

    @api.model
    def _create_consumption_picking(self, batch, lines, consumption):
        warehouse = lines[0].warehouse_id
        location = lines[0].location_id
        picking_type = self._get_his_picking_type(warehouse, consumption)
        Move = self.env["stock.move"].sudo()
        picking = (
            self.env["stock.picking"]
            .sudo()
            .create(
                {
                    "picking_type_id": picking_type.id,
                    "location_id": location.id,
                    "location_dest_id": consumption.id,
                    "origin": batch.name,
                    "scheduled_date": fields.Datetime.to_datetime(
                        "%s 00:00:00" % batch.business_date
                    ),
                    "company_id": batch.company_id.id,
                }
            )
        )
        line_moves = []
        grouped = defaultdict(lambda: self.env["vpk.his.stock.line"])
        for line in lines:
            grouped[line.product_id.id] |= line
        for _product_id, product_lines in grouped.items():
            first = product_lines[0]
            vals = {
                "name": first.product_id.display_name,
                "product_id": first.product_id.id,
                "product_uom_qty": sum(product_lines.mapped("qty")),
                "product_uom": first.uom_id.id,
                "picking_id": picking.id,
                "location_id": location.id,
                "location_dest_id": consumption.id,
                "company_id": batch.company_id.id,
                "origin": batch.name,
            }
            lots = product_lines.mapped("lot_id")
            if len(lots) == 1 and lots[:1] and "restrict_lot_id" in Move._fields:
                vals["restrict_lot_id"] = lots.id
            move = Move.create(vals)
            for line in product_lines:
                line_moves.append((line, move))
        self._validate_picking(picking, line_moves)
        return picking

    @api.model
    def _validate_picking(self, picking, line_moves):
        picking.action_confirm()
        picking.move_line_ids.unlink()
        self._assign_lots_fefo(picking, line_moves)
        if not picking.move_line_ids:
            picking.action_assign()
        for move in picking.move_ids:
            if move.move_line_ids:
                for ml in move.move_line_ids:
                    if float_is_zero(ml.quantity, precision_digits=4):
                        ml.quantity = ml.quantity_product_uom or move.product_uom_qty
                move.quantity = sum(move.move_line_ids.mapped("quantity"))
            else:
                move.quantity = move.product_uom_qty
            move.picked = True
        picking.with_context(
            skip_immediate=True, skip_backorder=True, skip_sms=True
        ).button_validate()

    @api.model
    def _assign_lots_fefo(self, picking, line_moves):
        """Assign the HIS lot on each move. If none was sent, pick FEFO lots."""
        Quant = self.env["stock.quant"].sudo()
        pairs = line_moves
        if line_moves and not isinstance(line_moves[0], tuple):
            pairs = [
                (
                    line,
                    picking.move_ids.filtered(
                        lambda m, product=line.product_id: m.product_id == product
                    )[:1],
                )
                for line in line_moves
            ]
        for line, move in pairs:
            if move and not move.exists():
                move = picking.move_ids.filtered(
                    lambda m, product=line.product_id: m.product_id == product
                )[:1]
            if not move:
                continue
            product = line.product_id
            if product.tracking == "none":
                continue
            if line.lot_id:
                self.env["stock.move.line"].sudo().create(
                    {
                        "move_id": move.id,
                        "product_id": product.id,
                        "product_uom_id": line.uom_id.id,
                        "quantity": line.qty,
                        "location_id": line.location_id.id,
                        "location_dest_id": picking.location_dest_id.id,
                        "lot_id": line.lot_id.id,
                        "picking_id": picking.id,
                        "company_id": picking.company_id.id,
                    }
                )
                continue
            domain = [
                ("product_id", "=", product.id),
                ("location_id", "child_of", line.location_id.id),
                ("quantity", ">", 0),
                ("lot_id", "!=", False),
            ]
            quants = Quant.search(domain)
            if "expiration_date" in self.env["stock.lot"]._fields:
                quants = quants.sorted(
                    lambda q: q.lot_id.expiration_date
                    or fields.Date.to_date("2099-12-31")
                )
            remaining = line.qty
            for quant in quants:
                if float_compare(remaining, 0.0, precision_digits=4) <= 0:
                    break
                take = min(remaining, quant.quantity)
                self.env["stock.move.line"].sudo().create(
                    {
                        "move_id": move.id,
                        "product_id": product.id,
                        "product_uom_id": line.uom_id.id,
                        "quantity": take,
                        "location_id": quant.location_id.id,
                        "location_dest_id": picking.location_dest_id.id,
                        "lot_id": quant.lot_id.id,
                        "picking_id": picking.id,
                        "company_id": picking.company_id.id,
                    }
                )
                remaining -= take

    @api.model
    def _create_scrap(self, batch, line):
        scrap_vals = {
            "product_id": line.product_id.id,
            "scrap_qty": line.qty,
            "product_uom_id": line.uom_id.id,
            "location_id": line.location_id.id,
            "lot_id": line.lot_id.id if line.lot_id else False,
            "origin": batch.name,
            "company_id": batch.company_id.id,
        }
        scrap = self.env["stock.scrap"].sudo().create(scrap_vals)
        scrap.action_validate()
        return scrap

    @api.model
    def _post_reversal(self, batch):
        original = batch.original_batch_id
        if not original:
            raise UserError(_("Reversal batch has no original batch"))
        new_invoices = self.env["account.move"]
        if original.invoice_ids:
            default_values_list = [
                {
                    "date": batch.business_date,
                    "invoice_date": batch.business_date,
                    "ref": _("Reversal of %s") % original.external_id,
                    "invoice_origin": batch.name,
                }
                for _move in original.invoice_ids
            ]
            new_invoices = original.invoice_ids.sudo()._reverse_moves(
                default_values_list=default_values_list, cancel=False
            )
            to_post = new_invoices.filtered(lambda m: m.state == "draft")
            if to_post:
                to_post.action_post()
        new_payments = self.env["account.payment"]
        for payment in original.payment_ids:
            if payment.state == "posted":
                try:
                    payment.sudo().action_draft()
                    payment.sudo().action_cancel()
                except UserError:
                    if payment.move_id:
                        reversed_moves = payment.move_id.sudo()._reverse_moves(
                            default_values_list=[
                                {
                                    "date": batch.business_date,
                                    "ref": _("Reversal of %s") % original.external_id,
                                }
                            ],
                            cancel=False,
                        )
                        reversed_moves.filtered(lambda m: m.state == "draft").action_post()
        new_pickings = self.env["stock.picking"]
        Return = self.env["stock.return.picking"].sudo()
        for picking in original.picking_ids.filtered(lambda p: p.state == "done"):
            wizard = Return.with_context(
                active_id=picking.id,
                active_ids=picking.ids,
                active_model="stock.picking",
            ).create({"picking_id": picking.id})
            action = wizard.action_create_returns_all()
            returned = self.env["stock.picking"]
            if isinstance(action, dict) and action.get("res_id"):
                returned = self.env["stock.picking"].browse(action["res_id"])
            if returned:
                original_lines = original.stock_line_ids
                if original.batch_type == "stock_requisition":
                    original_lines = original.requisition_line_ids
                self._validate_picking(returned, original_lines)
                new_pickings |= returned
        batch.invoice_ids = new_invoices
        batch.payment_ids = new_payments
        batch.picking_ids = new_pickings
