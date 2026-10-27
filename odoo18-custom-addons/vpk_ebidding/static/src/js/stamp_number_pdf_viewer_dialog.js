/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SignPdfViewerDialog } from "@vpk_official_document/js/sign_pdf_viewer_dialog";

const THAI_DIGITS = {
    0: "๐",
    1: "๑",
    2: "๒",
    3: "๓",
    4: "๔",
    5: "๕",
    6: "๖",
    7: "๗",
    8: "๘",
    9: "๙",
};

export class StampNumberPdfViewerDialog extends SignPdfViewerDialog {
    static template = "vpk_ebidding.StampNumberPdfViewerDialog";
    static props = {
        ...SignPdfViewerDialog.props,
        documentNumber: { type: String, optional: true },
        documentDate: { type: String, optional: true },
        numberBox: { type: Object, optional: true },
        dateBox: { type: Object, optional: true },
        hasNumberStamp: { type: Boolean, optional: true },
        hasDateStamp: { type: Boolean, optional: true },
        applyMethod: { type: String, optional: true },
    };
    static defaultProps = {
        ...SignPdfViewerDialog.defaultProps,
        title: _t("บันทึกเลขที่/วันที่เอกสาร"),
        canSign: false,
        applyMethod: "action_apply_document_stamps",
        hasNumberStamp: false,
        hasDateStamp: false,
    };

    setup() {
        super.setup();
        this.state.documentNumber = this.props.documentNumber || "";
        this.state.documentDate = this.props.documentDate || "";
        this.state.markTarget = "number";
        this.state.numberBox = this._fromServerBox(this.props.numberBox);
        this.state.dateBox = this._fromServerBox(this.props.dateBox);
        this.state.hasNumberStamp = Boolean(this.props.hasNumberStamp);
        this.state.hasDateStamp = Boolean(this.props.hasDateStamp);
        this.state.attachmentId = this.props.attachmentId;
    }

    get stampEnabled() {
        const hasNumber = Boolean((this.state.documentNumber || "").trim() && this.state.numberBox);
        const hasDate = Boolean((this.state.documentDate || "").trim() && this.state.dateBox);
        return (hasNumber || hasDate) && !this.state.busy;
    }

    _toThaiDigits(value) {
        return String(value || "").replace(/[0-9]/g, (digit) => THAI_DIGITS[digit] || digit);
    }

    _boxLabel(kind) {
        if (kind === "date") {
            return this._formatDateLabel(this.state.documentDate) || _t("กรอบวันที่เอกสาร");
        }
        return (this.state.documentNumber || "").trim() || _t("กรอบเลขที่เอกสาร");
    }

    _formatDateLabel(value) {
        if (!value) {
            return "";
        }
        const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
        if (!match) {
            return this._toThaiDigits(value);
        }
        const months = [
            "",
            "มกราคม",
            "กุมภาพันธ์",
            "มีนาคม",
            "เมษายน",
            "พฤษภาคม",
            "มิถุนายน",
            "กรกฎาคม",
            "สิงหาคม",
            "กันยายน",
            "ตุลาคม",
            "พฤศจิกายน",
            "ธันวาคม",
        ];
        const day = Number(match[3]);
        const month = Number(match[2]);
        const year = Number(match[1]) + 543;
        return this._toThaiDigits(`${day} ${months[month] || ""} ${year}`);
    }

    _fromServerBox(box) {
        if (!box || box.x_ratio === undefined || box.x_ratio === null) {
            return null;
        }
        const pageIndex = Number(box.page_index || 0);
        return {
            pageIndex,
            pageNumber: pageIndex + 1,
            xRatio: box.x_ratio,
            yRatio: box.y_ratio,
            wRatio: box.w_ratio,
            hRatio: box.h_ratio,
        };
    }

