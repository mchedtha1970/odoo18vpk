# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import json

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command, Datetime
from odoo.tests import HttpCase, TransactionCase, tagged


def _tiny_pdf():
    return base64.b64encode(
        b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    )


@tagged("post_install", "-at_install")
class TestMobileApprovalApiService(TransactionCase):
    def setUp(self):
        super().setUp()
        self.password = "MobileApi@2569"
        self.user = self.env["res.users"].create(
            {
                "name": "ผู้อนุมัติมือถือ",
                "login": "mobile.approver",
                "password": self.password,
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("purchase.group_purchase_user").id,
                        ]
                    )
                ],
            }
        )
        self.definition = self.env["tier.definition"].create(
            {
                "name": "อนุมัติเอกสารราชการ (ทดสอบ API)",
                "model_id": self.env["ir.model"]._get("vpk.official.document").id,
                "review_type": "individual",
                "reviewer_id": self.user.id,
                "definition_type": "domain",
                "definition_domain": "[]",
                "sequence": 10,
                "approve_sequence": False,
                "company_id": False,
            }
        )
        self.document = self.env["vpk.official.document"].create(
            {
                "document_type": "wa_committee_order",
                "agency": "โรงพยาบาลวชิระภูเก็ต",
                "signer_name": self.user.name,
                "line_ids": [
                    Command.create(
                        {"name": "นายทดสอบ ประธาน", "role": "chairman"}
                    )
                ],
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "order.pdf",
                "datas": _tiny_pdf(),
                "res_model": self.document._name,
                "res_id": self.document.id,
                "mimetype": "application/pdf",
            }
        )
        self.document.write(
            {
                "pdf_file": _tiny_pdf(),
                "pdf_filename": "order.pdf",
                "pdf_attachment_id": attachment.id,
                "state": "to_approve",
            }
        )
        self.review = self.env["tier.review"].create(
            {
                "model": self.document._name,
                "res_id": self.document.id,
                "definition_id": self.definition.id,
                "requested_by": self.env.user.id,
                "status": "pending",
                "sequence": 1,
            }
        )
        self.review._compute_reviewer_ids()
        self.review._compute_can_review()
        self.env.flush_all()
        self.assertIn(self.user, self.review.reviewer_ids)
        self.assertTrue(self.review.can_review)
        self.assertTrue(
            self.env["tier.review"]
            .with_user(self.user)
            .search([("id", "=", self.review.id)])
        )
        self.service = (
            self.env["vpk.approval.api.service"].with_user(self.user)
        )

    def test_pending_list_contains_review(self):
        result = self.service.search_pending()
        ids = [item["id"] for item in result["items"]]
        self.assertIn(self.review.id, ids)
        item = next(row for row in result["items"] if row["id"] == self.review.id)
        self.assertTrue(item["has_pdf"])
        self.assertTrue(item["pdf_url"].endswith("/pdf"))
        self.assertEqual(item["document_id"], self.document.id)

    def test_pdf_bytes(self):
        pdf = self.service.get_pdf(self.review.id)
        self.assertTrue(pdf["content"].startswith(b"%PDF"))
        self.assertIn("order.pdf", pdf["filename"])

    def test_other_user_cannot_open(self):
        other = self.env["res.users"].create(
            {
                "name": "คนอื่น",
                "login": "mobile.other",
                "password": self.password,
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        try:
            self.env["vpk.approval.api.service"].with_user(other).get_review(
                self.review.id
            )
        except (AccessError, UserError):
            return
        self.fail("other user must not open this review")

    def test_validate_without_purchase_request_acl(self):
        request = self.env["purchase.request"].search([], limit=1)
        if not request:
            self.skipTest("No purchase request in test database")
        director = self.env["res.users"].create(
            {
                "name": "ผู้อำนวยการไม่มี ACL ใบขอซื้อ",
                "login": "mobile.director.no.pr",
                "password": self.password,
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        self.document.with_context(skip_validation_check=True).write(
            {"request_id": request.id}
        )
        self.definition.write({"reviewer_id": director.id})
        self.review._compute_reviewer_ids()
        self.review._compute_can_review()
        self.env.flush_all()
        self.assertIn(director, self.review.reviewer_ids)
        self.document.with_user(director)._validate_tier(self.review)
        self.assertEqual(self.review.status, "approved")
        self.assertEqual(self.document.state, "approved")

    def test_approved_list_and_pdf(self):
        pending = self.service.search_reviews(status="pending")
        self.assertIn(self.review.id, [item["id"] for item in pending["items"]])
        now = Datetime.now()
        self.review.write(
            {
                "status": "approved",
                "done_by": self.user.id,
                "reviewed_date": now,
            }
        )
        self.document.with_context(skip_validation_check=True).write(
            {"state": "approved"}
        )
        self.review._compute_can_review()
        self.env.flush_all()
        pending = self.service.search_reviews(status="pending")
        self.assertNotIn(self.review.id, [item["id"] for item in pending["items"]])
        approved = self.service.search_reviews(status="approved")
        ids = [item["id"] for item in approved["items"]]
        self.assertIn(self.review.id, ids)
        item = next(row for row in approved["items"] if row["id"] == self.review.id)
        self.assertEqual(item["status"], "approved")
        self.assertEqual(item["document_state"], "approved")
        self.assertFalse(item["can_sign"])
        self.assertTrue(item["pdf_url"])
        detail = self.service.get_review(self.review.id)
        self.assertEqual(detail["status"], "approved")
        pdf = self.service.get_pdf(self.review.id)
        self.assertTrue(pdf["content"].startswith(b"%PDF"))


@tagged("post_install", "-at_install")
class TestMobileApprovalApiHttp(HttpCase):
    readonly_enabled = False

    def test_health(self):
        response = self.url_open("/vpk/api/v1/mobile/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_approvals_require_auth(self):
        response = self.url_open(
            "/vpk/api/v1/mobile/approvals",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json().get("ok"))

    def test_login_and_list(self):
        password = "MobileApi@2569"
        user = self.env["res.users"].create(
            {
                "name": "ผู้อนุมัติมือถือ HTTP",
                "login": "mobile.http",
                "password": password,
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        bad = self.url_open(
            "/vpk/api/v1/mobile/auth/login",
            data=json.dumps({"login": user.login, "password": "wrong"}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(bad.status_code, 401)
        ok = self.url_open(
            "/vpk/api/v1/mobile/auth/login",
            data=json.dumps({"login": user.login, "password": password}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        data = ok.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["uid"], user.id)
        self.assertTrue(data.get("session_id"))
        self.assertEqual(data["session_id"], data["sid"])
        self.assertEqual(data["session_id"], ok.cookies.get("session_id"))
        listing = self.url_open("/vpk/api/v1/mobile/approvals")
        self.assertEqual(listing.status_code, 200, listing.text)
        payload = listing.json()
        self.assertTrue(payload["ok"])
        self.assertIn("items", payload)
        self.assertIn("count", payload)

        session_id = data["session_id"]
        self.opener.cookies.clear()
        without_cookie = self.url_open(
            "/vpk/api/v1/mobile/approvals",
            headers={"X-Openerp-Session-Id": session_id},
        )
        self.assertEqual(without_cookie.status_code, 200, without_cookie.text)
        self.assertTrue(without_cookie.json()["ok"])

        self.opener.cookies.clear()
        bearer = self.url_open(
            "/vpk/api/v1/mobile/approvals",
            headers={"Authorization": "Bearer %s" % session_id},
        )
        self.assertEqual(bearer.status_code, 200, bearer.text)
        self.assertTrue(bearer.json()["ok"])

    def test_jsonrpc_authenticate_returns_session_id(self):
        password = "MobileApi@2569"
        user = self.env["res.users"].create(
            {
                "name": "ผู้อนุมัติมือถือ RPC",
                "login": "mobile.rpc",
                "password": password,
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        response = self.url_open(
            "/web/session/authenticate",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "db": self.env.cr.dbname,
                        "login": user.login,
                        "password": password,
                    },
                    "id": 1,
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json().get("result") or {}
        self.assertEqual(result.get("uid"), user.id)
        self.assertTrue(result.get("session_id"))
        self.assertEqual(result["session_id"], response.cookies.get("session_id"))
