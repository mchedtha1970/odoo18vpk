# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging
import traceback
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class VpkHrPayrollService(models.AbstractModel):
    _name = "vpk.hr.payroll.service"
    _description = "รับชุดเงินเดือนจาก HR"

    @api.model
    def ingest_payroll(self, payload, request_meta=None):
        request_meta = request_meta or {}
        payload = payload if isinstance(payload, dict) else {}
        Log = self.env["vpk.hr.payroll.api.log"].sudo()
        log = Log.create(
            {
                "endpoint": request_meta.get("endpoint") or "",
                "http_method": request_meta.get("method") or "POST",
                "remote_addr": request_meta.get("remote_addr"),
                "request_body": self._dump(payload),
                "state": "pending",
                "external_id": self._text(payload.get("external_id")),
                "source_system": self._text(payload.get("source_system")),
            }
        )
        try:
            result = self._ingest_payload(payload)
            log.write(
                {
                    "state": "success",
                    "batch_id": result.get("batch_id"),
                    "external_id": result.get("external_id"),
                    "source_system": result.get("source_system"),
                    "response_body": self._dump(result),
                    "http_status": result.get("http_status", 202),
                }
            )
            return result
        except (UserError, ValidationError) as err:
            log.write(
                {
                    "state": "error",
                    "error_message": str(err),
                    "response_body": self._dump({"ok": False, "error": str(err)}),
                    "http_status": 400,
                }
            )
            raise
        except Exception as err:
            _logger.exception("HR payroll ingest failed")
            log.write(
                {
                    "state": "error",
                    "error_message": str(err),
                    "response_body": traceback.format_exc()[-4000:],
                    "http_status": 500,
                }
            )
            raise UserError(_("รับข้อมูลเงินเดือนไม่สำเร็จ: %s") % err) from err

    @api.model
    def _ingest_payload(self, payload):
        external_id = self._text(payload.get("external_id"))
        source_system = self._text(payload.get("source_system")) or "hr"
        if not external_id:
            raise UserError(_("ต้องส่ง external_id"))
        pay_date = self._date(payload.get("pay_date"))
        if not pay_date:
            raise UserError(_("ต้องส่ง pay_date เป็น YYYY-MM-DD"))
        lines = payload.get("lines")
        if lines is None:
            lines = payload.get("items")
        if not isinstance(lines, list) or not lines:
            raise UserError(_("ต้องส่ง lines เป็นรายการเงินเดือน"))

        Batch = self.env["vpk.hr.payroll.batch"].sudo()
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
            raise UserError(_("ชุด %s ถูกยกเลิกแล้ว ใช้ external_id ใหม่") % external_id)

        control = payload.get("control_totals") or {}
        vals = {
            "external_id": external_id,
            "source_system": source_system,
            "pay_date": pay_date,
            "period": self._text(payload.get("period")) or False,
            "description": self._text(payload.get("description")) or False,
            "control_debit_total": self._amount(control.get("debit_total")),
            "state": "draft",
            "error_message": False,
        }
        if existing:
            existing.line_ids.unlink()
            existing.write(vals)
            batch = existing
            action = "updated"
        else:
            batch = Batch.create(vals)
            action = "created"
        self._create_lines(batch, lines)
        batch.action_validate()
        result = batch.to_api_dict()
        result["action"] = action
        result["http_status"] = 202
        return result

    @api.model
    def _create_lines(self, batch, lines):
        Line = self.env["vpk.hr.payroll.line"].sudo()
        for item in lines:
            if not isinstance(item, dict):
                raise UserError(_("แต่ละบรรทัดต้องเป็น object"))
            code = self._text(item.get("component_code"))
            if not code:
                raise UserError(_("lines[].component_code จำเป็น"))
            Line.create(
                {
                    "batch_id": batch.id,
                    "line_external_id": self._text(item.get("line_external_id")) or False,
                    "component_code": code,
                    "description": self._text(item.get("description")) or False,
                    "department_code": self._text(item.get("department_code")) or False,
                    "amount": self._amount(item.get("amount")),
                }
            )

    @api.model
    def get_batch(self, external_id, source_system=None):
        domain = [("external_id", "=", external_id)]
        if source_system:
            domain.append(("source_system", "=", source_system))
        batch = self.env["vpk.hr.payroll.batch"].sudo().search(domain, limit=1)
        if not batch:
            raise UserError(_("ไม่พบชุดเงินเดือน %s") % external_id)
        return batch.to_api_dict()

    @api.model
    def _text(self, value):
        if value is None:
            return ""
        return str(value).strip()

    @api.model
    def _amount(self, value):
        if value in (None, ""):
            return 0.0
        return float(value)

    @api.model
    def _date(self, value):
        text = self._text(value)
        if not text:
            return False
        try:
            return fields.Date.to_date(datetime.strptime(text[:10], "%Y-%m-%d").date())
        except ValueError:
            return False

    @api.model
    def _dump(self, payload):
        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except TypeError:
            return str(payload)
