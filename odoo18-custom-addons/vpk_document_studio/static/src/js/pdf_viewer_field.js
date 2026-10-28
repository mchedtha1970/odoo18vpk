/** @odoo-module **/

import { Component, onWillDestroy, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class PdfViewerField extends Component {
    static template = "vpk_document_studio.PdfViewerField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            viewerUrl: "",
            loading: false,
            generating: false,
            error: false,
        });
        this.objectUrl = null;
        this._loadFromProps(this.props);
        onWillUpdateProps((nextProps) => this._loadFromProps(nextProps));
        onWillDestroy(() => this._revoke());
    }

    hasPdf(props = this.props) {
        const data = props.record.data;
        return Boolean(data.pdf_filename || data[props.name]);
    }

    _revoke() {
        if (this.objectUrl) {
            URL.revokeObjectURL(this.objectUrl);
            this.objectUrl = null;
        }
    }

    async _loadFromProps(props) {
        if (!this.hasPdf(props) || !props.record.resId) {
            this._revoke();
            this.state.viewerUrl = "";
            this.state.error = false;
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        this.state.error = false;
        try {
            const filename = encodeURIComponent(props.record.data.pdf_filename || "document.pdf");
            const url = `/web/content/${props.record.resModel}/${props.record.resId}/${props.name}/${filename}`;
            const response = await fetch(url, { credentials: "same-origin" });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const blob = await response.blob();
            const pdfBlob =
                blob.type === "application/pdf"
                    ? blob
                    : new Blob([blob], { type: "application/pdf" });
            this._revoke();
            this.objectUrl = URL.createObjectURL(pdfBlob);
            this.state.viewerUrl = `/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
                this.objectUrl
            )}`;
        } catch (_err) {
            this.state.error = true;
            this.state.viewerUrl = "";
        } finally {
            this.state.loading = false;
        }
    }

    async generatePdf() {
        if (!this.props.record.resId || this.state.generating) {
            return;
        }
        this.state.generating = true;
        try {
            await this.orm.call(this.props.record.resModel, "action_generate_pdf", [
                this.props.record.resId,
            ]);
            await this.props.record.load();
            await this._loadFromProps(this.props);
        } catch (_err) {
            this.notification.add(_t("สร้างไฟล์ PDF ไม่สำเร็จ"), { type: "danger" });
        } finally {
            this.state.generating = false;
        }
    }
}

registry.category("fields").add("vpk_pdf_viewer", {
    component: PdfViewerField,
    supportedTypes: ["binary"],
});
