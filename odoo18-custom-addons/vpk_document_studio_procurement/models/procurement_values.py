from odoo import _, api, fields, models

THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
ROLE_LABELS = {
    "chairman": "ประธานกรรมการ",
    "committee": "กรรมการ",
    "member": "กรรมการ",
    "secretary": "กรรมการและเลขานุการ",
}
INSPECTION_ROLE_LABELS = {
    "chairman": "ประธานกรรมการฯ",
    "committee": "กรรมการ",
    "member": "กรรมการ",
    "secretary": "กรรมการและเลขานุการ",
}
DEFAULT_RECIPIENT = "ผู้ว่าราชการจังหวัดภูเก็ต"
DEFAULT_DIRECTOR_POSITION = "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต"
DEFAULT_ACTING = "ปฏิบัติราชการแทนผู้ว่าราชการจังหวัดภูเก็ต"


class ProcurementDocumentValues(models.AbstractModel):
    """Values for Document Studio templates built from procurement records.

    Every template code listed here is filled from the purchase request,
    work acceptance or purchase order the document is created from. Codes
    the template does not use are ignored.
    """

    _name = "vpk.procurement.document.values"
    _description = "ค่าตั้งต้นของเอกสารจัดซื้อจัดจ้าง"

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------
    @api.model
    def thai(self, value):
        return str(value if value not in (None, False) else "").translate(THAI_DIGITS)

    @api.model
    def money(self, amount):
        return self.thai("{:,.2f}".format(amount or 0.0))

    @api.model
    def qty(self, value):
        value = value or 0.0
        if abs(value - round(value)) < 1e-9:
            return self.thai(int(round(value)))
        return self.thai("{:.4f}".format(value).rstrip("0").rstrip("."))

    @api.model
    def baht_text(self, amount, company=None):
        currency = (company or self.env.company).currency_id
        try:
            text = currency.with_context(lang="th_TH").amount_to_text(amount or 0.0)
        except Exception:
            text = currency.amount_to_text(amount or 0.0)
        if text and "บาท" not in text:
            text = "%sบาทถ้วน" % text
        return text or ""

    @api.model
    def thai_date(self, value):
        if not value:
            return ""
        if hasattr(value, "date") and callable(value.date):
            value = value.date()
        return self.thai(self.env["thai.utils"].format_thai_date(value))

    @api.model
    def person_from_user(self, user):
        if not user:
            return "", ""
        employee = user.sudo().employee_id
        if not employee and "employee_ids" in user._fields:
            employee = user.sudo().employee_ids[:1]
        name = (employee.name if employee else "") or user.name or ""
        position = ""
        if employee:
            position = employee.job_title or (employee.job_id.name if employee.job_id else "")
        return name, position

    @api.model
    def user_by_person_name(self, name):
        name = " ".join((name or "").split())
        if not name:
            return self.env["res.users"]
        user = self.env["res.users"].sudo().search(
            [("name", "=", name), ("share", "=", False)], limit=1
        )
        if user:
            return user
        employees = self.env["hr.employee"].sudo().search([("name", "=", name)], limit=2)
        if len(employees) == 1 and employees.user_id:
            return employees.user_id
        return self.env["res.users"]

    @api.model
    def company_person(self, company, role):
        """Return (user, name, position) for officer / head_officer / signer."""
        user_field = "official_doc_%s_id" % role
        name_field = "official_doc_%s_name" % role
        position_field = "official_doc_%s_position" % role
        user = company[user_field] if user_field in company._fields else self.env["res.users"]
        if not user and name_field in company._fields:
            user = self.user_by_person_name(company[name_field])
        name, position = self.person_from_user(user)
        if not name and name_field in company._fields:
            name = company[name_field] or ""
        if position_field in company._fields and company[position_field]:
            position = position or company[position_field]
        return user, name, position

    @api.model
    def director_secretary(self):
        return self.env.ref(
            "vpk_tier_validation.user_director_secretary", raise_if_not_found=False
        ) or self.env["res.users"]

    # ------------------------------------------------------------------
    # Source lookups
    # ------------------------------------------------------------------
    @api.model
    def request_from_acceptance(self, acceptance):
        purchase = acceptance.purchase_id
        if not purchase or "purchase_request_lines" not in purchase.order_line._fields:
            return self.env["purchase.request"]
        return purchase.order_line.mapped("purchase_request_lines.request_id")[:1]

    @api.model
    def request_from_order(self, order):
        if "purchase_request_lines" not in order.order_line._fields:
            return self.env["purchase.request"]
        return order.order_line.mapped("purchase_request_lines.request_id")[:1]

    @api.model
    def item_summary(self, request):
        if "memo_item_summary" in request._fields and request.memo_item_summary:
            return request.memo_item_summary
        lines = request.line_ids.filtered(lambda line: not getattr(line, "cancelled", False))
        if lines:
            return lines[0].name or lines[0].product_id.display_name or request.name
        return request.description or request.name or ""

    @api.model
    def method_name(self, request):
        if "memo_procurement_method" in request._fields and request.memo_procurement_method:
            return request.memo_procurement_method
        if "procurement_method_id" in request._fields and request.procurement_method_id:
            return request.procurement_method_id.name
        return "วิธีเฉพาะเจาะจง"

    @api.model
    def recipient(self, request):
        if "memo_to" in request._fields and request.memo_to:
            return request.memo_to
        company = request.company_id
        if "vpk_memo_default_to" in company._fields and company.vpk_memo_default_to:
            return company.vpk_memo_default_to
        return DEFAULT_RECIPIENT

    @api.model
    def request_lines(self, request):
        return request.line_ids.filtered(
            lambda line: not getattr(line, "cancelled", False) and line.product_qty
        )

    @api.model
    def committee_rows(self, request=None, acceptance=None, kind="work_acceptance"):
        """[{name, position, role, user}] chairman first."""
        rows = []
        if kind == "price_mid":
            members = (
                request.price_mid_committee_ids
                if request and "price_mid_committee_ids" in request._fields
                else self.env["procurement.committee"]
            )
        else:
            members = self.env["procurement.committee"]
            if acceptance and acceptance.committee_ids:
                for member in acceptance.committee_ids.sorted(
                    key=lambda m: (0 if m.role == "chairman" else 1, m.sequence, m.id)
                ):
                    rows.append(
                        {
                            "name": member.name,
                            "position": member.position or "",
                            "role": member.role or "member",
                            "user": member.employee_id,
                        }
                    )
                return rows
            if request and "work_acceptance_committee_ids" in request._fields:
                members = request.work_acceptance_committee_ids
        for member in members.sorted(
            key=lambda m: (0 if m.approve_role == "chairman" else 1, m.id)
        ):
            employee = member.employee_id
            position = ""
            if employee:
                position = employee.job_title or (employee.job_id.name if employee.job_id else "")
            rows.append(
                {
                    "name": member.name or employee.name or "",
                    "position": position,
                    "role": member.approve_role or "committee",
                    "user": employee.user_id if employee else self.env["res.users"],
                }
            )
        return rows

    @api.model
    def committee_text(self, rows):
        lines = []
        for index, row in enumerate(rows, start=1):
            line = "%s. %s" % (self.thai(index), row["name"])
            if row["position"]:
                line += "  ตำแหน่ง  %s" % row["position"]
            line += "  %s" % ROLE_LABELS.get(row["role"], "กรรมการ")
            lines.append(line)
        return "\n".join(lines)

    @api.model
    def integrity_values(self, values, committee):
        people = [
            (values.get("head_officer_name"), "หัวหน้าเจ้าหน้าที่"),
            (values.get("officer_name"), "เจ้าหน้าที่"),
        ]
        for row in committee:
            role = "ประธานกรรมการตรวจรับพัสดุ" if row["role"] == "chairman" else "กรรมการตรวจรับพัสดุ"
            people.append((row["name"], role))
        people = [(name, role) for name, role in people if name]
        return {
            "integrity_people": "\n".join(
                "ข้าพเจ้า  %s  (%s)" % (name, role) for name, role in people
            ),
            "integrity_signers": "\n\n".join(
                "ลงนาม......................................................\n(%s)\n%s"
                % (name, role)
                for name, role in people
            ),
        }

    # ------------------------------------------------------------------
    # Values per source
    # ------------------------------------------------------------------
    @api.model
    def _people_values(self, company, request=None):
        values = {}
        officer_user, officer_name, officer_position = self.company_person(company, "officer")
        if not officer_name and request:
            officer_name, officer_position = self.person_from_user(
                request.assigned_to or request.requested_by
            )
        _head_user, head_name, head_position = self.company_person(company, "head_officer")
        _signer_user, signer_name, signer_position = self.company_person(company, "signer")
        acting = ""
        if "vpk_memo_approver_acting" in company._fields:
            acting = company.vpk_memo_approver_acting or ""
        values.update(
            {
                "officer_name": officer_name,
                "officer_position": officer_position or "เจ้าหน้าที่",
                "head_officer_name": head_name,
                "head_officer_position": head_position or "หัวหน้าเจ้าหน้าที่",
                "signer_name": signer_name,
                "signer_position": signer_position or DEFAULT_DIRECTOR_POSITION,
                "approver_acting": acting or DEFAULT_ACTING,
            }
        )
        return values

    @api.model
    def values_from_request(self, request, type_code=False):
        request = request.sudo()
        company = request.company_id
        item = self.item_summary(request)
        method = self.method_name(request)
        department = request.department_id.name if request.department_id else company.name
        amount = request.estimated_cost if "estimated_cost" in request._fields else 0.0
        budget = ""
        if "budget_id" in request._fields and request.budget_id:
            budget = request.budget_id.display_name
        reason = ""
        if "expense_reason" in request._fields and request.expense_reason:
            reason = request.expense_reason.strip()
        delivery = 30
        if "memo_delivery_days" in request._fields and request.memo_delivery_days:
            delivery = request.memo_delivery_days
        today = fields.Date.context_today(request)
        proposer_name, proposer_position = self.person_from_user(request.requested_by)
        work_lines = []
        for index, line in enumerate(self.request_lines(request), start=1):
            name = (line.name or line.product_id.display_name or "").strip() or "-"
            text = "%s. %s  จำนวน  %s" % (self.thai(index), name, self.qty(line.product_qty))
            if line.product_uom_id:
                text += "  %s" % line.product_uom_id.name
            text += "  เป็นเงิน  %s  บาท" % self.money(line.estimated_cost)
            work_lines.append(text)
        committee = self.committee_rows(request=request)
        spec_committee = self.committee_rows(request=request, kind="price_mid")
        amount_text = self.money(amount)
        baht = self.baht_text(amount, company)
        purpose = ("เพื่อ%s" % reason) if reason else "เพื่อใช้ในราชการ"
        values = {
            "agency": (
                company.official_doc_agency
                if "official_doc_agency" in company._fields and company.official_doc_agency
                else company.name
            ),
            "department_name": department,
            "memo_date": fields.Date.to_string(today),
            "doc_date_th": self.thai_date(today),
            "order_date_th": self.thai_date(today),
            "year_be": self.thai(today.year + 543),
            "recipient": self.recipient(request),
            "item_summary": item,
            "item_count_th": self.thai(len(work_lines) or 1),
            "procurement_method": method,
            "amount_text": amount_text,
            "baht_text": baht,
            "budget_source": budget or "งบประมาณของหน่วยงาน",
            "price_mid_source": "ราคากลางตามท้องตลาด",
            "delivery_days_th": self.thai(delivery),
            "reason_text": purpose,
            "work_detail": "\n".join(work_lines),
            "committee_lines": self.committee_text(committee),
            "spec_committee_lines": self.committee_text(spec_committee),
            "proposer_name": proposer_name,
            "proposer_position": proposer_position,
            "pr_name": request.name or "",
        }
        values.update(self._people_values(company, request))
        values.update(self.integrity_values(values, committee))
        values["subject"] = self.default_subject(type_code, item, method)
        values["body"] = self.default_body(type_code, values)
        return values

    @api.model
    def values_from_acceptance(self, acceptance, type_code=False):
        acceptance = acceptance.sudo()
        request = self.request_from_acceptance(acceptance)
        values = self.values_from_request(request, type_code) if request else {}
        if not request:
            values.update(self._people_values(acceptance.company_id))
        purchase = acceptance.purchase_id
        contract = acceptance.contract_id if "contract_id" in acceptance._fields else False
        company = acceptance.company_id
        if contract:
            ref_text = "ตาม สัญญา เลขที่ %s ลงวันที่ %s" % (
                self.thai(contract.name),
                self.thai_date(contract.date_start),
            )
            total = contract.amount_total
        else:
            order_date = purchase.date_approve or purchase.date_order
            ref_text = "ตาม ใบสั่งซื้อ เลขที่ %s ลงวันที่ %s" % (
                self.thai(purchase.name or ""),
                self.thai_date(order_date),
            )
            total = purchase.amount_total
        products = purchase.order_line.mapped("product_id")
        verb = "จ้าง" if products and all(p.type == "service" for p in products) else "ซื้อ"
        project = ""
        for source in (purchase, request):
            if source and "egp_project_name" in source._fields and source.egp_project_name:
                project = source.egp_project_name
                break
        if not project and request:
            project = self.item_summary(request)
        project = project or purchase.name or acceptance.name or ""
        method = values.get("procurement_method") or "วิธีเฉพาะเจาะจง"
        if not method.startswith("วิธี"):
            method = "วิธี%s" % method
        installment = (
            acceptance.contract_installment_id
            if "contract_installment_id" in acceptance._fields
            else False
        )
        if installment:
            inspect_intro = "คณะกรรมการตรวจรับพัสดุ ได้ตรวจรับงาน%s แล้ว ผลปรากฏ ดังนี้" % (
                self.thai(installment.name)
            )
        else:
            inspect_intro = "คณะกรรมการตรวจรับพัสดุ ได้ตรวจรับพัสดุแล้ว ผลปรากฏ ดังนี้"
        checked, unchecked = "☑", "☐"
        penalty = acceptance.penalty_amount or 0.0
        has_penalty = bool(acceptance.has_penalty)
        complete = acceptance.inspection_completeness != "incomplete"
        project_no = ""
        for source in (purchase, request):
            if source and "egp_project_reference" in source._fields and source.egp_project_reference:
                project_no = source.egp_project_reference
                break
        committee = self.committee_rows(request=request, acceptance=acceptance)
        signer_lines = []
        for row in committee:
            signer_lines.append(
                "(ลงชื่อ)..................................................... %s\n(%s)"
                % (INSPECTION_ROLE_LABELS.get(row["role"], "กรรมการ"), row["name"])
            )
        report_date = acceptance.acceptance_date or fields.Date.context_today(acceptance)
        values.update(
            {
                "memo_date": fields.Date.to_string(report_date),
                "doc_date_th": self.thai_date(report_date),
                "report_date": "วันที่ %s" % self.thai_date(report_date),
                "intro": "%s %s ได้ตกลง %s กับ %s สำหรับโครงการ %s โดย%s เป็นจำนวนเงินทั้งสิ้น %s บาท (%s)"
                % (
                    ref_text,
                    company.name or "",
                    verb,
                    purchase.partner_id.name or "",
                    project,
                    method,
                    self.money(total),
                    self.baht_text(total, company),
                ),
                "inspect_intro": inspect_intro,
                "chk_correct": checked if acceptance.inspection_correct else unchecked,
                "chk_complete": checked if complete else unchecked,
                "chk_incomplete": unchecked if complete else checked,
                "chk_fine": checked if has_penalty else unchecked,
                "fine_text": (
                    " เป็นจำนวนเงิน %s บาท" % self.money(penalty)
                    if has_penalty and penalty > 0
                    else ""
                ),
                "chk_nofine": unchecked if has_penalty else checked,
                "pay_amount": self.money(acceptance.payment_amount or 0.0),
                "project_no": self.thai(project_no or "-"),
                "contract_no": self.thai((contract.name if contract else "") or "-"),
                "wa_no": self.thai(acceptance.name or "-"),
                "vendor_name": purchase.partner_id.name or "",
                "po_name": purchase.name or "",
                "committee_lines": self.committee_text(committee),
                "inspection_signers": "\n\n".join(signer_lines),
            }
        )
        values.update(self.integrity_values(values, committee))
        if not request:
            values["item_summary"] = purchase.name or acceptance.name or ""
            values["subject"] = self.default_subject(
                type_code, values["item_summary"], "วิธีเฉพาะเจาะจง"
            )
            values["body"] = self.default_body(type_code, values)
        return values

    @api.model
    def values_from_order(self, order, type_code=False):
        request = self.request_from_order(order)
        values = self.values_from_request(request, type_code) if request else {}
        values.setdefault("agency", order.company_id.name)
        values.update(
            {
                "vendor_name": order.partner_id.name or "",
                "po_name": order.name or "",
                "amount_text": self.money(order.amount_total),
                "baht_text": self.baht_text(order.amount_total, order.company_id),
            }
        )
        return values

    @api.model
    def values_for(self, record, type_code=False):
        if not record:
            return {}
        handlers = {
            "purchase.request": self.values_from_request,
            "work.acceptance": self.values_from_acceptance,
            "purchase.order": self.values_from_order,
        }
        handler = handlers.get(record._name)
        return handler(record, type_code) if handler else {}

    # ------------------------------------------------------------------
    # Default wording
    # ------------------------------------------------------------------
    @api.model
    def default_subject(self, type_code, item, method):
        item = item or "................................"
        method = method or "วิธีเฉพาะเจาะจง"
        subjects = {
            "spec_price_committee": (
                "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดรายละเอียดคุณลักษณะเฉพาะและกำหนดราคากลางของ%s"
                % item
            ),
            "specific_method_approval": "รายงานขออนุมัติซื้อ/จ้าง%s  โดย%s" % (item, method),
            "ebidding_method_approval": "รายงานขออนุมัติซื้อ/จ้าง%s  โดย%s" % (item, method),
            "purchase_approval_memo": "ขออนุมัติจัดซื้อ%s" % item,
            "inspection_report": "ใบตรวจรับการจัดซื้อ/จัดจ้าง",
            "integrity_over_100k": "แบบแสดงความบริสุทธิ์ใจในการจัดซื้อจัดจ้าง",
            "wa_committee_order": (
                "แต่งตั้งคณะกรรมการตรวจรับพัสดุ  สำหรับการซื้อ/จ้าง%s  โดย%s" % (item, method)
            ),
        }
        # Types created in Studio keep the subject from their own template.
        return subjects.get(type_code, "")

    @api.model
    def default_body(self, type_code, values):
        department = values.get("department_name") or "................................"
        item = values.get("item_summary") or "................................"
        method = values.get("procurement_method") or "วิธีเฉพาะเจาะจง"
        amount = values.get("amount_text", "")
        baht = values.get("baht_text", "")
        if type_code == "spec_price_committee":
            return _(
                "ด้วย  %(department)s  มีความประสงค์จะดำเนินการจัดซื้อ/จัดจ้าง%(item)s  "
                "จำนวน  %(count)s  รายการ  โดย%(method)s  ใช้งบประมาณจาก%(budget)s  "
                "จำนวนเงิน  %(amount)s  บาท  (%(baht)s)  %(reason)s  "
                "โดยเตรียมความพร้อมสำหรับการดำเนินงานจัดหาพัสดุตามแนวทางปฏิบัติและระเบียบที่เกี่ยวข้อง"
            ) % {
                "department": department,
                "item": item,
                "count": values.get("item_count_th", "๑"),
                "method": method,
                "budget": values.get("budget_source", ""),
                "amount": amount,
                "baht": baht,
                "reason": values.get("reason_text", ""),
            }
        if type_code in ("specific_method_approval", "ebidding_method_approval"):
            return _(
                "ด้วย%(department)s  มีความประสงค์ในการจัดซื้อจัดจ้าง%(item)s  "
                "เป็นจำนวนเงินทั้งสิ้น  %(amount)s  บาท  (%(baht)s)  %(reason)s  "
                "โดยใช้งบประมาณจาก%(budget)s  "
                "ซึ่งขอจัดซื้อจัดจ้างตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
                "พ.ศ. ๒๕๖๐  ข้อ  ๒๒  โดยมีรายละเอียด  ดังต่อไปนี้"
            ) % {
                "department": department,
                "item": item,
                "amount": amount,
                "baht": baht,
                "reason": values.get("reason_text", ""),
                "budget": values.get("budget_source", ""),
            }
        if type_code == "purchase_approval_memo":
            return _(
                "ด้วย  %(department)s  มีความประสงค์ขออนุมัติจัดซื้อ%(item)s  "
                "โดย%(method)s  เป็นจำนวนเงินทั้งสิ้น  %(amount)s  บาท  (%(baht)s)  "
                "รายละเอียดดังนี้"
            ) % {
                "department": department,
                "item": item,
                "method": method,
                "amount": amount,
                "baht": baht,
            }
        if type_code != "wa_committee_order":
            return ""
        return _(
            "ด้วย  %(department)s  มีความประสงค์จะดำเนินการจัดซื้อจัดจ้าง%(item)s  โดย%(method)s  "
            "เพื่อให้เป็นไปตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
            "พ.ศ. ๒๕๖๐  และตามกฎกระทรวงกำหนดวงเงินการจัดซื้อจัดจ้างพัสดุโดยวิธีเฉพาะเจาะจง  "
            "วงเงินการจัดซื้อจัดจ้างที่ไม่ทำข้อตกลงเป็นหนังสือ  "
            "และวงเงินการจัดซื้อจัดจ้างในการแต่งตั้งผู้ตรวจรับพัสดุ  พ.ศ. ๒๕๖๐  ข้อ  ๕  "
            "จึงขอแต่งตั้งคณะกรรมการตรวจรับพัสดุ  สำหรับการจัดซื้อ/จัดจ้าง%(item)s  "
            "โดย%(method)s  ประกอบด้วย"
        ) % {"department": department, "item": item, "method": method}