    _persistCurrentBox() {
        if (!this.state.markedBox) {
            return;
        }
        if (this.state.markTarget === "date") {
            this.state.dateBox = this.state.markedBox;
        } else {
            this.state.numberBox = this.state.markedBox;
        }
    }

    _injectMarkerStyles(doc) {
        super._injectMarkerStyles(doc);
        if (!doc || doc.getElementById("vpk-date-marker-style")) {
            return;
        }
        const style = doc.createElement("style");
        style.id = "vpk-date-marker-style";
        style.textContent = `
            .vpk-date-mark-overlay {
                border-color: #2563eb !important;
                background: rgba(37, 99, 235, 0.16) !important;
            }
        `;
        doc.head.appendChild(style);
    }

    _drawOverlay(doc, box, kind) {
        if (!box) {
            return;
        }
        const pageEl = doc.querySelector(`.page[data-page-number="${box.pageNumber}"]`);
        if (!pageEl) {
            return;
        }
        const overlay = doc.createElement("div");
        overlay.className =
            kind === "date"
                ? "vpk-sig-mark-overlay vpk-date-mark-overlay"
                : "vpk-sig-mark-overlay vpk-number-mark-overlay";
        overlay.style.left = `${(box.xRatio * 100).toFixed(2)}%`;
        overlay.style.top = `${(box.yRatio * 100).toFixed(2)}%`;
        overlay.style.width = `${(box.wRatio * 100).toFixed(2)}%`;
        overlay.style.height = `${(box.hRatio * 100).toFixed(2)}%`;
        overlay.style.fontFamily = '"TH Sarabun New", THSarabunNew, Sarabun, sans-serif';
        overlay.style.fontWeight = "700";
        overlay.style.color = "#111827";
        overlay.style.fontSize = "clamp(13px, 1.6vw, 22px)";
        overlay.style.letterSpacing = "0.02em";
        overlay.textContent = this._boxLabel(kind);
        pageEl.appendChild(overlay);
    }

    _renderMarkedOverlay() {
        const doc = this._getIframeDoc();
        if (!doc) {
            return;
        }
        this._injectMarkerStyles(doc);
        this._persistCurrentBox();
        for (const old of doc.querySelectorAll(".vpk-sig-mark-overlay")) {
            old.remove();
        }
        this._drawOverlay(doc, this.state.numberBox, "number");
        this._drawOverlay(doc, this.state.dateBox, "date");
    }

