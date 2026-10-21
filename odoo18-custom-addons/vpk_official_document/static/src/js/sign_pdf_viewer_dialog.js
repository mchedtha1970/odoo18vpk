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
        secretaryScreen: { type: Boolean, optional: true },
        onSigned: { type: Function, optional: true },
        onRejected: { type: Function, optional: true },
    };
    static defaultProps = {
        title: _t("เอกสาร"),
        canSign: true,
        secretaryScreen: false,
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
            checked: false,
            secretaryScreen: false,
            busy: false,
            objectUrl: "",
            viewerUrl: "",
            markingMode: false,
            markedBox: null,
        });
        this._fallbackTimer = null;
        this._pdfUnbind = [];
        this._dragState = null;

        onWillStart(async () => {
            await Promise.all([this._prepareViewer(), this._loadScreenState()]);
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

    async _loadScreenState() {
        this.state.secretaryScreen = Boolean(this.props.secretaryScreen);
        if (this.props.resModel !== "vpk.official.document" || !this.props.resId) {
            return;
        }
        const [doc] = await this.orm.read(this.props.resModel, [this.props.resId], [
            "vpk_secretary_can_screen",
            "vpk_secretary_screen_state",
        ]);
        if (!doc) {
            return;
        }
        this.state.secretaryScreen = Boolean(
            doc.vpk_secretary_can_screen || this.props.secretaryScreen
        );
        this.state.checked = doc.vpk_secretary_screen_state === "checked";
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
        return (
            this.props.canSign &&
            (this.state.reachedEnd || Boolean(this.state.markedBox)) &&
            !this.state.busy
        );
    }

    onIframeLoad() {
        this.state.loading = false;
        this._bindPdfEndDetection();
        this._bindPdfSignatureMarker();
    }

    _getIframeDoc() {
        const iframe = this.iframeRef.el;
        return iframe && iframe.contentDocument;
    }

    _injectMarkerStyles(doc) {
        if (!doc || doc.getElementById("vpk-sig-marker-style")) {
            return;
        }
        const style = doc.createElement("style");
        style.id = "vpk-sig-marker-style";
        style.textContent = `
            body.vpk-sig-marking-mode #viewerContainer .page {
                cursor: crosshair !important;
            }
            body.vpk-sig-marking-mode #viewerContainer .page .textLayer {
                pointer-events: none !important;
                user-select: none !important;
            }
            .vpk-sig-mark-overlay {
                position: absolute;
                border: 2.5px dashed #16a34a;
                background: rgba(22, 163, 74, 0.16);
                border-radius: 6px;
                z-index: 60;
                pointer-events: none;
                display: flex;
                align-items: center;
                justify-content: center;
                box-sizing: border-box;
                box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.85);
            }
            .vpk-sig-mark-label {
                background: #16a34a;
                color: #ffffff;
                font-family: sans-serif;
                font-size: 12px;
                font-weight: 600;
                padding: 2px 10px;
                border-radius: 999px;
                white-space: nowrap;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
            }
        `;
        doc.head.appendChild(style);
    }

    _syncMarkingModeClass() {
        const doc = this._getIframeDoc();
        if (!doc || !doc.body) {
            return;
        }
        this._injectMarkerStyles(doc);
        doc.body.classList.toggle("vpk-sig-marking-mode", Boolean(this.state.markingMode));
    }

    _renderMarkedOverlay() {
        const doc = this._getIframeDoc();
        if (!doc) {
            return;
        }
        this._injectMarkerStyles(doc);
        for (const old of doc.querySelectorAll(".vpk-sig-mark-overlay")) {
            old.remove();
        }
        const box = this.state.markedBox;
        if (!box) {
            return;
        }
        const pageEl = doc.querySelector(`.page[data-page-number="${box.pageNumber}"]`);
        if (!pageEl) {
            return;
        }
        const overlay = doc.createElement("div");
        overlay.className = "vpk-sig-mark-overlay";
        overlay.style.left = `${(box.xRatio * 100).toFixed(2)}%`;
        overlay.style.top = `${(box.yRatio * 100).toFixed(2)}%`;
        overlay.style.width = `${(box.wRatio * 100).toFixed(2)}%`;
        overlay.style.height = `${(box.hRatio * 100).toFixed(2)}%`;

        const label = doc.createElement("span");
        label.className = "vpk-sig-mark-label";
        label.textContent = "กรอบตำแหน่งลายเซ็น";
        overlay.appendChild(label);
        pageEl.appendChild(overlay);
    }

    _bindPdfSignatureMarker() {
        const setupMarker = () => {
            const doc = this._getIframeDoc();
            const iframe = this.iframeRef.el;
            const win = iframe && iframe.contentWindow;
            if (!doc || !win) {
                return;
            }
            this._injectMarkerStyles(doc);
            this._syncMarkingModeClass();

            const onMouseDown = (ev) => {
                if (!this.state.markingMode || ev.button !== 0) {
                    return;
                }
                const pageEl = ev.target && ev.target.closest && ev.target.closest(".page");
                if (!pageEl) {
                    return;
                }
                const pageNumber = parseInt(pageEl.dataset.pageNumber || "1", 10);
                const rect = pageEl.getBoundingClientRect();
                if (!rect.width || !rect.height) {
                    return;
                }
                ev.preventDefault();
                ev.stopPropagation();
                const startX = Math.max(0, Math.min(rect.width, ev.clientX - rect.left));
                const startY = Math.max(0, Math.min(rect.height, ev.clientY - rect.top));
                this._dragState = {
                    pageEl,
                    pageNumber,
                    rect,
                    startX,
                    startY,
                    curX: startX,
                    curY: startY,
                };
                this._updateDragPreview();
            };

            const onMouseMove = (ev) => {
                if (!this._dragState) {
                    return;
                }
                ev.preventDefault();
                const { rect } = this._dragState;
                this._dragState.curX = Math.max(0, Math.min(rect.width, ev.clientX - rect.left));
                this._dragState.curY = Math.max(0, Math.min(rect.height, ev.clientY - rect.top));
                this._updateDragPreview();
            };

            const onMouseUp = (ev) => {
                if (!this._dragState) {
                    return;
                }
                ev.preventDefault();
                const { pageNumber, rect, startX, startY, curX, curY } = this._dragState;
                this._dragState = null;

                const dragW = Math.abs(curX - startX);
                const dragH = Math.abs(curY - startY);
                let xRatio;
                let yRatio;
                let wRatio;
                let hRatio;

                if (dragW < 18 && dragH < 14) {
                    // Single click: place standard signature box centered at click point
                    wRatio = 0.24;
                    hRatio = 0.065;
                    xRatio = Math.max(0.02, Math.min(1 - wRatio - 0.02, startX / rect.width - wRatio / 2));
                    yRatio = Math.max(0.02, Math.min(1 - hRatio - 0.02, startY / rect.height - hRatio / 2));
                } else {
                    const left = Math.min(startX, curX);
                    const top = Math.min(startY, curY);
                    wRatio = Math.max(0.08, Math.min(0.95, dragW / rect.width));
                    hRatio = Math.max(0.03, Math.min(0.5, dragH / rect.height));
                    xRatio = Math.max(0, Math.min(1 - wRatio, left / rect.width));
                    yRatio = Math.max(0, Math.min(1 - hRatio, top / rect.height));
                }

                this.state.markedBox = {
                    pageIndex: Math.max(0, pageNumber - 1),
                    pageNumber,
                    xRatio,
                    yRatio,
                    wRatio,
                    hRatio,
                };
                this.state.markingMode = false;
                this.state.reachedEnd = true;
                this._syncMarkingModeClass();
                this._renderMarkedOverlay();
            };

            doc.addEventListener("mousedown", onMouseDown, true);
            doc.addEventListener("mousemove", onMouseMove, true);
            doc.addEventListener("mouseup", onMouseUp, true);
            this._pdfUnbind.push(() => {
                doc.removeEventListener("mousedown", onMouseDown, true);
                doc.removeEventListener("mousemove", onMouseMove, true);
                doc.removeEventListener("mouseup", onMouseUp, true);
            });

            const app = win.PDFViewerApplication;
            if (app && app.eventBus) {
                const onPageRendered = () => this._renderMarkedOverlay();
                app.eventBus.on("pagerendered", onPageRendered);
                this._pdfUnbind.push(() => {
                    app.eventBus.off("pagerendered", onPageRendered);
                });
            }
        };
        setTimeout(setupMarker, 300);
    }

    _updateDragPreview() {
        if (!this._dragState) {
            return;
        }
        const { pageNumber, rect, startX, startY, curX, curY } = this._dragState;
        const left = Math.min(startX, curX);
        const top = Math.min(startY, curY);
        const width = Math.max(24, Math.abs(curX - startX));
        const height = Math.max(16, Math.abs(curY - startY));
        this.state.markedBox = {
            pageIndex: Math.max(0, pageNumber - 1),
            pageNumber,
            xRatio: left / rect.width,
            yRatio: top / rect.height,
            wRatio: Math.min(1 - left / rect.width, width / rect.width),
            hRatio: Math.min(1 - top / rect.height, height / rect.height),
        };
        this._renderMarkedOverlay();
    }

    onToggleMarkMode() {
        this.state.markingMode = !this.state.markingMode;
        this._syncMarkingModeClass();
        if (this.state.markingMode) {
            this.notification.add(
                _t("คลิกลากตีกรอบ (หรือคลิก 1 ครั้ง) บนจุดที่ต้องการวางลายเซ็นในเอกสาร"),
                { type: "info" }
            );
        }
    }

    onClearMarkedBox() {
        this.state.markedBox = null;
        this.state.markingMode = false;
        this._syncMarkingModeClass();
        this._renderMarkedOverlay();
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

    async onMarkChecked() {
        if (!this.state.reachedEnd || this.state.busy) {
            this.notification.add(_t("เลื่อนเอกสารจนถึงหน้าสุดท้ายก่อนตรวจสอบ"), {
                type: "warning",
            });
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call(this.props.resModel, "action_secretary_mark_checked", [
                [this.props.resId],
            ]);
            this.state.checked = true;
            this.notification.add(_t("ตรวจสอบแล้ว"), { type: "success" });
        } catch (_err) {
            // ORM service already shows the error
        }
        this.state.busy = false;
    }

    async onSendDirector() {
        if (!this.state.checked) {
            this.notification.add(_t("กรุณากดตรวจสอบแล้ว ก่อนส่งผู้อำนวยการ"), {
                type: "warning",
            });
            return;
        }
        await this._callTier("action_secretary_send_director", async () => {
            this.notification.add(_t("ส่งผู้อำนวยการแล้ว"), { type: "success" });
            if (this.props.onSigned) {
                await this.props.onSigned();
            }
        });
    }

    async onSign() {
        if (!this.signEnabled) {
            this.notification.add(_t("เลื่อนเอกสารจนถึงหน้าสุดท้าย หรือกำหนดกรอบลายเซ็นก่อนลงนาม"), {
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
        const customBox = this.state.markedBox
            ? {
                  page_index: this.state.markedBox.pageIndex,
                  x_ratio: this.state.markedBox.xRatio,
                  y_ratio: this.state.markedBox.yRatio,
                  w_ratio: this.state.markedBox.wRatio,
                  h_ratio: this.state.markedBox.hRatio,
              }
            : null;
        try {
            const result = await this.orm.call(
                this.props.resModel,
                "action_apply_signature",
                [[this.props.resId], encoded, customBox]
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
