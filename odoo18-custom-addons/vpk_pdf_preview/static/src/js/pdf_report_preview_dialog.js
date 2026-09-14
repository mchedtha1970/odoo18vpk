/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { downloadReport } from "@web/webclient/actions/reports/utils";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillDestroy, onWillStart, useRef, useState } from "@odoo/owl";

export class PdfReportPreviewDialog extends Component {
    static template = "vpk_pdf_preview.PdfReportPreviewDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: { type: String, optional: true },
        reportUrl: String,
        action: Object,
        userContext: { type: Object, optional: true },
    };
    static defaultProps = {
        title: _t("Print Preview"),
        userContext: {},
    };

    setup() {
        this.notification = useService("notification");
        this.ui = useService("ui");
        this.iframeRef = useRef("pdfFrame");
        this.state = useState({
            loading: true,
            error: false,
            objectUrl: "",
            viewerUrl: "",
        });

        onWillStart(async () => {
            await this._prepareViewer();
        });

        onWillDestroy(() => {
            if (this.state.objectUrl) {
                URL.revokeObjectURL(this.state.objectUrl);
            }
        });
    }

    async _prepareViewer() {
        this.state.loading = true;
        this.state.error = false;
        try {
            const response = await fetch(this.props.reportUrl, {
                credentials: "same-origin",
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const blob = await response.blob();
            const pdfBlob =
                blob.type === "application/pdf"
                    ? blob
                    : new Blob([blob], { type: "application/pdf" });
            this.state.objectUrl = URL.createObjectURL(pdfBlob);
            // Use Odoo-bundled PDF.js viewer (toolbar: zoom, print, download, rotate, annotate)
            this.state.viewerUrl = `/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
                this.state.objectUrl
            )}`;
        } catch (_err) {
            this.state.error = true;
            this.notification.add(_t("ไม่สามารถสร้างตัวอย่าง PDF ได้"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    onIframeLoad() {
        this.state.loading = false;
    }

    async onDownload() {
        this.ui.block();
        try {
            const { success, message } = await downloadReport(
                rpc,
                this.props.action,
                "pdf",
                this.props.userContext || {}
            );
            if (message) {
                this.notification.add(message, {
                    sticky: true,
                    title: _t("รายงาน"),
                });
            }
            if (!success) {
                this.notification.add(_t("ไม่สามารถดาวน์โหลด PDF ได้"), {
                    type: "danger",
                });
            }
        } finally {
            this.ui.unblock();
        }
    }

    onClose() {
        this.props.close();
    }
}
