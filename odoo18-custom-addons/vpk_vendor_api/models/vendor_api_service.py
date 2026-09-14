# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import binascii
import json
import logging
import traceback

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_normalize

_logger = logging.getLogger(__name__)


class VendorApiService(models.AbstractModel):
    _name = "vpk.vendor.api.service"
    _description = "Vendor Registration API Service"

    @api.model
    def register_vendor(self, payload, request_meta=None):
        """Create or update a supplier partner from external payload.

        Returns dict suitable for JSON response.
        """
        request_meta = request_meta or {}
        Log = self.env["vpk.vendor.api.log"].sudo()
        log = Log.create(
            {
                "endpoint": request_meta.get("endpoint") or "/vpk/api/v1/vendors/register",
                "http_method": request_meta.get("method") or "POST",
                "remote_addr": request_meta.get("remote_addr"),
                "request_body": self._safe_json_dump(payload),
                "state": "pending",
            }
        )
        try:
            result = self._register_vendor(payload)
            log.write(
                {
                    "state": "success",
                    "partner_id": result.get("partner_id"),
                    "external_id": result.get("external_id"),
                    "action": result.get("action"),
                    "response_body": self._safe_json_dump(result),
                    "http_status": 200,
                }
            )
            return result
        except (UserError, ValidationError) as err:
            log.write(
                {
                    "state": "error",
                    "error_message": str(err),
                    "response_body": self._safe_json_dump(
                        {"ok": False, "error": str(err)}
                    ),
                    "http_status": 400,
                }
            )
            raise
        except Exception as err:  # noqa: BLE001 — log then re-raise as UserError
            _logger.exception("Vendor API register failed")
            log.write(
                {
                    "state": "error",
                    "error_message": str(err),
                    "response_body": traceback.format_exc()[-4000:],
                    "http_status": 500,
                }
            )
            raise UserError(_("Vendor API internal error: %s") % err) from err

    @api.model
    def _register_vendor(self, payload):
        if not isinstance(payload, dict):
            raise UserError(_("Request body must be a JSON object"))

        external_id = self._clean_str(payload.get("external_id") or payload.get("external_ref"))
        vat = self._clean_str(payload.get("vat"))
        company_registry = self._clean_str(
            payload.get("company_registry") or payload.get("branch")
        ) or "00000"
        company_type = (payload.get("company_type") or "company").strip()
        if company_type not in ("company", "person"):
            raise UserError(_("company_type must be 'company' or 'person'"))

        Partner = self.env["res.partner"].sudo().with_context(
            res_partner_search_mode="supplier",
            default_supplier_rank=1,
        )
        partner = self._find_existing(Partner, external_id, vat, company_registry)
        vals = self._prepare_partner_vals(payload, external_id, vat, company_registry, company_type)

        if partner:
            action = "updated"
            partner.write(vals)
        else:
            action = "created"
            partner = Partner.create(vals)

        # Ensure supplier
        if partner.supplier_rank < 1:
            partner.supplier_rank = 1

        self._sync_banks(partner, payload.get("banks") or [])
        self._sync_contacts(partner, payload.get("contacts") or [])
        documents_info = self._sync_documents(
            partner,
            payload.get("documents") or payload.get("files") or [],
        )

        portal_info = {}
        portal_payload = payload.get("portal_user") or {}
        if portal_payload.get("create"):
            portal_info = self._create_or_update_portal_user(partner, portal_payload)

        partner.message_post(
            body=_(
                "Vendor profile %(action)s via Vendor API"
                "%(ext)s",
                action=action,
                ext=(" (external_id=%s)" % external_id) if external_id else "",
            )
        )

        result = {
            "ok": True,
            "action": action,
            "partner_id": partner.id,
            "name": partner.name,
            "external_id": partner.vpk_vendor_external_id or False,
            "vat": partner.vat or False,
            "company_registry": partner.company_registry or False,
            "supplier_rank": partner.supplier_rank,
            "portal_url": self._portal_url(),
            "documents": documents_info,
        }
        result.update(portal_info)
        return result

    @api.model
    def upload_vendor_documents(self, partner, documents, request_meta=None):
        """Attach commercial documents to an existing vendor."""
        request_meta = request_meta or {}
        Log = self.env["vpk.vendor.api.log"].sudo()
        log = Log.create(
            {
                "endpoint": request_meta.get("endpoint")
                or "/vpk/api/v1/vendors/<id>/documents",
                "http_method": request_meta.get("method") or "POST",
                "remote_addr": request_meta.get("remote_addr"),
                "request_body": self._safe_json_dump(
                    {
                        "partner_id": partner.id,
                        "external_id": partner.vpk_vendor_external_id,
                        "documents": documents,
                    }
                ),
                "state": "pending",
                "partner_id": partner.id,
                "external_id": partner.vpk_vendor_external_id,
            }
        )
        try:
            docs = self._sync_documents(partner, documents)
            result = {
                "ok": True,
                "action": "documents_uploaded",
                "partner_id": partner.id,
                "external_id": partner.vpk_vendor_external_id or False,
                "documents": docs,
            }
            log.write(
                {
                    "state": "success",
                    "action": "documents_uploaded",
                    "response_body": self._safe_json_dump(result),
                    "http_status": 200,
                }
            )
            partner.message_post(
                body=_(
                    "Uploaded %(count)s commercial document(s) via Vendor API",
                    count=len(docs),
                )
            )
            return result
        except (UserError, ValidationError) as err:
            log.write(
                {
                    "state": "error",
                    "error_message": str(err),
                    "http_status": 400,
                    "response_body": self._safe_json_dump(
                        {"ok": False, "error": str(err)}
                    ),
                }
            )
            raise
        except Exception as err:  # noqa: BLE001
            _logger.exception("Vendor document upload failed")
            log.write(
                {
                    "state": "error",
                    "error_message": str(err),
                    "http_status": 500,
                    "response_body": traceback.format_exc()[-4000:],
                }
            )
            raise UserError(_("Vendor API internal error: %s") % err) from err

    @api.model
    def list_vendor_documents(self, partner):
        Attachment = self.env["ir.attachment"].sudo()
        attachments = Attachment.search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", partner.id),
                ("type", "=", "binary"),
            ],
            order="id desc",
        )
        return [self._attachment_to_dict(att) for att in attachments]

    @api.model
    def _sync_documents(self, partner, documents):
        if not documents:
            return []
        if not isinstance(documents, list):
            raise UserError(_("documents must be a list"))

        max_bytes = self._max_upload_bytes()
        Attachment = self.env["ir.attachment"].sudo()
        results = []
        for item in documents:
            if not isinstance(item, dict):
                raise UserError(_("Each document must be an object"))
            filename = self._clean_str(
                item.get("filename") or item.get("name") or item.get("fname")
            )
            if not filename:
                raise UserError(_("Each document requires filename"))
            doc_type = self._clean_str(item.get("doc_type") or item.get("type")) or "other"
            display_name = self._clean_str(item.get("display_name")) or filename
            mimetype = self._clean_str(item.get("mimetype") or item.get("content_type"))

            raw = item.get("content")
            if raw is None:
                b64 = item.get("content_base64") or item.get("datas")
                if not b64:
                    raise UserError(
                        _("Document '%s' requires content_base64 or content") % filename
                    )
                try:
                    if isinstance(b64, bytes):
                        b64 = b64.decode("ascii")
                    # Allow data-URL prefix
                    if isinstance(b64, str) and "," in b64 and b64.strip().startswith(
                        "data:"
                    ):
                        b64 = b64.split(",", 1)[1]
                    raw = base64.b64decode(b64, validate=False)
                except (binascii.Error, ValueError, TypeError) as err:
                    raise UserError(
                        _("Document '%s' has invalid base64 content") % filename
                    ) from err
            elif isinstance(raw, str):
                raw = raw.encode("utf-8")
            elif not isinstance(raw, (bytes, bytearray)):
                raise UserError(_("Document '%s' content must be bytes or base64") % filename)

            raw = bytes(raw)
            if not raw:
                raise UserError(_("Document '%s' is empty") % filename)
            if len(raw) > max_bytes:
                raise UserError(
                    _(
                        "Document '%(name)s' exceeds max size (%(max)s bytes)",
                        name=filename,
                        max=max_bytes,
                    )
                )

            datas = base64.b64encode(raw)
            replace = bool(item.get("replace", True))
            existing = Attachment.search(
                [
                    ("res_model", "=", "res.partner"),
                    ("res_id", "=", partner.id),
                    ("name", "=", filename),
                    ("description", "=", self._doc_description(doc_type, display_name)),
                ],
                limit=1,
            )
            if not existing and replace:
                # Also match same filename + same doc_type prefix
                candidates = Attachment.search(
                    [
                        ("res_model", "=", "res.partner"),
                        ("res_id", "=", partner.id),
                        ("name", "=", filename),
                    ]
                )
                for cand in candidates:
                    if (cand.description or "").startswith("vpk_doc_type:%s|" % doc_type):
                        existing = cand
                        break

            vals = {
                "name": filename,
                "datas": datas,
                "res_model": "res.partner",
                "res_id": partner.id,
                "type": "binary",
                "description": self._doc_description(doc_type, display_name),
            }
            if mimetype:
                vals["mimetype"] = mimetype

            if existing and replace:
                existing.write(vals)
                attachment = existing
                action = "updated"
            else:
                attachment = Attachment.create(vals)
                action = "created"

            results.append(
                {
                    **self._attachment_to_dict(attachment),
                    "action": action,
                    "doc_type": doc_type,
                }
            )
        return results

    @api.model
    def _doc_description(self, doc_type, display_name):
        return "vpk_doc_type:%s|%s" % (doc_type, display_name)

    @api.model
    def _parse_doc_description(self, description):
        description = description or ""
        if description.startswith("vpk_doc_type:"):
            rest = description[len("vpk_doc_type:") :]
            doc_type, _, display = rest.partition("|")
            return doc_type or "other", display or False
        return "other", description or False

    @api.model
    def _attachment_to_dict(self, attachment):
        doc_type, display_name = self._parse_doc_description(attachment.description)
        return {
            "attachment_id": attachment.id,
            "filename": attachment.name,
            "display_name": display_name or attachment.name,
            "doc_type": doc_type,
            "mimetype": attachment.mimetype or False,
            "file_size": attachment.file_size or 0,
        }

    @api.model
    def _max_upload_bytes(self):
        raw = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_vendor_api.max_upload_mb", "10")
        )
        try:
            mb = float(raw or 10)
        except ValueError:
            mb = 10.0
        return int(mb * 1024 * 1024)

    @api.model
    def _find_existing(self, Partner, external_id, vat, company_registry):
        if external_id:
            partner = Partner.search(
                [("vpk_vendor_external_id", "=", external_id)], limit=1
            )
            if partner:
                return partner
        if vat:
            domain = [
                ("vat", "=", vat),
                ("company_registry", "=", company_registry),
                ("parent_id", "=", False),
            ]
            partner = Partner.search(domain, limit=1)
            if partner:
                return partner
        return Partner.browse()

    @api.model
    def _prepare_partner_vals(self, payload, external_id, vat, company_registry, company_type):
        is_company = company_type == "company"
        name_company = self._clean_str(payload.get("name_company") or payload.get("name"))
        if is_company and not name_company:
            raise UserError(_("name_company (or name) is required for company vendors"))
        if not is_company:
            firstname = self._clean_str(payload.get("firstname"))
            lastname = self._clean_str(payload.get("lastname"))
            if not firstname and not lastname and not name_company:
                raise UserError(_("firstname/lastname or name is required for person vendors"))

        vals = {
            "company_type": company_type,
            "is_company": is_company,
            "supplier_rank": 1,
            "customer_rank": int(payload.get("customer_rank") or 0),
            "vat": vat or False,
            "company_registry": company_registry if is_company else False,
            "email": self._clean_str(payload.get("email")) or False,
            "phone": self._clean_str(payload.get("phone")) or False,
            "mobile": self._clean_str(payload.get("mobile")) or False,
            "website": self._clean_str(payload.get("website")) or False,
            "street": self._clean_str(payload.get("street")) or False,
            "street2": self._clean_str(payload.get("street2")) or False,
            "city": self._clean_str(payload.get("city")) or False,
            "zip": self._clean_str(payload.get("zip")) or False,
            "comment": self._clean_str(payload.get("comment")) or False,
            "ref": self._clean_str(payload.get("ref")) or external_id or False,
        }
        if external_id:
            vals["vpk_vendor_external_id"] = external_id

        if is_company:
            vals["name_company"] = name_company
        else:
            if firstname or lastname:
                vals["firstname"] = firstname or False
                vals["lastname"] = lastname or False
            else:
                vals["name"] = name_company

        # Legal form (shortcut e.g. บจก. / name e.g. บริษัทจำกัด)
        type_code = self._clean_str(
            payload.get("partner_company_type_code")
            or payload.get("company_legal_type")
            or payload.get("partner_company_type")
        )
        if type_code and "partner_company_type_id" in self.env["res.partner"]._fields:
            CType = self.env["res.partner.company.type"].sudo()
            ctype = CType.search([("shortcut", "=", type_code)], limit=1)
            if not ctype:
                ctype = CType.search([("name", "=", type_code)], limit=1)
            if not ctype:
                ctype = CType.search(
                    ["|", ("shortcut", "ilike", type_code), ("name", "ilike", type_code)],
                    limit=1,
                )
            if ctype:
                vals["partner_company_type_id"] = ctype.id

        country = self._resolve_country(payload)
        if country:
            vals["country_id"] = country.id
        state = self._resolve_state(payload, country)
        if state:
            vals["state_id"] = state.id

        return {k: v for k, v in vals.items() if v is not False or k in (
            "vat", "email", "phone", "mobile", "street", "street2", "city", "zip", "comment", "ref"
        )}

    @api.model
    def _resolve_country(self, payload):
        Country = self.env["res.country"].sudo()
        code = self._clean_str(payload.get("country_code") or "TH")
        country = Country.search([("code", "=", code.upper())], limit=1)
        return country

    @api.model
    def _resolve_state(self, payload, country):
        code = self._clean_str(payload.get("state_code"))
        name = self._clean_str(payload.get("state_name"))
        if not country or (not code and not name):
            return self.env["res.country.state"]
        State = self.env["res.country.state"].sudo()
        domain = [("country_id", "=", country.id)]
        if code:
            state = State.search(domain + [("code", "=", code)], limit=1)
            if state:
                return state
        if name:
            return State.search(domain + [("name", "ilike", name)], limit=1)
        return State.browse()

    @api.model
    def _sync_banks(self, partner, banks):
        if not banks:
            return
        Bank = self.env["res.bank"].sudo()
        PartnerBank = self.env["res.partner.bank"].sudo()
        for item in banks:
            if not isinstance(item, dict):
                continue
            acc_number = self._clean_str(item.get("acc_number"))
            if not acc_number:
                continue
            bank = self.env["res.bank"]
            bank_code = self._clean_str(item.get("bank_code"))
            bank_name = self._clean_str(item.get("bank_name") or item.get("bank"))
            if bank_code and "bank_code" in Bank._fields:
                bank = Bank.search([("bank_code", "=", bank_code)], limit=1)
            if not bank and bank_name:
                bank = Bank.search([("name", "=", bank_name)], limit=1)
                if not bank:
                    bank_vals = {"name": bank_name}
                    if bank_code and "bank_code" in Bank._fields:
                        bank_vals["bank_code"] = bank_code
                    branch = self._clean_str(item.get("bank_branch_code"))
                    if branch and "bank_branch_code" in Bank._fields:
                        bank_vals["bank_branch_code"] = branch
                    bank = Bank.create(bank_vals)

            existing = PartnerBank.search(
                [("partner_id", "=", partner.id), ("acc_number", "=", acc_number)],
                limit=1,
            )
            bank_vals = {
                "partner_id": partner.id,
                "acc_number": acc_number,
                "acc_holder_name": self._clean_str(item.get("acc_holder_name")) or partner.name,
                "bank_id": bank.id if bank else False,
            }
            if "allow_out_payment" in PartnerBank._fields and "allow_out_payment" in item:
                bank_vals["allow_out_payment"] = bool(item.get("allow_out_payment"))
            if existing:
                existing.write(bank_vals)
            else:
                PartnerBank.create(bank_vals)

    @api.model
    def _sync_contacts(self, partner, contacts):
        if not contacts:
            return
        Partner = self.env["res.partner"].sudo()
        for item in contacts:
            if not isinstance(item, dict):
                continue
            email = self._clean_str(item.get("email"))
            firstname = self._clean_str(item.get("firstname"))
            lastname = self._clean_str(item.get("lastname"))
            name = self._clean_str(item.get("name"))
            if not name and (firstname or lastname):
                name = " ".join(p for p in (firstname, lastname) if p)
            if not name and not email:
                continue
            contact_type = self._clean_str(item.get("type")) or "contact"
            domain = [("parent_id", "=", partner.id), ("type", "=", contact_type)]
            if email:
                domain.append(("email", "=", email))
            elif name:
                domain.append(("name", "=", name))
            existing = Partner.search(domain, limit=1)
            vals = {
                "parent_id": partner.id,
                "type": contact_type,
                "company_type": "person",
                "email": email or False,
                "phone": self._clean_str(item.get("phone")) or False,
                "mobile": self._clean_str(item.get("mobile")) or False,
                "function": self._clean_str(item.get("function")) or False,
            }
            if firstname or lastname:
                vals["firstname"] = firstname or False
                vals["lastname"] = lastname or False
            elif name:
                vals["name"] = name
            if existing:
                existing.write(vals)
            else:
                Partner.create(vals)

    @api.model
    def _create_or_update_portal_user(self, partner, portal_payload):
        email = self._clean_str(portal_payload.get("email") or partner.email)
        login = self._clean_str(portal_payload.get("login") or email)
        password = portal_payload.get("password")
        if not email or not login:
            raise UserError(_("portal_user.create requires email and login"))
        if not password or len(str(password)) < 4:
            raise UserError(_("portal_user.password must be at least 4 characters"))

        partner.write({"email": email})
        group_portal = self.env.ref("base.group_portal")
        group_public = self.env.ref("base.group_public")
        Users = (
            self.env["res.users"]
            .sudo()
            .with_context(no_reset_password=True, active_test=False)
        )

        conflict = Users.search(
            [("login", "=", login), ("partner_id", "!=", partner.id)], limit=1
        )
        if conflict:
            raise UserError(
                _("Login '%(login)s' is already used by %(name)s", login=login, name=conflict.name)
            )

        user = partner.with_context(active_test=False).user_ids[:1]
        if user and user._is_internal():
            raise UserError(
                _("Partner is linked to an internal user; cannot create portal user")
            )

        company = partner.company_id or self.env.company
        if not user:
            user = Users.with_company(company)._create_user_from_template(
                {
                    "name": partner.name,
                    "login": login,
                    "email": email_normalize(email) or email,
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "company_ids": [(6, 0, company.ids)],
                }
            )
        else:
            user.write(
                {
                    "login": login,
                    "email": email_normalize(email) or email,
                    "active": True,
                }
            )

        user.write(
            {
                "active": True,
                "groups_id": [(4, group_portal.id), (3, group_public.id)],
            }
        )
        user.sudo()._set_encrypted_password(
            user.id, user._crypt_context().hash(str(password))
        )
        partner.sudo().signup_type = False

        return {
            "portal_user_id": user.id,
            "portal_login": user.login,
            "portal_created": True,
        }

    @api.model
    def _portal_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        return f"{base}/vendor"

    @api.model
    def _clean_str(self, value):
        if value is None:
            return False
        text = str(value).strip()
        return text or False

    @api.model
    def _safe_json_dump(self, data):
        try:
            data = self._mask_sensitive(data)
            return json.dumps(data, ensure_ascii=False, default=str)[:8000]
        except Exception:  # noqa: BLE001
            return str(data)[:8000]

    @api.model
    def _mask_sensitive(self, data):
        if isinstance(data, list):
            return [self._mask_sensitive(x) for x in data]
        if not isinstance(data, dict):
            return data
        masked = dict(data)
        portal = masked.get("portal_user")
        if isinstance(portal, dict) and portal.get("password"):
            portal = dict(portal)
            portal["password"] = "***"
            masked["portal_user"] = portal
        for key in ("documents", "files"):
            docs = masked.get(key)
            if isinstance(docs, list):
                cleaned = []
                for doc in docs:
                    if isinstance(doc, dict):
                        doc = dict(doc)
                        for secret in ("content_base64", "datas", "content"):
                            if secret in doc and doc[secret]:
                                size = (
                                    len(doc[secret])
                                    if isinstance(doc[secret], (str, bytes, bytearray))
                                    else "?"
                                )
                                doc[secret] = "<omitted len=%s>" % size
                        cleaned.append(doc)
                    else:
                        cleaned.append(doc)
                masked[key] = cleaned
        return masked
