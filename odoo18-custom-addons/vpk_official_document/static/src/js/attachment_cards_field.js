/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { FileModel } from "@web/core/file_viewer/file_model";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { SignPdfViewerDialog } from "./sign_pdf_viewer_dialog";

function guessMimetype(name, mimetype) {
    if (mimetype && mimetype !== "application/octet-stream") {
        return mimetype;
    }
    const lower = (name || "").toLowerCase();
    if (lower.endsWith(".pdf") || name === "pdf_file") {
        return "application/pdf";
    }
    if (lower.endsWith(".docx") || name === "docx_file") {
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    }
    if (lower.endsWith(".doc")) {
        return "application/msword";
    }
    return mimetype || "";
}

function toFileModel(record) {
    const name = record.data.name || "";
    const mimetype = guessMimetype(name, record.data.mimetype || "");
    let extension = name.includes(".") ? name.split(".").pop() : "";
    if (!extension && mimetype === "application/pdf") {
        extension = "pdf";
    }
    return Object.assign(new FileModel(), {
        id: record.resId,
        name,
        filename: name,
        mimetype,
        type: "binary",
        extension,
    });
}

export class VpkAttachmentCardsField extends Component {
    static template = "vpk_official_document.AttachmentCardsField";
    static props = { ...standardFieldProps };

    setup() {
        this.fileViewer = useFileViewer();
        this.dialog = useService("dialog");
    }

    get files() {
        const relational = this.props.record.data[this.props.name];
        if (!relational || !relational.records) {
            return [];
        }
        return relational.records.map(toFileModel).filter((file) => file.id);
    }

    open(file) {
        const files = this.files;
        const current = files.find((item) => item.id === file.id) || file;
        const record = this.props.record;
        if (
            current.isPdf &&
            record &&
            record.resModel === "vpk.official.document" &&
            record.data.state === "to_approve" &&
            record.data.can_review
        ) {
            this.dialog.add(SignPdfViewerDialog, {
                title: record.data.name || current.displayName,
                attachmentId: current.id,
                resModel: record.resModel,
                resId: record.resId,
                canSign: true,
                onSigned: async () => {
                    await record.load();
                },
            });
            return;
        }
        if (current.isViewable) {
            this.fileViewer.open(current, files);
            return;
        }
        window.open(current.downloadUrl, "_blank");
    }
}

registry.category("fields").add("vpk_attachment_cards", {
    component: VpkAttachmentCardsField,
    supportedTypes: ["many2many"],
    isEmpty: () => false,
    relatedFields: [
        { name: "name", type: "char" },
        { name: "mimetype", type: "char" },
    ],
});
