# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).


def align_official_document_saraban_numbers(env):
    """รายงานขออนุมัติใช้เลขจากใบขอซื้อ ส่วนเอกสารอื่นต้องขอเลขของตนเอง."""
    Document = env["vpk.official.document"].sudo()
    approvals = Document.search(
        [
            ("document_type", "=", "specific_method_approval"),
            ("request_id", "!=", False),
        ]
    )
    for approval in approvals:
        request = approval.request_id
        pr_doc = (
            request.saraban_document_id
            if "saraban_document_id" in request._fields
            else False
        )
        number = ""
        if "saraban_book_no_display" in request._fields:
            number = (request.saraban_book_no_display or "").strip()
        vals = {}
        if pr_doc and approval.saraban_document_id != pr_doc:
            vals["saraban_document_id"] = pr_doc.id
        if number and approval.saraban_book_no != number:
            vals["saraban_book_no"] = number
        if vals:
            approval.write(vals)

    others = Document.search(
        [
            ("document_type", "!=", "specific_method_approval"),
            ("saraban_book_no", "!=", False),
            ("request_id", "!=", False),
        ]
    )
    for doc in others:
        request = doc.request_id
        pr_no = ""
        if "saraban_book_no_display" in request._fields:
            pr_no = (request.saraban_book_no_display or "").strip()
        if not pr_no:
            continue
        if (doc.saraban_book_no or "").strip() != pr_no:
            continue
        linked = doc.saraban_document_id
        if linked and "purpose" in linked._fields and linked.purpose == "official_document":
            continue
        doc.write({"saraban_book_no": False, "saraban_document_id": False})


def post_init_hook(env):
    align_official_document_saraban_numbers(env)
