/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

function many2oneId(value) {
    if (!value) {
        return false;
    }
    if (Array.isArray(value)) {
        return value[0] || false;
    }
    if (typeof value === "object") {
        return value.id || value.resId || value[0] || false;
    }
    return value;
}

function hasPdf(record) {
    const data = record?.data || {};
    if (data.has_pdf) {
        return true;
    }
    return Boolean(
        data.pdf_filename || data.pdf_file || many2oneId(data.pdf_attachment_id)
    );
}

export class VpkPdfIconField extends Component {
    static template = "vpk_official_document.PdfIconField";
    static props = {
        ...standardFieldProps,
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    }

    get hasFile() {
        const data = this.props.record?.data || {};
        const value = data[this.props.name];
        if (typeof value === "boolean") {
            return value || hasPdf(this.props.record);
        }
        if (value && typeof value === "object") {
            return Boolean(many2oneId(value)) || hasPdf(this.props.record);
        }
        return Boolean(value) || hasPdf(this.props.record);
    }

    get fileName() {
        const data = this.props.record?.data || {};
        return data.pdf_filename || "document.pdf";
    }

    async open(ev) {
        ev?.stopPropagation?.();
        ev?.preventDefault?.();
        if (!this.hasFile || !this.props.record.resId) {
            this.notification.add("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน", {
                type: "warning",
            });
            return;
        }
        const action = await this.orm.call(
            this.props.record.resModel,
            "action_open_pdf_viewer",
            [[this.props.record.resId]]
        );
        if (action) {
            await this.action.doAction(action);
        }
    }
}

const vpkPdfIconField = {
    component: VpkPdfIconField,
    supportedTypes: ["many2one", "char", "binary", "boolean"],
    additionalClasses: ["o_vpk_pdf_icon_field"],
    listViewWidth: 56,
    fieldDependencies: [
        { name: "has_pdf", type: "boolean" },
        { name: "pdf_filename", type: "char" },
        { name: "pdf_attachment_id", type: "many2one" },
    ],
    isEmpty: () => false,
};

registry.category("fields").add("vpk_pdf_icon", vpkPdfIconField);
registry.category("fields").add("list.vpk_pdf_icon", vpkPdfIconField);
registry.category("fields").add("kanban.vpk_pdf_icon", vpkPdfIconField);
