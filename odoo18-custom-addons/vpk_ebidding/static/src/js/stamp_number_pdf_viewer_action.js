/** @odoo-module **/

import { registry } from "@web/core/registry";
import { StampNumberPdfViewerDialog } from "./stamp_number_pdf_viewer_dialog";

function openStampNumberPdfViewerAction(env, action) {
    const params = action.params || {};
    const attachmentId = Number(params.attachment_id);
    if (!attachmentId) {
        return;
    }
    return new Promise((resolve) => {
        env.services.dialog.add(
            StampNumberPdfViewerDialog,
            {
                title: params.title || action.name || "",
                attachmentId,
                resModel: params.res_model,
                resId: Number(params.res_id),
                canSign: false,
                documentNumber: params.document_number || "",
                documentDate: params.document_date || "",
                numberBox: params.number_box || {},
                dateBox: params.date_box || {},
                hasNumberStamp: Boolean(params.has_number_stamp),
                hasDateStamp: Boolean(params.has_date_stamp),
                applyMethod: params.apply_method || "action_apply_document_stamps",
            },
            {
                onClose: () =>
                    resolve({ type: "ir.actions.client", tag: "soft_reload" }),
            }
        );
    });
}

registry
    .category("actions")
    .add("vpk_ebidding_stamp_number_pdf_viewer", openStampNumberPdfViewerAction);
