/** @odoo-module **/

import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";
import { registry } from "@web/core/registry";

export class VpkDocumentFileField extends BinaryField {
    static template = "vpk_document.DocumentFileField";

    openFile(ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        const id = this.props.record.resId;
        if (!id) {
            return;
        }
        window.open(`/vpk_document/open/${id}`, "_blank", "noopener");
    }

    getDownloadData() {
        const data = super.getDownloadData();
        const filename = this.downloadFilename();
        if (filename) {
            data.filename = filename;
            data.filename_field = filename;
        }
        return data;
    }

    downloadFilename() {
        const values = this.props.record.data;
        const original = values.file_name || "";
        const dot = original.lastIndexOf(".");
        const extension = dot > 0 ? original.slice(dot) : "";
        let stem = (values.name || "").trim();
        if (!stem) {
            return original;
        }
        stem = stem.replace(/[\\/:*?"<>|\r\n\t]/g, " ").replace(/\s+/g, " ").trim();
        if (!stem) {
            return original;
        }
        if (extension && !stem.toLowerCase().endsWith(extension.toLowerCase())) {
            return stem + extension;
        }
        return stem;
    }
}

registry.category("fields").add("vpk_document_file", {
    ...binaryField,
    component: VpkDocumentFileField,
});
