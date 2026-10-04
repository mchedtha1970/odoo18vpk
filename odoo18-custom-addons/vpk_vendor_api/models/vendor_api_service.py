# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import re
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import email_normalize


class VendorApiService(models.AbstractModel):
    _name = "vpk.vendor.api.service"
    _description = "Vendor mobile API"

    def _vendor_user(self):
        user = self.env.user
        if not user or user._is_public() or not user._is_portal():
            raise AccessError(_("บัญชีนี้ไม่ใช่ผู้ขาย"))
        return user

    def _partner_domain(self):
        user = self._vendor_user()
        commercial = user.partner_id.commercial_partner_id
        return [("partner_id", "child_of", commercial.id), ("vpk_po_sent_on", "!=", False)]

    def _order_domain(self, status="waiting"):
        status = (status or "waiting").strip().lower()
        domain = list(self._partner_domain())
        if status in ("confirmed", "signed", "done"):
            domain.append(("vpk_vendor_confirm_state", "=", "confirmed"))
            return domain, "confirmed"
        if status == "all":
            return domain, "all"
        domain.append(("vpk_vendor_confirm_state", "=", "waiting"))
        return domain, "waiting"

    def _require_order(self, order_id):
        order = self.env["purchase.order"].browse(int(order_id)).exists()
        if not order or not order.filtered_domain(self._partner_domain()):
            raise UserError(_("ไม่พบใบสั่งซื้อ"))
        return order

    def search_orders(self, limit=50, offset=0, status="waiting"):
        domain, status = self._order_domain(status)
        limit = min(max(int(limit or 50), 1), 200)
        offset = max(int(offset or 0), 0)
        Order = self.env["purchase.order"].sudo()
        count = Order.search_count(domain)
        orders = Order.search(domain, limit=limit, offset=offset, order="vpk_po_sent_on desc, id desc")
        return {
            "count": count,
            "limit": limit,
            "offset": offset,
            "status": status,
            "items": [self.serialize_order(order) for order in orders],
        }

    def get_order(self, order_id):
        return self.serialize_order(self._require_order(order_id).sudo(), detail=True)

    def search_zips(self, query, limit=20):
        """Lookup Thai Geonames postal codes the same way the Odoo address widget does."""
        term = re.sub(r"[%_]", "", (query or "").strip())
        if len(term) < 3:
            return {"items": []}
        limit = min(max(int(limit or 20), 1), 30)
        Zip = self.env["res.city.zip"].sudo().with_context(lang="th_TH")
        records = Zip.search([("name", "=ilike", "%s%%" % term)], limit=limit, order="name, id")
        items = []
        for rec in records:
            city_name = rec.city_id.name or ""
            parts = city_name.split(", ", 1)
            street2 = parts[0] if len(parts) == 2 else ""
            city = parts[1] if len(parts) == 2 else city_name
            state = rec.city_id.state_id.name or ""
            country = rec.city_id.country_id.name or ""
            label = ", ".join(part for part in (rec.name, city_name, state, country) if part)
            items.append(
                {
                    "id": rec.id,
                    "zip": rec.name or "",
                    "label": label,
                    "street2": street2,
                    "city": city,
                    "state": state,
                    "country": country,
                }
            )
        return {"items": items}

    def _address_vals(self, env, payload):
        vals = {}
        street = (payload.get("street") or "").strip()
        if street:
            vals["street"] = street
        zip_id = payload.get("zip_id")
        if not zip_id:
            return vals
        try:
            zip_id = int(zip_id)
        except (TypeError, ValueError) as err:
            raise UserError(_("ไม่พบรหัสไปรษณีย์")) from err
        record = env["res.city.zip"].browse(zip_id).exists()
        if not record:
            raise UserError(_("ไม่พบรหัสไปรษณีย์"))
        city_name = record.city_id.with_context(lang="th_TH").name or ""
        parts = city_name.split(", ", 1)
        vals.update(
            {
                "zip_id": record.id,
                "zip": record.name,
                "street2": parts[0] if len(parts) == 2 else False,
                "city": parts[1] if len(parts) == 2 else city_name,
                "state_id": record.city_id.state_id.id,
                "country_id": record.city_id.country_id.id,
            }
        )
        if "city_id" in env["res.partner"]._fields:
            vals["city_id"] = record.city_id.id
        return vals

    def register_portal_account(self, payload):
        """Create a supplier partner and a portal login for the vendor app."""
        name = (payload.get("name") or payload.get("name_company") or "").strip()
        email = (payload.get("email") or "").strip()
        password = payload.get("password") or ""
        phone = (payload.get("phone") or "").strip()
        vat = re.sub(r"\D", "", payload.get("vat") or "")
        if not name:
            raise UserError(_("กรุณาระบุชื่อผู้จำหน่าย"))
        if "@" not in email or "." not in email.split("@")[-1]:
            raise UserError(_("กรุณาระบุอีเมลที่ใช้เข้าสู่ระบบ"))
        if len(password) < 6:
            raise UserError(_("รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร"))
        login = email_normalize(email) or email.lower()
        Users = self.env["res.users"].sudo().with_context(
            no_reset_password=True, active_test=False
        )
        if Users.search_count([("login", "=", login)]):
            raise UserError(_("อีเมลนี้มีบัญชีอยู่แล้ว กรุณาเข้าสู่ระบบ"))
        is_company = (payload.get("company_type") or "company").strip() != "person"
        vals = {
            "company_type": "company" if is_company else "person",
            "is_company": is_company,
            "name": name,
            "email": login,
            "phone": phone or False,
            "supplier_rank": 1,
            "customer_rank": 0,
        }
        if is_company:
            vals["name_company"] = name
        elif "firstname" in self.env["res.partner"]._fields:
            vals["firstname"] = name
        if vat:
            if len(vat) != 13:
                raise UserError(_("เลขประจำตัวผู้เสียภาษีต้องมี 13 หลัก"))
            if self.env["res.partner"].sudo().search_count(
                [
                    ("vat", "=", vat),
                    ("company_registry", "=", "00000"),
                    ("parent_id", "=", False),
                ]
            ):
                raise UserError(_("เลขประจำตัวผู้เสียภาษีนี้มีในระบบแล้ว"))
            vals["vat"] = vat
            vals["company_registry"] = "00000"
        company = self.env["res.company"].sudo().search([], order="id", limit=1)
        if not company:
            raise UserError(_("ไม่พบบริษัทในระบบ"))
        root = self.env.ref("base.user_root")
        env = api.Environment(
            self.env.cr,
            root.id,
            dict(self.env.context, allowed_company_ids=[company.id]),
        )
        vals.update(self._address_vals(env, payload))
        partner = env["res.partner"].create(vals)
        group_portal = env.ref("base.group_portal")
        Users = env["res.users"].with_context(no_reset_password=True, active_test=False)
        user = Users.create(
            {
                "name": partner.name,
                "login": login,
                "email": login,
                "partner_id": partner.id,
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "groups_id": [(6, 0, [group_portal.id])],
                "password": password,
            }
        )
        user.sudo()._set_encrypted_password(user.id, user._crypt_context().hash(password))
        return {"ok": True, "login": user.login, "partner_id": partner.id}

    def _profile_payload(self, user):
        partner = user.partner_id.commercial_partner_id.sudo()
        return {
            "name": partner.display_name or partner.name or "",
            "vat": partner.vat or "",
            "email": partner.email or "",
            "login": user.login or "",
            "phone": partner.phone or partner.mobile or "",
            "street": partner.street or "",
            "street2": partner.street2 or "",
            "city": partner.city or "",
            "zip": partner.zip or "",
            "state": partner.state_id.with_context(lang="th_TH").name or "",
            "country": partner.country_id.with_context(lang="th_TH").name or "",
            "company_type": "company" if partner.is_company else "person",
            "zip_id": partner.zip_id.id or False,
        }

    def get_profile(self):
        user = self._vendor_user()
        return {"profile": self._profile_payload(user)}

    def update_profile(self, payload):
        user = self._vendor_user()
        partner = user.partner_id.commercial_partner_id.sudo()
        vals = {}
        if payload.get("zip_id"):
            vals.update(self._address_vals(partner.env, payload))
        for key in ("phone", "street", "street2"):
            if key in payload:
                vals[key] = (payload.get(key) or "").strip()
        if vals:
            partner.write(vals)
        return {"profile": self._profile_payload(user)}

    def me(self):
        user = self._vendor_user()
        waiting = self.search_orders(limit=1, offset=0, status="waiting")["count"]
        confirmed = self.search_orders(limit=1, offset=0, status="confirmed")["count"]
        return {
            "user": {
                "id": user.id,
                "login": user.login,
                "name": user.name,
            },
            "waiting_count": waiting,
            "confirmed_count": confirmed,
        }

    def serialize_order(self, order, detail=False):
        labels = dict(
            order._fields["vpk_vendor_confirm_state"]._description_selection(order.env)
        )
        state_labels = dict(order._fields["state"]._description_selection(order.env))
        payload = {
            "id": order.id,
            "name": order.name or "",
            "title": order.name or "",
            "partner": order.partner_id.display_name or "",
            "amount_total": order.amount_total,
            "currency": order.currency_id.name or "",
            "date_order": fields.Datetime.to_string(order.date_order) if order.date_order else False,
            "sent_on": fields.Datetime.to_string(order.vpk_po_sent_on) if order.vpk_po_sent_on else False,
            "state": order.state,
            "state_label": state_labels.get(order.state, order.state),
            "status": order.vpk_vendor_confirm_state,
            "status_label": labels.get(
                order.vpk_vendor_confirm_state, order.vpk_vendor_confirm_state
            ),
            "can_sign": order.vpk_vendor_confirm_state == "waiting" and bool(order.has_pdf),
            "has_pdf": bool(order.has_pdf),
            "pdf_filename": order.pdf_filename or "",
            "pdf_url": "/vpk/api/v1/vendor/orders/%s/pdf" % order.id if order.has_pdf else False,
            "signed_by": order.signed_by or "",
            "signed_on": fields.Datetime.to_string(order.signed_on) if order.signed_on else False,
            "origin": order.origin or "",
        }
        if detail:
            payload["project_name"] = (
                order.egp_project_name if "egp_project_name" in order._fields else ""
            ) or ""
            payload["project_reference"] = (
                order.egp_project_reference
                if "egp_project_reference" in order._fields
                else ""
            ) or ""
        return payload

    def get_pdf(self, order_id):
        order = self._require_order(order_id).sudo()
        attachment = order._vpk_po_pdf_attachment()
        if not attachment or not attachment.raw:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณารอฝ่ายจัดซื้อพิมพ์ใบสั่งซื้อ"))
        filename = attachment.name or "purchase-order.pdf"
        return {
            "filename": filename,
            "content": attachment.raw,
            "content_disposition": "inline; filename*=UTF-8''%s" % quote(filename),
        }

    def sign_order(self, order_id, signature=None, name=None):
        order = self._require_order(order_id).sudo()
        if order.vpk_vendor_confirm_state != "waiting":
            raise UserError(_("ใบสั่งซื้อนี้ไม่ได้อยู่ในสถานะรอผู้ขายยืนยัน"))
        if not order._can_vendor_confirm():
            raise UserError(_("เอกสารนี้ไม่ได้อยู่ในสถานะที่ต้องให้ผู้ขายยืนยัน"))
        signer = (name or self.env.user.name or order.partner_id.name or "").strip()
        raw = (signature or "").strip()
        if raw.startswith("data:"):
            raw = raw.split(",", 1)[-1]
        order._vpk_stamp_vendor_signature(raw)
        order.action_portal_vendor_confirm(name=signer, signature=raw)
        order.invalidate_recordset()
        return {"ok": True, "item": self.serialize_order(order)}

    def _trade_partner(self):
        user = self._vendor_user()
        return user.partner_id.commercial_partner_id

    def _trade_payload(self, document):
        return {
            "id": document.id,
            "name": document.name or "",
            "date": fields.Date.to_string(document.doc_date) or "",
            "filename": document.filename or "",
            "note": document.note or "",
            "has_file": bool(document.datas),
        }

    def list_trade_documents(self):
        partner = self._trade_partner()
        documents = self.env["vpk.vendor.trade.document"].sudo().search(
            [("partner_id", "=", partner.id)]
        )
        return {"items": [self._trade_payload(document) for document in documents]}

    def create_trade_document(self, payload):
        partner = self._trade_partner()
        name = (payload.get("name") or "").strip()
        filename = (payload.get("filename") or "").strip()
        encoded = (payload.get("file") or "").strip()
        if encoded.startswith("data:"):
            encoded = encoded.split(",", 1)[-1]
        encoded = "".join(encoded.split())
        if not name:
            raise UserError(_("กรุณาระบุชื่อเอกสาร"))
        if not filename.lower().endswith(".pdf"):
            raise UserError(_("อัปโหลดได้เฉพาะไฟล์ PDF"))
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception as err:
            raise UserError(_("ไฟล์ PDF ไม่ถูกต้อง")) from err
        if not raw.startswith(b"%PDF") or len(raw) > 15 * 1024 * 1024:
            if not raw.startswith(b"%PDF"):
                raise UserError(_("ไฟล์ไม่ใช่ PDF"))
            raise UserError(_("ไฟล์ต้องมีขนาดไม่เกิน 15 MB"))
        document = self.env["vpk.vendor.trade.document"].sudo().create(
            {
                "partner_id": partner.id,
                "name": name,
                "filename": filename,
                "datas": encoded,
                "note": (payload.get("note") or "").strip() or False,
            }
        )
        return {"item": self._trade_payload(document)}

    def get_trade_document_pdf(self, document_id):
        partner = self._trade_partner()
        document = self.env["vpk.vendor.trade.document"].sudo().browse(int(document_id)).exists()
        if not document or document.partner_id != partner or not document.datas:
            raise AccessError(_("ไม่พบเอกสาร"))
        filename = document.filename or "document.pdf"
        attachment = document._pdf_attachment()
        content = attachment.raw if attachment else base64.b64decode(document.datas)
        return {
            "filename": filename,
            "content": content,
            "content_disposition": "inline; filename*=UTF-8''%s" % quote(filename),
        }

    def delete_trade_document(self, document_id):
        partner = self._trade_partner()
        document = self.env["vpk.vendor.trade.document"].sudo().browse(int(document_id)).exists()
        if not document or document.partner_id != partner:
            raise AccessError(_("ไม่พบเอกสาร"))
        document.unlink()
        return {"ok": True}