    async _prepareViewer() {
        this.state.loading = true;
        this.state.error = false;
        try {
            const attachmentId = this.state.attachmentId || this.props.attachmentId;
            const response = await fetch(`/web/content/${attachmentId}?unique=${Date.now()}`, {
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
            if (this.state.objectUrl) {
                URL.revokeObjectURL(this.state.objectUrl);
            }
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

    _applyServerResult(result) {
        if (!result) {
            return;
        }
        if (result.attachment_id) {
            this.state.attachmentId = result.attachment_id;
        }
        this.state.hasNumberStamp = Boolean(result.has_number_stamp);
        this.state.hasDateStamp = Boolean(result.has_date_stamp);
        if (!result.has_number_stamp) {
            this.state.numberBox = null;
        } else {
            this.state.numberBox = this._fromServerBox(result.number_box) || this.state.numberBox;
        }
        if (!result.has_date_stamp) {
            this.state.dateBox = null;
        } else {
            this.state.dateBox = this._fromServerBox(result.date_box) || this.state.dateBox;
        }
        this.state.markedBox = null;
        this.state.markingMode = false;
        this._syncMarkingModeClass();
    }

    _startMark(target) {
        this.state.markTarget = target;
        this.state.markedBox = target === "date" ? this.state.dateBox : this.state.numberBox;
        this.state.markingMode = true;
        this._syncMarkingModeClass();
        this._renderMarkedOverlay();
        this.notification.add(
            target === "date"
                ? _t("คลิกลากตีกรอบบนจุดที่ต้องการวางวันที่เอกสาร")
                : _t("คลิกลากตีกรอบบนจุดที่ต้องการวางเลขที่เอกสาร"),
            { type: "info" }
        );
    }

    onMarkNumber() {
        this._startMark("number");
    }

    onMarkDate() {
        this._startMark("date");
    }

    onToggleMarkMode() {
        if (this.state.markingMode) {
            this.state.markingMode = false;
            this._syncMarkingModeClass();
            return;
        }
        this._startMark(this.state.markTarget || "number");
    }

    onClearMarkedBox() {
        if (this.state.markTarget === "date") {
            this.state.dateBox = null;
        } else {
            this.state.numberBox = null;
        }
        this.state.markedBox = null;
        this.state.markingMode = false;
        this._syncMarkingModeClass();
        this._renderMarkedOverlay();
    }

    onDocumentNumberInput(ev) {
        this.state.documentNumber = ev.target.value;
        this._renderMarkedOverlay();
    }

    onDocumentDateInput(ev) {
        this.state.documentDate = ev.target.value;
        this._renderMarkedOverlay();
    }

    _toServerBox(box) {
        if (!box) {
            return null;
        }
        return {
            page_index: box.pageIndex,
            x_ratio: box.xRatio,
            y_ratio: box.yRatio,
            w_ratio: box.wRatio,
            h_ratio: box.hRatio,
        };
    }

    async onStampNumber() {
        const number = (this.state.documentNumber || "").trim();
        const dateValue = (this.state.documentDate || "").trim();
        if (!number && !dateValue) {
            this.notification.add(_t("กรุณาระบุเลขที่เอกสารหรือวันที่เอกสาร"), {
                type: "warning",
            });
            return;
        }
        if (number && !this.state.numberBox) {
            this.notification.add(_t("กรุณากำหนดกรอบตำแหน่งเลขที่เอกสารบนหน้าเอกสาร"), {
                type: "warning",
            });
            return;
        }
        if (dateValue && !this.state.dateBox) {
            this.notification.add(_t("กรุณากำหนดกรอบตำแหน่งวันที่เอกสารบนหน้าเอกสาร"), {
                type: "warning",
            });
            return;
        }
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call(this.props.resModel, this.props.applyMethod, [
                [this.props.resId],
                {
                    document_number: number,
                    number_box: this._toServerBox(this.state.numberBox),
                    document_date: dateValue,
                    date_box: this._toServerBox(this.state.dateBox),
                },
            ]);
            this.notification.add(_t("บันทึกเลขที่/วันที่เอกสารลงในไฟล์แล้ว"), {
                type: "success",
            });
            this.props.close();
            if (this.props.onSigned) {
                await this.props.onSigned();
            }
        } catch (_err) {
            this.state.busy = false;
        }
    }

    async _removeStamp(methodName, successMessage) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await this.orm.call(this.props.resModel, methodName, [
                [this.props.resId],
                true,
            ]);
            this._applyServerResult(result);
            await this._prepareViewer();
            this.notification.add(successMessage, { type: "success" });
        } catch (_err) {
            this.state.busy = false;
            return;
        }
        this.state.busy = false;
    }

    async onRemoveNumberStamp() {
        if (!this.state.hasNumberStamp) {
            this.notification.add(_t("ยังไม่มีเลขที่เอกสารที่ประทับบนไฟล์"), {
                type: "warning",
            });
            return;
        }
        await this._removeStamp("action_remove_number_stamp", _t("ลบเลขที่เอกสารออกจากไฟล์แล้ว"));
    }

    async onRemoveDateStamp() {
        if (!this.state.hasDateStamp) {
            this.notification.add(_t("ยังไม่มีวันที่เอกสารที่ประทับบนไฟล์"), {
                type: "warning",
            });
            return;
        }
        await this._removeStamp("action_remove_date_stamp", _t("ลบวันที่เอกสารออกจากไฟล์แล้ว"));
    }
}
