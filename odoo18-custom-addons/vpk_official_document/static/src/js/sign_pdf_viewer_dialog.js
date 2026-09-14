/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { SignatureDialog } from "@web/core/signature/signature_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillDestroy, onWillStart, useRef, useState } from "@odoo/owl";

export class SignPdfViewerDialog extends Component {
    static template = "vpk_official_document.SignPdfViewerDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: { type: String, optional: true },
        attachmentId: Number,
        resModel: String,
        resId: Number,
        canSign: { type: Boolean, optional: true },
        onSigned: { type: Function, optional: true },
        onRejected: { type: Function, optional: true },
    };
    static defaultProps = {
        title: _t("เอกสาร"),
        canSign: true,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.iframeRef = useRef("pdfFrame");
        this.state = useState({
            loading: true,
            error: false,
            reachedEnd: false,
            busy: false,
            objectUrl: "",
            viewerUrl: "",
        });
        this._fallbackTimer = null;
        this._pdfUnbind = [];

        onWillStart(async () => {
            await this._prepareViewer();
        });

        onWillDestroy(() => {
            if (this._fallbackTimer) {
                clearTimeout(this._fallbackTimer);
            }
            if (this.state.objectUrl) {
                URL.revokeObjectURL(this.state.objectUrl);
            }
            for (const unbind of this._pdfUnbind) {
                try {
                    unbind();
                } catch (_err) {
                    // PDF.js viewer already gone
                }
            }
        });
    }

    async _prepareViewer() {
        this.state.loading = true;
        this.state.error = false;
        try {
            const response = await fetch(`/web/content/${this.props.attachmentId}`, {
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
            this.state.viewerUrl = `/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
                this.state.objectUrl
            )}`;
        } catch (_err) {
            this.state.error = true;
            this.notification.add(_t("ไม่สามารถเปิดไฟล์ PDF ได้"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    get signEnabled() {
        return this.props.canSign && this.state.reachedEnd && !this.state.busy;
    }

    onIframeLoad() {
        this.state.loading = false;
        this._bindPdfEndDetection();
    }

    _bindPdfEndDetection() {
        const bind = () => {
            const iframe = this.iframeRef.el;
            const win = iframe && iframe.contentWindow;
            const app = win && win.PDFViewerApplication;
            if (!app) {
                this._fallbackTimer = setTimeout(() => {
                    this.state.reachedEnd = true;
                }, 2000);
                return;
            }
            const markIfAtEnd = () => {
                const count = app.pagesCount;
                if (!count) {
                    return;
                }
                if (count <= 1 || app.page >= count) {
                    this.state.reachedEnd = true;
                    return;
                }
                const container = win.document.getElementById("viewerContainer");
                if (
                    container &&
                    container.scrollTop + container.clientHeight >=
                        container.scrollHeight - 64
                ) {
                    this.state.reachedEnd = true;
                }
            };
            const onReady = () => {
                markIfAtEnd();
                if (!app.eventBus) {
                    return;
                }
                const onPage = () => markIfAtEnd();
                app.eventBus.on("pagechanging", onPage);
                app.eventBus.on("updateviewarea", onPage);
                app.eventBus.on("pagesloaded", onPage);
                this._pdfUnbind.push(() => {
                    app.eventBus.off("pagechanging", onPage);
                    app.eventBus.off("updateviewarea", onPage);
                    app.eventBus.off("pagesloaded", onPage);
                });
            };
            if (app.initializedPromise) {
                app.initializedPromise.then(onReady);
            } else {
                onReady();
            }
        };
        setTimeout(bind, 250);
    }

    async _callTier(methodName, onDone) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await this.orm.call(
                this.props.resModel,
                methodName,
                [[this.props.resId]]
            );
            this.props.close();
            if (result && typeof result === "object" && result.type) {
                await this.action.doAction(result, {
                    onClose: onDone,
                });
            } else if (onDone) {
                await onDone();
            }
        } catch (_err) {
            this.state.busy = false;
        }
    }

    async onSign() {
        if (!this.signEnabled) {
            this.notification.add(_t("เลื่อนเอกสารจนถึงหน้าสุดท้ายก่อนลงนาม"), {
                type: "warning",
            });
            return;
        }
        this.dialog.add(SignatureDialog, {
            defaultName: "",
            nameAndSignatureProps: {
                mode: "draw",
                displaySignatureRatio: 3,
                signatureType: "signature",
                noInputName: true,
            },
            uploadSignature: (payload) => {
                this._submitSignature(payload);
            },
        });
    }

    async _submitSignature({ signatureImage }) {
        const encoded = (signatureImage || "").split(",")[1];
        if (!encoded) {
            this.notification.add(_t("กรุณาลงลายเซ็น"), { type: "warning" });
            return;
        }
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await this.orm.call(
                this.props.resModel,
                "action_apply_signature",
                [[this.props.resId], encoded]
            );
            this.props.close();
            const afterSign = async () => {
                this.notification.add(_t("ลงนามแล้ว"), { type: "success" });
                if (this.props.onSigned) {
                    await this.props.onSigned();
                }
            };
            if (result && typeof result === "object" && result.type) {
                await this.action.doAction(result, {
                    onClose: afterSign,
                });
            } else {
                await afterSign();
            }
        } catch (_err) {
            this.state.busy = false;
        }
    }

    async onReject() {
        await this._callTier("reject_tier", this.props.onRejected || this.props.onSigned);
    }

    onClose() {
        this.props.close();
    }
}
