import logging

_logger = logging.getLogger("clear_pr_flow")
env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True))  # noqa: F821
cr = env.cr


def budget_snapshot():
    Line = env["budget.lines"].sudo()
    lines = Line.search([])
    return {
        "lines": len(lines),
        "pr_reserved": round(sum(lines.mapped("pr_reserved_amount")), 2),
        "po_committed": round(sum(lines.mapped("po_committed_amount")), 2),
        "available": round(sum(lines.mapped("pr_available_amount")), 2),
    }


def ids_of(model, domain):
    if model not in env:
        return []
    return env[model].sudo().with_context(active_test=False).search(domain).ids


def purge(model, ids, cancel_methods=()):
    if not ids or model not in env:
        return 0
    recs = env[model].sudo().with_context(active_test=False).browse(ids).exists()
    if not recs:
        return 0
    count = len(recs)
    for method in cancel_methods:
        if hasattr(recs, method):
            try:
                with cr.savepoint():
                    getattr(recs, method)()
            except Exception as exc:  # noqa: BLE001
                print("  cancel %s.%s failed: %s" % (model, method, str(exc)[:120]))
    try:
        with cr.savepoint():
            recs.with_context(force_delete=True, _force_unlink=True).unlink()
        print("  ORM deleted %s x%d" % (model, count))
        return count
    except Exception as exc:  # noqa: BLE001
        print("  ORM unlink %s failed (%s) -> SQL" % (model, str(exc)[:160]))
    table = env[model]._table
    with cr.savepoint():
        cr.execute("DELETE FROM mail_message WHERE model=%s AND res_id = ANY(%s)", (model, recs.ids))
        cr.execute("DELETE FROM mail_followers WHERE res_model=%s AND res_id = ANY(%s)", (model, recs.ids))
        cr.execute("DELETE FROM mail_activity WHERE res_model=%s AND res_id = ANY(%s)", (model, recs.ids))
        cr.execute("DELETE FROM ir_attachment WHERE res_model=%s AND res_id = ANY(%s)", (model, recs.ids))
        cr.execute('DELETE FROM "%s" WHERE id = ANY(%%s)' % table, (recs.ids,))
    print("  SQL deleted %s x%d" % (model, count))
    return count


print("BUDGET BEFORE", budget_snapshot())

pr_ids = ids_of("purchase.request", [])
prl_ids = ids_of("purchase.request.line", [("request_id", "in", pr_ids)])
req_ids = ids_of("purchase.requisition", [])
po_ids = ids_of("purchase.order", [])
print("PR", len(pr_ids), "PR lines", len(prl_ids), "requisitions", len(req_ids), "PO", len(po_ids))

official_ids = ids_of(
    "vpk.official.document",
    ["|", "|", ("request_id", "in", pr_ids), ("requisition_id", "in", req_ids), ("purchase_id", "in", po_ids)],
)
studio_ids = ids_of(
    "vpk.document.studio.document",
    ["|", ("request_id", "in", pr_ids), ("official_document_id", "in", official_ids)],
)
saraban_ids = ids_of(
    "saraban.document",
    ["|", ("purchase_request_id", "in", pr_ids), ("official_document_id", "in", official_ids)],
)
egp_doc_ids = ids_of(
    "purchase.requisition.egp.document",
    ["|", ("purchase_request_id", "in", pr_ids), ("requisition_id", "in", req_ids)],
)
committee_ids = ids_of(
    "procurement.committee",
    ["|", ("request_id", "in", pr_ids), ("requisition_id", "in", req_ids)],
)
appointment_ids = ids_of("procurement.committee.appointment", [("request_id", "in", pr_ids)])
wa_ids = ids_of("work.acceptance", [("purchase_id", "in", po_ids)])
contract_ids = ids_of("purchase.contract", [("requisition_id", "in", req_ids)])
picking_ids = ids_of("stock.picking", [("purchase_id", "in", po_ids)])
qc_ids = ids_of("vpk.stock.qc", [("picking_id", "in", picking_ids)])
guarantee_ids = ids_of("procurement.guarantee", ["|", ("contract_id", "in", contract_ids), ("purchase_order_id", "in", po_ids)])
tier_ids = []
if "tier.review" in env:
    for model, ids in (
        ("purchase.request", pr_ids),
        ("purchase.requisition", req_ids),
        ("purchase.order", po_ids),
        ("vpk.official.document", official_ids),
    ):
        tier_ids += ids_of("tier.review", [("model", "=", model), ("res_id", "in", ids)])

done_moves = ids_of("stock.move", [("picking_id", "in", picking_ids), ("state", "=", "done")])
if done_moves:
    raise SystemExit("ABORT: found %d done stock moves" % len(done_moves))
bill_lines = ids_of("account.move.line", [("purchase_line_id.order_id", "in", po_ids)])
if bill_lines:
    raise SystemExit("ABORT: found %d vendor bill lines" % len(bill_lines))

purge("tier.review", tier_ids)
purge("vpk.document.studio.document", studio_ids)
purge("saraban.document", saraban_ids)
purge("purchase.requisition.egp.document", egp_doc_ids)
purge("vpk.official.document", official_ids, ("action_cancel",))
purge("work.acceptance", wa_ids, ("button_cancel",))
purge("vpk.stock.qc", qc_ids, ("action_cancel",))
purge("stock.picking", picking_ids, ("action_cancel",))
purge("procurement.guarantee", guarantee_ids)
purge("purchase.contract", contract_ids, ("action_cancel",))
purge("purchase.order", po_ids, ("button_cancel",))
purge("procurement.committee", committee_ids)
purge("procurement.committee.appointment", appointment_ids)
purge("purchase.requisition", req_ids, ("action_cancel",))
purge("purchase.request", pr_ids, ("button_draft",))

cr.commit()
env.invalidate_all()
print("REMAINING", {
    "purchase.request": len(ids_of("purchase.request", [])),
    "purchase.requisition": len(ids_of("purchase.requisition", [])),
    "purchase.order": len(ids_of("purchase.order", [])),
    "vpk.official.document": len(ids_of("vpk.official.document", [])),
    "vpk.document.studio.document": len(ids_of("vpk.document.studio.document", [])),
    "work.acceptance": len(ids_of("work.acceptance", [])),
    "purchase.contract": len(ids_of("purchase.contract", [])),
})
print("BUDGET AFTER", budget_snapshot())
