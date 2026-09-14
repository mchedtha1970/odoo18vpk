# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging
import traceback
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

from .his_stock_line import ITEM_TYPE_ALIASES

_logger = logging.getLogger(__name__)

STOCK_PII_KEEP = {
    "hn",
    "vn",
    "patient_hn",
    "visit_id",
    "visit_no",
    "visit_number",
}

PII_KEYS = {
    "hn",
    "an",
    "vn",
    "cid",
    "pid",
    "patient_id",
    "patient_name",
    "patient_hn",
    "national_id",
    "visit_id",
    "encounter_id",
    "firstname",
    "lastname",
    "birthdate",
    "dob",
}


class HisApiService(models.AbstractModel):
    _name = "vpk.his.api.service"
    _description = "HIS Inbound API Service"

    @api.model
    def ingest_revenue(self, payload, request_meta=None):
        return self._ingest(payload, "revenue", request_meta=request_meta)

    @api.model
    def ingest_stock_issues(self, payload, request_meta=None):
        return self._ingest(payload, "stock_issue", request_meta=request_meta)

    @api.model
    def ingest_stock_requisitions(self, payload, request_meta=None):
        return self._ingest(payload, "stock_requisition", request_meta=request_meta)

    @api.model
    def get_batch(self, external_id, source_system=None):
        domain = [("external_id", "=", external_id)]
        if source_system:
            domain.append(("source_system", "=", source_system))
        batches = self.env["vpk.his.batch"].sudo().search(domain, order="id desc")
        if not batches:
            raise UserError(_("Batch not found"))
        if len(batches) > 1 and not source_system:
            raise UserError(
                _("Multiple batches share this external_id; pass source_system")
            )
        return batches[0].to_api_dict()

    @api.model
    def list_entitlements(self):
        maps = self.env["vpk.his.entitlement.map"].sudo().search(
            [("active", "=", True), ("company_id", "=", self.env.company.id)]
        )
        return {
            "ok": True,
            "entitlements": [
                {
                    "code": rec.code,
                    "name": rec.name,
                    "service_type": rec.service_type,
                    "item_type": rec.item_type,
                    "create_payment": rec.create_payment,
                    "parks_receivable": rec.code != "SELF_PAY"
                    or rec.service_type == "ip",
                }
                for rec in maps
            ],
        }

    @api.model
    def list_payment_methods(self):
        maps = self.env["vpk.his.payment.method.map"].sudo().search(
            [("active", "=", True), ("company_id", "=", self.env.company.id)]
        )
        return {
            "ok": True,
            "payment_methods": [
                {
                    "code": rec.code,
                    "name": rec.name,
                    "is_entitlement": rec.is_entitlement,
                    "create_payment": rec.create_payment,
                    "applies_advance": rec.code == "advance",
                    "receives_advance": rec.code == "advance_in",
                }
                for rec in maps
            ],
        }

    @api.model
    def list_warehouses(self):
        warehouses = self.env["stock.warehouse"].sudo().search(
            [("company_id", "=", self.env.company.id)]
        )
        unit_maps = self.env["vpk.his.unit.map"].sudo().search(
            [("active", "=", True), ("company_id", "=", self.env.company.id)]
        )
        return {
            "ok": True,
            "warehouses": [
                {
                    "code": wh.code,
                    "name": wh.name,
                    "stock_location": wh.lot_stock_id.complete_name,
                }
                for wh in warehouses
            ],
            "units": [
                {
                    "his_code": rec.his_code,
                    "name": rec.name,
                    "warehouse_code": rec.warehouse_id.code,
                    "location": rec.location_id.complete_name
                    if rec.location_id
                    else False,
                }
                for rec in unit_maps
            ],
        }

    @api.model
    def list_products(self, codes=None, tracking=None, limit=50):
        Product = self.env["product.product"].sudo()
        domain = [("is_storable", "=", True)]
        codes = [c for c in (codes or []) if c]
        if codes:
            wanted = set()
            for code in codes:
                code = str(code).strip()
                wanted.add(code)
                if code.isdigit():
                    wanted.add(code.zfill(5))
            domain.append(("default_code", "in", list(wanted)))
        if tracking in ("lot", "serial", "none"):
            domain.append(("tracking", "=", tracking))
        try:
            limit = min(max(int(limit or 50), 1), 200)
        except (TypeError, ValueError):
            limit = 50
        products = Product.search(domain, limit=limit, order="default_code, id")
        return {
            "ok": True,
            "products": [
                {
                    "code": rec.default_code,
                    "name": rec.name,
                    "uom": rec.uom_id.name,
                    "tracking": rec.tracking,
                    "lot_required": rec.tracking in ("lot", "serial"),
                }
                for rec in products
                if rec.default_code
            ],
        }

    @api.model
    def _ingest(self, payload, default_type, request_meta=None):
        request_meta = request_meta or {}
        payload = self._strip_pii(
            payload if isinstance(payload, dict) else {},
            keep=STOCK_PII_KEEP if default_type == "stock_issue" else None,
        )
        Log = self.env["vpk.his.api.log"].sudo()
        log = Log.create(
            {
                "endpoint": request_meta.get("endpoint") or "",
                "http_method": request_meta.get("method") or "POST",
                "remote_addr": request_meta.get("remote_addr"),
                "request_body": self._safe_json_dump(payload),
                "state": "pending",
                "external_id": self._clean_str(payload.get("external_id")),
                "source_system": self._clean_str(payload.get("source_system")),
            }
        )
        try:
            result = self._ingest_payload(payload, default_type)
            log.write(
                {
                    "state": "success",
                    "action": result.get("action"),
                    "batch_id": result.get("batch_id"),
                    "external_id": result.get("external_id"),
                    "source_system": result.get("source_system"),
                    "response_body": self._safe_json_dump(result),
                    "http_status": result.get("http_status", 202),
                }
            )
            return result
        except (UserError, ValidationError) as err:
            log.write(
                {
                    "state": "error",
                    "action": "error",
                    "error_message": str(err),
                    "response_body": self._safe_json_dump(
                        {"ok": False, "error": str(err)}
                    ),
                    "http_status": 400,
                }
            )
            raise
        except Exception as err:  # noqa: BLE001
            _logger.exception("HIS API ingest failed")
            log.write(
                {
                    "state": "error",
                    "action": "error",
                    "error_message": str(err),
                    "response_body": traceback.format_exc()[-4000:],
                    "http_status": 500,
                }
            )
            raise UserError(_("HIS API internal error: %s") % err) from err

    @api.model
    def _ingest_payload(self, payload, default_type):
        if not isinstance(payload, dict):
            raise UserError(_("Request body must be a JSON object"))
        external_id = self._clean_str(payload.get("external_id"))
        source_system = self._clean_str(payload.get("source_system"))
        if not external_id:
            raise UserError(_("external_id is required"))
        if not source_system:
            raise UserError(_("source_system is required"))
        business_date = self._parse_date(payload.get("business_date"))
        if not business_date:
            raise UserError(_("business_date is required (YYYY-MM-DD)"))

        batch_type = self._clean_str(payload.get("batch_type")) or default_type
        if payload.get("original_external_id") and batch_type != "reversal":
            batch_type = "reversal"
        if batch_type not in ("revenue", "stock_issue", "stock_requisition", "reversal"):
            raise UserError(_("Invalid batch_type"))
        if batch_type == "revenue" and default_type == "stock_issue":
            # stock endpoint must stay stock unless explicit reversal
            if not payload.get("original_external_id"):
                batch_type = "stock_issue"
        if batch_type == "stock_requisition" and default_type == "stock_issue":
            if not payload.get("original_external_id"):
                batch_type = "stock_issue"
        if default_type == "stock_requisition" and batch_type not in (
            "stock_requisition",
            "reversal",
        ):
            if not payload.get("original_external_id"):
                batch_type = "stock_requisition"

        Batch = self.env["vpk.his.batch"].sudo()
        existing = Batch.search(
            [
                ("external_id", "=", external_id),
                ("source_system", "=", source_system),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        if existing and existing.state == "posted":
            result = existing.to_api_dict()
            result["action"] = "unchanged"
            result["http_status"] = 200
            return result
        if existing and existing.state == "cancelled":
            raise UserError(
                _("Batch %s is cancelled; use a new external_id") % external_id
            )

        currency = self._resolve_currency(payload.get("currency"))
        control = payload.get("control_totals") or {}
        vals = {
            "external_id": external_id,
            "source_system": source_system,
            "batch_type": batch_type,
            "business_date": business_date,
            "shift": self._clean_str(payload.get("shift")) or False,
            "currency_id": currency.id,
            "original_external_id": self._clean_str(payload.get("original_external_id"))
            or False,
            "control_sales_total": self._to_float(control.get("sales_total")),
            "control_payments_total": self._to_float(control.get("payments_total")),
            "control_qty_total": self._to_float(
                control.get("qty_total") if "qty_total" in control else None
            ),
            "state": "draft",
        }

        if existing:
            existing.sale_line_ids.unlink()
            existing.payment_line_ids.unlink()
            existing.stock_line_ids.unlink()
            existing.requisition_line_ids.unlink()
            existing.write(vals)
            batch = existing
            action = "updated"
        else:
            batch = Batch.create(vals)
            action = "created"

        if batch_type in ("revenue", "reversal") and default_type == "revenue":
            self._create_sale_lines(batch, payload.get("sales") or [])
            self._create_payment_lines(batch, payload.get("payments") or [])
        if batch_type in ("stock_issue", "reversal") and default_type == "stock_issue":
            issues = payload.get("issues")
            if issues is None:
                issues = payload.get("items")
            self._create_stock_lines(batch, issues or [])
        if batch_type in ("stock_requisition", "reversal") and default_type == "stock_requisition":
            self._apply_requisition_routing(batch, payload)
            if batch_type == "stock_requisition":
                lines = payload.get("lines")
                if lines is None:
                    lines = payload.get("items")
                if lines is None:
                    lines = payload.get("requisitions")
                self._create_requisition_lines(batch, lines or [])

        batch._validate_batch()
        result = batch.to_api_dict()
        result["action"] = action
        result["http_status"] = 202
        return result

    @api.model
    def _create_sale_lines(self, batch, sales):
        if not isinstance(sales, list):
            raise UserError(_("sales must be a list"))
        Line = self.env["vpk.his.sale.line"].sudo()
        for item in sales:
            if not isinstance(item, dict):
                raise UserError(_("Each sales line must be an object"))
            entitlement = self._clean_str(item.get("entitlement_code"))
            if not entitlement:
                raise UserError(_("sales[].entitlement_code is required"))
            amount_total = self._to_float(item.get("amount_total"))
            amount_tax = self._to_float(item.get("amount_tax"))
            amount_untaxed = self._to_float(item.get("amount_untaxed"))
            if float_is_zero(amount_untaxed, precision_digits=4):
                amount_untaxed = amount_total - amount_tax
            service_type = (self._clean_str(item.get("service_type")) or "op").lower()
            if service_type not in ("op", "ip"):
                raise UserError(_("sales[].service_type must be op or ip"))
            item_type = self._clean_str(item.get("item_type")) or "service"
            if item_type == "all":
                item_type = "service"
            Line.create(
                {
                    "batch_id": batch.id,
                    "line_external_id": self._clean_str(item.get("line_external_id"))
                    or False,
                    "entitlement_code": entitlement,
                    "service_type": service_type,
                    "item_type": item_type,
                    "department_code": self._clean_str(item.get("department_code"))
                    or False,
                    "ticket_external_id": self._clean_str(
                        item.get("ticket_external_id")
                    )
                    or False,
                    "qty": self._to_float(item.get("qty")) or 1.0,
                    "amount_untaxed": amount_untaxed,
                    "amount_tax": amount_tax,
                    "amount_total": amount_total,
                    "income_account_code": self._clean_str(
                        item.get("income_account_code")
                    )
                    or False,
                }
            )

    @api.model
    def _create_payment_lines(self, batch, payments):
        if not isinstance(payments, list):
            raise UserError(_("payments must be a list"))
        Line = self.env["vpk.his.payment.line"].sudo()
        for item in payments:
            if not isinstance(item, dict):
                raise UserError(_("Each payment line must be an object"))
            method = self._clean_str(item.get("payment_method_code"))
            if not method:
                raise UserError(_("payments[].payment_method_code is required"))
            service_type = (self._clean_str(item.get("service_type")) or "").lower()
            if service_type and service_type not in ("op", "ip"):
                raise UserError(_("payments[].service_type must be op or ip"))
            Line.create(
                {
                    "batch_id": batch.id,
                    "line_external_id": self._clean_str(item.get("line_external_id"))
                    or False,
                    "payment_method_code": method,
                    "entitlement_code": self._clean_str(item.get("entitlement_code"))
                    or False,
                    "ticket_external_id": self._clean_str(
                        item.get("ticket_external_id")
                    )
                    or False,
                    "service_type": service_type or False,
                    "amount": self._to_float(item.get("amount")),
                    "journal_code": self._clean_str(item.get("journal_code")) or False,
                }
            )

    @api.model
    def _create_stock_lines(self, batch, issues):
        if not isinstance(issues, list):
            raise UserError(_("issues must be a list"))
        Line = self.env["vpk.his.stock.line"].sudo()
        for item in issues:
            if not isinstance(item, dict):
                raise UserError(_("Each issue line must be an object"))
            for row in self._expand_issue_lots(item):
                product_code = self._clean_str(row.get("product_code"))
                if not product_code:
                    raise UserError(_("issues[].product_code is required"))
                reason = self._clean_str(row.get("reason")) or "patient_use"
                if reason not in ("patient_use", "ward_use", "expired", "adjust"):
                    raise UserError(_("Invalid issues[].reason"))
                item_type = self._normalize_stock_item_type(row.get("item_type"))
                Line.create(
                    {
                        "batch_id": batch.id,
                        "line_external_id": self._clean_str(row.get("line_external_id"))
                        or False,
                        "product_code": product_code,
                        "item_type": item_type,
                        "warehouse_code": self._clean_str(row.get("warehouse_code"))
                        or False,
                        "location_code": self._clean_str(row.get("location_code"))
                        or False,
                        "department_code": self._clean_str(row.get("department_code"))
                        or False,
                        "uom": self._clean_str(row.get("uom")) or False,
                        "qty": self._to_float(row.get("qty")),
                        "lot_name": self._clean_str(
                            row.get("lot_name") or row.get("lot")
                        )
                        or False,
                        "hn": self._stock_hn(row),
                        "vn": self._stock_vn(row),
                        "reason": reason,
                    }
                )

    @api.model
    def _apply_requisition_routing(self, batch, payload):
        Warehouse = self.env["stock.warehouse"].sudo()
        Location = self.env["stock.location"].sudo()
        batch.department_code = self._clean_str(payload.get("department_code")) or False
        batch.source_warehouse_code = (
            self._clean_str(payload.get("source_warehouse_code")) or False
        )
        batch.dest_warehouse_code = (
            self._clean_str(payload.get("dest_warehouse_code")) or False
        )
        batch.dest_location_code = (
            self._clean_str(payload.get("dest_location_code")) or False
        )

        source_wh = False
        if batch.source_warehouse_code:
            source_wh = Warehouse.search(
                [("code", "=ilike", batch.source_warehouse_code.strip())], limit=1
            )
        dest_wh = False
        if batch.dest_warehouse_code:
            dest_wh = Warehouse.search(
                [("code", "=ilike", batch.dest_warehouse_code.strip())], limit=1
            )
        dest_loc = False
        if batch.department_code and not dest_wh:
            unit_map = self.env["vpk.his.unit_map"].find_map(batch.department_code)
            if unit_map:
                dest_wh = unit_map.warehouse_id
                dest_loc = unit_map.location_id
        if not source_wh:
            source_wh = Warehouse.search([("code", "=", "PHAR")], limit=1)
        if not source_wh:
            source_wh = Warehouse.search(
                [("company_id", "=", batch.company_id.id)], limit=1
            )
        if not dest_wh:
            dest_wh = Warehouse.search([("code", "=", "UNIT")], limit=1)
        batch.source_warehouse_id = source_wh.id if source_wh else False
        batch.dest_warehouse_id = dest_wh.id if dest_wh else False
        if not batch.source_warehouse_code and source_wh:
            batch.source_warehouse_code = source_wh.code
        if not batch.dest_warehouse_code and dest_wh:
            batch.dest_warehouse_code = dest_wh.code

        if batch.dest_location_code and dest_wh:
            loc_domain = [
                ("usage", "=", "internal"),
                "|",
                ("complete_name", "ilike", batch.dest_location_code),
                ("name", "ilike", batch.dest_location_code),
            ]
            if dest_wh.view_location_id:
                loc_domain = [
                    ("usage", "=", "internal"),
                    ("id", "child_of", dest_wh.view_location_id.id),
                    "|",
                    ("complete_name", "ilike", batch.dest_location_code),
                    ("name", "ilike", batch.dest_location_code),
                ]
            found = Location.search(loc_domain, limit=1)
            if found:
                dest_loc = found
        if not dest_loc and dest_wh:
            dest_loc = dest_wh.lot_stock_id
        source_loc = source_wh.lot_stock_id if source_wh else False
        batch.source_location_id = source_loc.id if source_loc else False
        batch.dest_location_id = dest_loc.id if dest_loc else False

    @api.model
    def _create_requisition_lines(self, batch, lines):
        if not isinstance(lines, list):
            raise UserError(_("lines must be a list"))
        Line = self.env["vpk.his.requisition.line"].sudo()
        for item in lines:
            if not isinstance(item, dict):
                raise UserError(_("Each requisition line must be an object"))
            for row in self._expand_issue_lots(item):
                product_code = self._clean_str(row.get("product_code"))
                if not product_code:
                    raise UserError(_("lines[].product_code is required"))
                item_type = self._normalize_stock_item_type(row.get("item_type"))
                Line.create(
                    {
                        "batch_id": batch.id,
                        "line_external_id": self._clean_str(row.get("line_external_id"))
                        or False,
                        "product_code": product_code,
                        "item_type": item_type,
                        "uom": self._clean_str(row.get("uom")) or False,
                        "qty": self._to_float(row.get("qty")),
                        "lot_name": self._clean_str(
                            row.get("lot_name") or row.get("lot")
                        )
                        or False,
                    }
                )

    @api.model
    def _normalize_stock_item_type(self, value):
        if value in (None, False, ""):
            return False
        raw = str(value).strip()
        mapped = ITEM_TYPE_ALIASES.get(raw) or ITEM_TYPE_ALIASES.get(raw.lower())
        if not mapped:
            raise UserError(
                _("issues[].item_type must be drug, medical_supply, or other")
            )
        return mapped

    @api.model
    def _expand_issue_lots(self, item):
        lots = item.get("lots")
        if lots is None:
            return [item]
        if not isinstance(lots, list):
            raise UserError(_("issues[].lots must be a list"))
        if not lots:
            return [item]
        if item.get("lot_name") or item.get("lot"):
            raise UserError(_("Send either lot_name or lots[], not both"))
        parent_qty = None
        if "qty" in item and item.get("qty") not in (None, False, ""):
            parent_qty = self._to_float(item.get("qty"))
        parent_id = self._clean_str(item.get("line_external_id")) or ""
        expanded = []
        total = 0.0
        for lot in lots:
            if not isinstance(lot, dict):
                raise UserError(_("Each lots[] entry must be an object"))
            lot_name = self._clean_str(
                lot.get("lot_name") or lot.get("lot") or lot.get("name")
            )
            if not lot_name:
                raise UserError(_("lots[].lot_name is required"))
            qty = self._to_float(lot.get("qty") if "qty" in lot else lot.get("quantity"))
            row = dict(item)
            row.pop("lots", None)
            row["lot_name"] = lot_name
            row["qty"] = qty
            row["line_external_id"] = (
                self._clean_str(lot.get("line_external_id"))
                or ("%s-%s" % (parent_id, lot_name) if parent_id else False)
            )
            expanded.append(row)
            total += qty
        if parent_qty is not None and float_compare(
            parent_qty, total, precision_digits=4
        ):
            raise UserError(
                _("issues[].qty %(qty)s does not match sum of lots %(lots)s")
                % {"qty": parent_qty, "lots": total}
            )
        return expanded

    @api.model
    def _parse_date(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value.date()
        text = str(value).strip()[:10]
        try:
            return fields.Date.from_string(text)
        except (ValueError, TypeError) as err:
            raise UserError(_("Invalid business_date")) from err

    @api.model
    def _resolve_currency(self, code):
        code = self._clean_str(code) or "THB"
        currency = self.env["res.currency"].sudo().search(
            [("name", "=", code.upper())], limit=1
        )
        return currency or self.env.company.currency_id

    @api.model
    def _to_float(self, value):
        if value in (None, False, ""):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError) as err:
            raise UserError(_("Invalid number: %s") % value) from err

    @api.model
    def _clean_str(self, value):
        if value is None or value is False:
            return False
        text = str(value).strip()
        return text or False

    @api.model
    def _stock_hn(self, row):
        return self._clean_str(
            row.get("hn") or row.get("HN") or row.get("patient_hn")
        )

    @api.model
    def _stock_vn(self, row):
        return self._clean_str(
            row.get("vn")
            or row.get("VN")
            or row.get("visit_id")
            or row.get("visit_no")
            or row.get("visit_number")
        )

    @api.model
    def _strip_pii(self, data, keep=None):
        keep = {str(k).lower() for k in (keep or set())}
        if isinstance(data, list):
            return [self._strip_pii(x, keep=keep) for x in data]
        if not isinstance(data, dict):
            return data
        cleaned = {}
        for key, val in data.items():
            if key.lower() in PII_KEYS and key.lower() not in keep:
                continue
            cleaned[key] = self._strip_pii(val, keep=keep)
        return cleaned

    @api.model
    def _safe_json_dump(self, data):
        try:
            return json.dumps(data, ensure_ascii=False, default=str)[:8000]
        except Exception:  # noqa: BLE001
            return str(data)[:8000]
