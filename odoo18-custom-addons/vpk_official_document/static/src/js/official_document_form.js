/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { useEffect } from "@odoo/owl";
import { SignPdfViewerDialog } from "./sign_pdf_viewer_dialog";

export class OfficialDocumentFormController extends FormController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this._vpkDialogOpen = false;
        this._vpkLastOpenedId = false;
        useEffect(
            () => {
                this._vpkMaybeOpenSignViewer();
            },
            () => [this.model.root.resId]
        );
    }

    _vpkPdfAttachmentId() {
        const value = this.model.root.data.pdf_attachment_id;
        if (!value) {
            return false;
        }
        if (typeof value === "object") {
            return value.id || value[0] || false;
        }
        return value;
    }

    _vpkShouldAutoOpenViewer() {
        const data = this.model.root.data;
        if (!this.model.root.resId || !data) {
            return false;
        }
        if (data.state !== "to_approve" || !data.can_review) {
            return false;
        }
        return Boolean(this._vpkPdfAttachmentId());
    }

    _vpkMaybeOpenSignViewer() {
        const resId = this.model.root.resId;
        if (!resId || this._vpkLastOpenedId === resId) {
            return;
        }
        if (!this._vpkShouldAutoOpenViewer()) {
            return;
        }
        this._vpkLastOpenedId = resId;
        this._vpkOpenViewer();
    }

    _vpkOpenViewer({ force = false } = {}) {
        if (this._vpkDialogOpen && !force) {
            return;
        }
        const pdfId = this._vpkPdfAttachmentId();
        if (!pdfId) {
            this.notification.add(_t("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"), {
                type: "warning",
            });
            return;
        }
        const data = this.model.root.data;
        this._vpkDialogOpen = true;
        this.dialog.add(
            SignPdfViewerDialog,
            {
                title: data.name || _t("เอกสาร"),
                attachmentId: pdfId,
                resModel: this.props.resModel,
                resId: this.model.root.resId,
                canSign: Boolean(data.can_review),
                onSigned: async () => {
                    if (this.model.root.resId) {
                        await this.model.root.load();
                    }
                },
            },
            {
                onClose: () => {
                    this._vpkDialogOpen = false;
                },
            }
        );
    }

    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "action_open_sign_viewer") {
            this._vpkOpenViewer({ force: true });
            return false;
        }
        return super.beforeExecuteActionButton(clickParams);
    }
}

registry.category("views").add("vpk_official_document_form", {
    ...formView,
    Controller: OfficialDocumentFormController,
});
