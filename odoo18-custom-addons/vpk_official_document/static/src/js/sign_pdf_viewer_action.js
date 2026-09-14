/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SignPdfViewerDialog } from "./sign_pdf_viewer_dialog";

function openSignPdfViewerAction(env, action) {
    const params = action.params || {};
    const attachmentId = Number(params.attachment_id);
    if (!attachmentId) {
        return;
    }
    return new Promise((resolve) => {
        env.services.dialog.add(
            SignPdfViewerDialog,
            {
                title: params.title || action.name || "",
                attachmentId,
                resModel: params.res_model,
                resId: Number(params.res_id),
                canSign: params.can_sign !== false,
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
    .add("vpk_official_document_sign_pdf_viewer", openSignPdfViewerAction);
