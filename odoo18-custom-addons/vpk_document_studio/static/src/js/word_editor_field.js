/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const FONTS = [
    "TH SarabunIT๙",
    "TH Sarabun New",
    "Angsana New",
    "Cordia New",
    "Tahoma",
    "Times New Roman",
    "Arial",
];
const SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72];
const COLORS = [
    "#000000", "#444444", "#666666", "#999999", "#cccccc", "#ffffff",
    "#7f0000", "#c00000", "#ff0000", "#ff9900", "#ffc000", "#ffff00",
    "#92d050", "#00b050", "#00b0f0", "#0070c0", "#002060", "#7030a0",
];
const SARABUN_PATH = "/l10n_th_base_utils/static/fonts/thai/THSarabunNew";
const STATE_COMMANDS = [
    "bold",
    "italic",
    "underline",
    "strikeThrough",
    "justifyLeft",
    "justifyCenter",
    "justifyRight",
    "justifyFull",
    "insertOrderedList",
    "insertUnorderedList",
];
const MOVABLE_BOX_SEL = ".o_vpk_we_fill_line, .o_vpk_we_field_box";

export class WordEditorField extends Component {
    static template = "vpk_document_studio.WordEditorField";
    static props = {
        ...standardFieldProps,
        showSave: { type: Boolean, optional: true },
        options: { type: Object, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.editableRef = useRef("editable");
        this.sourceRef = useRef("source");
        this.toolbarRef = useRef("toolbar");
        this.rulerRef = useRef("ruler");
        this.pageWrapRef = useRef("pageWrap");
        this.imageInputRef = useRef("imageInput");
        this.fonts = FONTS;
        this.sizes = SIZES;
        this.colors = COLORS;
        this.state = useState({
            menu: null,
            sourceMode: false,
            showTableGrid: false,
            inTable: false,
            dragOver: false,
            findBar: false,
            findText: "",
            replaceText: "",
            findMessage: "",
            tableRows: 3,
            tableCols: 3,
            lineCm: 6,
            lineStyle: "dotted",
            lineFieldCode: "",
            inFillLine: false,
            active: {},
            currentFont: "",
            currentSize: "",
            firstLineIndentCm: 0,
            leftIndentCm: 0,
            rightIndentCm: 0,
            rulerGuideCm: null,
            imgBox: null,
            lineBox: null,
            zoom: 100,
            lineDragging: false,
            canUndo: false,
            canRedo: false,
        });
        this.selectedImage = null;
        this.selectedLine = null;
        this.didDragLine = false;
        this.didPlaceCaretAfter = false;
        this.undoStack = [];
        this.redoStack = [];
        this.historyTimer = null;
        this.savedRange = null;
        this.findIndex = -1;
        this.commitTimer = null;
        this.lastValue = this.valueOf(this.props);

        const model = this.props.record.model;
        useBus(model.bus, "WILL_SAVE_URGENTLY", () => this.commitChanges());
        useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) =>
            detail.proms.push(this.commitChanges())
        );
        useExternalListener(window, "mousedown", (ev) => {
            if (this.state.menu && !this.toolbarRef.el?.contains(ev.target)) {
                this.state.menu = null;
            }
            if (
                this.selectedImage &&
                !ev.target.closest?.(".o_vpk_we_img_frame") &&
                !this.toolbarRef.el?.contains(ev.target) &&
                ev.target !== this.selectedImage
            ) {
                this.clearSelectedImage();
            }
            if (
                this.selectedLine &&
                !ev.target.closest?.(".o_vpk_we_line_frame") &&
                !this.toolbarRef.el?.contains(ev.target) &&
                !ev.target.closest?.(MOVABLE_BOX_SEL)
            ) {
                this.clearSelectedLine();
            }
        });
        useExternalListener(window, "resize", () => {
            this.updateImageOverlay();
            this.updateLineOverlay();
        });
        useExternalListener(document, "selectionchange", () => this.onSelectionChange());
        onMounted(() => {
            if (typeof ResizeObserver !== "undefined" && this.editableRef.el) {
                this.pageResizeObserver = new ResizeObserver(() => this.applyZoomLayout());
                this.pageResizeObserver.observe(this.editableRef.el);
            }
            this.setContent(this.lastValue);
            this.resetHistory(this.currentHtml());
        });
        onWillUpdateProps((nextProps) => {
            const value = this.valueOf(nextProps);
            if (value !== this.lastValue) {
                this.lastValue = value;
                this.setContent(value);
                this.clearSelectedImage();
                this.resetHistory(this.currentHtml());
            }
        });
        onWillUnmount(() => {
            this.pageResizeObserver?.disconnect();
            clearTimeout(this.commitTimer);
            clearTimeout(this.historyTimer);
        });
    }

    // ------------------------------------------------------------------
    // Value
    // ------------------------------------------------------------------

    valueOf(props) {
        const value = props.record.data[props.name];
        return value ? String(value) : "";
    }

    setContent(html) {
        if (this.editableRef.el) {
            this.editableRef.el.innerHTML = html || "<p><br></p>";
            this.promoteUnderlineCellsToFillLines();
            this.ensureEmptyFieldBoxes();
            this.ensureCaretAnchorsAroundBoxes();
        }
        if (this.sourceRef.el) {
            this.sourceRef.el.value = this.editableRef.el
                ? this.editableRef.el.innerHTML
                : html || "";
        }
    }

    promoteUnderlineCellsToFillLines() {
        const root = this.editableRef.el;
        if (!root) {
            return false;
        }
        let converted = false;
        for (const cell of root.querySelectorAll("td, th")) {
            if (cell.querySelector(".o_vpk_we_fill_line")) {
                continue;
            }
            const raw = cell.getAttribute("style") || "";
            const match = raw.match(/border-bottom\s*:\s*[^;]*(dotted|dashed|solid)/i);
            if (!match) {
                continue;
            }
            const lineStyle = match[1].toLowerCase() === "solid" ? "solid" : "dotted";
            const widthAttr = parseFloat(cell.getAttribute("width") || "");
            const rectW = cell.getBoundingClientRect().width;
            const px = rectW > 8 ? rectW : widthAttr > 0 ? widthAttr : 300;
            const cm = Math.max(1, Math.min(18, Math.round(this.pxToCm(px) * 10) / 10));
            const inner = cell.innerHTML.trim() || "&nbsp;";
            const span = document.createElement("span");
            span.className = "o_vpk_we_fill_line";
            span.dataset.lineCm = String(cm);
            span.dataset.lineStyle = lineStyle;
            span.setAttribute(
                "style",
                `display: inline-block; min-width: ${cm}cm; width: ${cm}cm; ` +
                    `border-bottom: 1px ${lineStyle} #000000; padding: 0 4px; ` +
                    `line-height: 1.05; text-align: left;`
            );
            span.innerHTML = inner;
            cell.innerHTML = "";
            cell.appendChild(span);
            span.after(document.createTextNode("\u200b"));
            cell.style.borderBottom = "none";
            cell.removeAttribute("width");
            converted = true;
        }
        if (!converted) {
            return false;
        }
        for (const table of root.querySelectorAll("table")) {
            if (!table.querySelector(".o_vpk_we_fill_line")) {
                continue;
            }
            table.querySelectorAll("colgroup, col").forEach((node) => node.remove());
            table.removeAttribute("width");
        }
        return true;
    }

    currentHtml() {
        if (this.state.sourceMode && this.sourceRef.el) {
            return this.sourceRef.el.value;
        }
        return this.editableRef.el ? this.editableRef.el.innerHTML : this.lastValue;
    }

    get showSave() {
        return Boolean(this.props.showSave || this.props.options?.showSave);
    }

    async commitChanges(force = false) {
        clearTimeout(this.commitTimer);
        if (this.props.readonly) {
            return;
        }
        const html = this.currentHtml();
        if (!force && html === this.lastValue) {
            return;
        }
        this.lastValue = html;
        await this.props.record.update({ [this.props.name]: html || false });
    }

    async saveRecord() {
        if (this.props.readonly) {
            return;
        }
        await this.commitChanges(true);
        await this.props.record.save({ reload: true });
        this.notification.add(_t("บันทึกเนื้อหาแล้ว"), { type: "success" });
    }

    onInput() {
        this.unwrapTypedCaretSinks();
        clearTimeout(this.commitTimer);
        this.commitTimer = setTimeout(() => this.commitChanges(), 400);
        clearTimeout(this.historyTimer);
        this.historyTimer = setTimeout(() => this.pushHistorySnapshot(), 350);
        this.updateImageOverlay();
        this.updateLineOverlay();
    }

    // ------------------------------------------------------------------
    // Undo / Redo History
    // ------------------------------------------------------------------

    resetHistory(initialHtml) {
        this.undoStack = [initialHtml || ""];
        this.redoStack = [];
        this.syncHistoryFlags();
    }

    syncHistoryFlags() {
        this.state.canUndo = this.undoStack.length > 1;
        this.state.canRedo = this.redoStack.length > 0;
    }

    pushHistorySnapshot() {
        const html = this.currentHtml();
        const top = this.undoStack[this.undoStack.length - 1];
        if (html !== top) {
            this.undoStack.push(html);
            if (this.undoStack.length > 80) {
                this.undoStack.shift();
            }
            this.redoStack = [];
            this.syncHistoryFlags();
        }
    }

    undoAction() {
        if (this.props.readonly) {
            return;
        }
        clearTimeout(this.historyTimer);
        this.pushHistorySnapshot();
        if (this.undoStack.length <= 1) {
            return;
        }
        const current = this.undoStack.pop();
        this.redoStack.push(current);
        const prev = this.undoStack[this.undoStack.length - 1];
        this.clearSelectedImage();
        this.setContent(prev);
        this.syncHistoryFlags();
        clearTimeout(this.commitTimer);
        this.commitTimer = setTimeout(() => this.commitChanges(), 200);
    }

    redoAction() {
        if (this.props.readonly || !this.redoStack.length) {
            return;
        }
        clearTimeout(this.historyTimer);
        const next = this.redoStack.pop();
        this.undoStack.push(next);
        this.clearSelectedImage();
        this.setContent(next);
        this.syncHistoryFlags();
        clearTimeout(this.commitTimer);
        this.commitTimer = setTimeout(() => this.commitChanges(), 200);
    }

    onEditorKeydown(ev) {
        if (ev.key === "Tab" && !this.props.readonly && !this.state.sourceMode) {
            ev.preventDefault();
            ev.stopPropagation();
            this.handleTabKey(ev.shiftKey);
            return;
        }
        const mod = ev.ctrlKey || ev.metaKey;
        if (mod && !ev.altKey && ev.key.toLowerCase() === "z") {
            ev.preventDefault();
            if (ev.shiftKey) {
                this.redoAction();
            } else {
                this.undoAction();
            }
            return;
        }
        if (mod && !ev.altKey && ev.key.toLowerCase() === "y") {
            ev.preventDefault();
            this.redoAction();
            return;
        }
        if (ev.key === "ArrowRight" && !ev.shiftKey && !ev.altKey && !mod) {
            const lineEl =
                this.currentFillLineElement() ||
                (this.selectedLine?.classList?.contains("o_vpk_we_fill_line")
                    ? this.selectedLine
                    : null);
            if (lineEl && !this.isPinnedBox(lineEl) && this.isCaretAtEndOf(lineEl)) {
                ev.preventDefault();
                this.placeCaretAfter(lineEl);
                return;
            }
        }
        if (
            this.selectedImage &&
            (ev.key === "Delete" || ev.key === "Backspace")
        ) {
            ev.preventDefault();
            this.pushHistorySnapshot();
            this.selectedImage.remove();
            this.clearSelectedImage();
            this.pushHistorySnapshot();
            this.onInput();
            return;
        }
        if (
            this.selectedLine?.classList?.contains("o_vpk_we_field_box") &&
            (ev.key === "Delete" || ev.key === "Backspace")
        ) {
            ev.preventDefault();
            this.pushHistorySnapshot();
            this.selectedLine.remove();
            this.clearSelectedLine();
            this.pushHistorySnapshot();
            this.onInput();
            return;
        }
        if (
            this.isFieldBox(this.selectedLine) &&
            ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(ev.key)
        ) {
            ev.preventDefault();
            const step = ev.shiftKey ? 0.2 : 0.05;
            const dx = ev.key === "ArrowLeft" ? -step : ev.key === "ArrowRight" ? step : 0;
            const dy = ev.key === "ArrowUp" ? -step : ev.key === "ArrowDown" ? step : 0;
            this.nudgeFieldBox(this.selectedLine, dx, dy);
        }
    }

    handleTabKey(isShift = false) {
        const editable = this.editableRef.el;
        if (!editable) {
            return;
        }
        editable.focus();
        const sel = document.getSelection();
        if (!sel || !sel.rangeCount) {
            return;
        }
        const range = sel.getRangeAt(0);
        let node = range.startContainer;
        if (node && node.nodeType === Node.TEXT_NODE) {
            node = node.parentElement;
        }

        // 1. Inside a table cell: move to next / previous cell like Word
        const cell = node?.closest?.("td, th");
        const table = cell?.closest?.("table");
        if (cell && table && this.isInEditor(table)) {
            const cells = Array.from(table.querySelectorAll("td, th"));
            const idx = cells.indexOf(cell);
            const target = cells[idx + (isShift ? -1 : 1)];
            if (target) {
                const newRange = document.createRange();
                newRange.selectNodeContents(target);
                newRange.collapse(true);
                sel.removeAllRanges();
                sel.addRange(newRange);
                this.savedRange = newRange.cloneRange();
                this.onSelectionChange();
            }
            return;
        }

        // 2. Inside a list item: indent / outdent list level
        if (node?.closest?.("li")) {
            this.exec(isShift ? "outdent" : "indent");
            return;
        }

        // 3. Regular paragraph: Shift+Tab removes a preceding tab or reduces first-line indent
        this.pushHistorySnapshot();
        if (isShift) {
            const prevNode =
                range.startContainer.nodeType === Node.TEXT_NODE && range.startOffset === 0
                    ? range.startContainer.previousSibling
                    : range.startContainer.childNodes?.[range.startOffset - 1];
            if (prevNode?.classList?.contains?.("o_vpk_we_tab")) {
                prevNode.remove();
                this.pushHistorySnapshot();
                this.onInput();
                return;
            }
            const blk = this.currentBlockElement();
            if (blk) {
                const cur = Math.max(0, (this.state.firstLineIndentCm || 0) - 1.25);
                this.state.firstLineIndentCm = Math.round(cur * 20) / 20;
                blk.style.textIndent = cur > 0 ? `${this.state.firstLineIndentCm}cm` : "";
                this.pushHistorySnapshot();
                this.onInput();
            }
            return;
        }

        // Insert a Word-equivalent tab stop spacing (8 non-breaking spaces) at the cursor
        document.execCommand(
            "insertHTML",
            false,
            '<span class="o_vpk_we_tab" data-vpk-tab="1">\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0</span>'
        );
        this.onSelectionChange();
        this.pushHistorySnapshot();
        this.onInput();
    }

    // ------------------------------------------------------------------
    // Image selection, alignment, resize & rotate
    // ------------------------------------------------------------------

    onEditorMouseDown(ev) {
        if (this.props.readonly || this.state.sourceMode || ev.button !== 0) {
            return;
        }
        if (ev.target.closest?.(".o_vpk_we_caret_sink")) {
            return;
        }
        const fieldEl = ev.target.closest?.(".o_vpk_we_field_box");
        if (fieldEl && this.isInEditor(fieldEl)) {
            const rect = fieldEl.getBoundingClientRect();
            const afterZone = Math.max(22, rect.width * 0.35);
            if (!this.isPinnedBox(fieldEl) && ev.clientX >= rect.right - afterZone) {
                ev.preventDefault();
                this.didPlaceCaretAfter = true;
                this.placeCaretAfter(fieldEl);
                return;
            }
            if (this.selectedLine !== fieldEl) {
                this.clearSelectedImage();
                this.selectLine(fieldEl);
            }
            const startX = ev.clientX;
            const startY = ev.clientY;
            const onMove = (moveEv) => {
                if (Math.hypot(moveEv.clientX - startX, moveEv.clientY - startY) < 6) {
                    return;
                }
                window.removeEventListener("mousemove", onMove);
                window.removeEventListener("mouseup", onCancel);
                moveEv.preventDefault();
                document.getSelection()?.removeAllRanges();
                this.startLineMove(moveEv);
            };
            const onCancel = () => {
                window.removeEventListener("mousemove", onMove);
                window.removeEventListener("mouseup", onCancel);
            };
            window.addEventListener("mousemove", onMove);
            window.addEventListener("mouseup", onCancel);
            return;
        }
        const lineEl = ev.target.closest?.(".o_vpk_we_fill_line");
        if (lineEl && this.isInEditor(lineEl)) {
            const rect = lineEl.getBoundingClientRect();
            const afterZone = Math.max(22, Math.min(40, rect.width * 0.18));
            if (!this.isPinnedBox(lineEl) && ev.clientX >= rect.right - afterZone) {
                ev.preventDefault();
                this.didPlaceCaretAfter = true;
                this.placeCaretAfter(lineEl);
                return;
            }
            this.selectLine(lineEl);
            return;
        }
        const lineBefore = this.fillLineLeftOfPoint(ev.clientX, ev.clientY);
        if (lineBefore && !this.isPinnedBox(lineBefore) && !this.clickIsOnForeignText(ev)) {
            ev.preventDefault();
            this.didPlaceCaretAfter = true;
            this.placeCaretAfter(lineBefore);
        }
    }

    onEditorClick(ev) {
        if (this.didDragLine) {
            this.didDragLine = false;
            ev.preventDefault();
            return;
        }
        if (this.didPlaceCaretAfter) {
            this.didPlaceCaretAfter = false;
            ev.preventDefault();
            return;
        }
        if (this.props.readonly || this.state.sourceMode) {
            return;
        }
        const img = ev.target.closest?.("img");
        if (img && this.isInEditor(img)) {
            ev.stopPropagation();
            this.clearSelectedLine();
            this.selectImage(img);
            return;
        }
        if (this.selectedImage) {
            this.clearSelectedImage();
        }
        let lineEl = ev.target.closest?.(MOVABLE_BOX_SEL);
        if (!lineEl) {
            const cell = ev.target.closest?.("td, th");
            if (cell && this.isInEditor(cell) && this.promoteUnderlineCellsToFillLines()) {
                lineEl = cell.querySelector(MOVABLE_BOX_SEL) || ev.target.closest?.(MOVABLE_BOX_SEL);
                this.onInput();
            }
        }
        if (lineEl && this.isInEditor(lineEl)) {
            this.selectLine(lineEl);
        } else if (this.selectedLine) {
            this.clearSelectedLine();
        }
    }

    isFieldBox(el) {
        return Boolean(el?.classList?.contains("o_vpk_we_field_box"));
    }

    isZwspNode(node) {
        return Boolean(
            node &&
                node.nodeType === Node.TEXT_NODE &&
                (node.textContent === "\u200b" || (node.textContent || "").includes("\u200b"))
        );
    }

    ensureEmptyFieldBoxes() {
        const root = this.editableRef.el;
        if (!root) {
            return;
        }
        for (const box of root.querySelectorAll(".o_vpk_we_field_box")) {
            const text = (box.textContent || "").replace(/[\u00a0\u200b\s]/g, "");
            if (text) {
                box.classList.remove("o_vpk_we_field_empty");
                continue;
            }
            box.textContent = "ว่าง";
            box.classList.add("o_vpk_we_field_empty");
        }
    }

    ensureCaretAfter(el) {
        return this.ensureCaretSinkAfter(el);
    }

    ensureCaretSinkAfter(el) {
        if (!el || !el.parentNode) {
            return null;
        }
        const next = el.nextSibling;
        if (next?.nodeType === Node.ELEMENT_NODE && next.classList?.contains("o_vpk_we_caret_sink")) {
            next.setAttribute("contenteditable", "true");
            if (!next.textContent) {
                next.textContent = "\u200b";
            }
            return next;
        }
        const sink = document.createElement("span");
        sink.className = "o_vpk_we_caret_sink";
        sink.setAttribute("contenteditable", "true");
        sink.textContent = "\u200b";
        if (this.isZwspNode(next)) {
            next.replaceWith(sink);
        } else {
            el.after(sink);
        }
        return sink;
    }

    unwrapTypedCaretSinks() {
        const root = this.editableRef.el;
        if (!root) {
            return;
        }
        const sel = document.getSelection();
        for (const sink of [...root.querySelectorAll(".o_vpk_we_caret_sink")]) {
            const text = (sink.textContent || "").replace(/\u200b/g, "");
            if (!text) {
                continue;
            }
            const node = document.createTextNode(text);
            const hadCaret = Boolean(sel?.rangeCount && sink.contains(sel.anchorNode));
            sink.replaceWith(node);
            if (hadCaret) {
                const range = document.createRange();
                range.setStart(node, node.textContent.length);
                range.collapse(true);
                sel.removeAllRanges();
                sel.addRange(range);
                this.savedRange = range.cloneRange();
            }
        }
    }

    ensureCaretAnchorsAroundBoxes() {
        const root = this.editableRef.el;
        if (!root) {
            return;
        }
        for (const el of root.querySelectorAll(".o_vpk_we_fill_line, .o_vpk_we_field_box")) {
            if (el.style.position === "absolute" || el.dataset.lineLeft) {
                continue;
            }
            this.ensureCaretSinkAfter(el);
            const prev = el.previousSibling;
            if (
                !this.isZwspNode(prev) &&
                !(prev && prev.nodeType === Node.TEXT_NODE && (prev.textContent || "").length) &&
                !(prev?.classList?.contains("o_vpk_we_caret_sink") || prev?.classList?.contains("o_vpk_we_field_box"))
            ) {
                el.before(document.createTextNode("\u200b"));
            }
        }
    }

    fillLineAt(clientX, clientY) {
        const stack = document.elementsFromPoint(clientX, clientY) || [];
        return (
            stack.find(
                (node) => node.classList?.contains?.("o_vpk_we_fill_line") && this.isInEditor(node)
            ) || null
        );
    }

    fieldBoxLeftOfPoint(clientX, clientY) {
        return this.boxLeftOfPoint(clientX, clientY, ".o_vpk_we_field_box", 8);
    }

    fillLineLeftOfPoint(clientX, clientY) {
        return this.boxLeftOfPoint(clientX, clientY, ".o_vpk_we_fill_line", 88);
    }

    boxLeftOfPoint(clientX, clientY, selector, maxGapPx) {
        const root = this.editableRef.el;
        if (!root) {
            return null;
        }
        let best = null;
        let bestRight = -Infinity;
        for (const box of root.querySelectorAll(selector)) {
            const rect = box.getBoundingClientRect();
            if (clientY < rect.top - 8 || clientY > rect.bottom + 8) {
                continue;
            }
            if (rect.right <= clientX + 2 && clientX <= rect.right + maxGapPx && rect.right > bestRight) {
                best = box;
                bestRight = rect.right;
            }
        }
        return best;
    }

    clickIsOnForeignText(ev) {
        if (ev.target?.closest?.(".o_vpk_we_fill_line, .o_vpk_we_field_box, .o_vpk_we_caret_sink")) {
            return false;
        }
        const range = this.rangeFromPoint(ev.clientX, ev.clientY);
        if (!range || range.startContainer.nodeType !== Node.TEXT_NODE) {
            return false;
        }
        return Boolean((range.startContainer.textContent || "").replace(/[\u00a0\u200b\s]/g, ""));
    }

    fieldsOverlappingFillLine(lineEl) {
        const page = this.editableRef.el;
        if (!page || !lineEl) {
            return [];
        }
        const lineRect = lineEl.getBoundingClientRect();
        const items = [];
        for (const box of page.querySelectorAll(".o_vpk_we_field_box")) {
            const rect = box.getBoundingClientRect();
            if (lineEl.contains(box)) {
                items.push({ box, left: rect.left });
                continue;
            }
            const overlapY = rect.bottom >= lineRect.top - 6 && rect.top <= lineRect.bottom + 6;
            const overlapX = rect.right >= lineRect.left && rect.left <= lineRect.right;
            if (overlapY && overlapX) {
                items.push({ box, left: rect.left });
            }
        }
        items.sort((a, b) => a.left - b.left);
        const seen = new Set();
        const boxes = [];
        for (const { box } of items) {
            if (seen.has(box)) {
                continue;
            }
            seen.add(box);
            boxes.push(box);
        }
        return boxes;
    }

    flattenFieldsIntoFillLine(lineEl) {
        const boxes = this.fieldsOverlappingFillLine(lineEl);
        for (const sink of [...lineEl.querySelectorAll(".o_vpk_we_caret_sink")]) {
            sink.remove();
        }
        for (const box of boxes) {
            this.clearFieldPin(box);
            lineEl.appendChild(box);
            this.ensureCaretSinkAfter(box);
        }
        return boxes;
    }

    clearFieldPin(fieldEl) {
        fieldEl.style.position = "";
        fieldEl.style.left = "";
        fieldEl.style.top = "";
        fieldEl.style.zIndex = "";
        fieldEl.style.margin = "";
        delete fieldEl.dataset.lineLeft;
        delete fieldEl.dataset.lineTop;
    }

    embedFieldInFillLine(fieldEl, lineEl, clientX) {
        if (!fieldEl || !lineEl || fieldEl === lineEl) {
            return false;
        }
        this.clearFieldPin(fieldEl);
        const lineRect = lineEl.getBoundingClientRect();
        const range = this.rangeFromPoint(
            clientX,
            lineRect.top + Math.min(10, Math.max(2, lineRect.height / 2))
        );
        if (range && lineEl.contains(range.commonAncestorContainer)) {
            range.insertNode(fieldEl);
        } else {
            lineEl.appendChild(fieldEl);
        }
        this.ensureCaretSinkAfter(fieldEl);
        return true;
    }

    makeFieldInline(fieldEl) {
        const rect = fieldEl.getBoundingClientRect();
        const range = this.rangeFromPoint(rect.left, rect.bottom - 2);
        this.clearFieldPin(fieldEl);
        if (
            range &&
            this.isInEditor(range.commonAncestorContainer) &&
            !fieldEl.contains(range.commonAncestorContainer)
        ) {
            range.insertNode(fieldEl);
        }
        this.ensureCaretSinkAfter(fieldEl);
    }

    placeCaretInNode(node, offset) {
        if (!node) {
            return;
        }
        const range = document.createRange();
        const max =
            node.nodeType === Node.TEXT_NODE
                ? node.textContent.length
                : node.childNodes.length;
        range.setStart(node, Math.max(0, Math.min(offset, max)));
        range.collapse(true);
        const sel = document.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        this.savedRange = range.cloneRange();
        this.clearSelectedLine();
        this.editableRef.el?.focus();
    }

    placeCaretBefore(el) {
        if (!el?.parentNode) {
            return;
        }
        let prev = el.previousSibling;
        if (prev?.classList?.contains("o_vpk_we_caret_sink")) {
            prev = prev.previousSibling;
        }
        if (!this.isZwspNode(prev)) {
            prev = document.createTextNode("\u200b");
            el.before(prev);
        }
        this.placeCaretInNode(prev, 0);
    }

    isPinnedBox(el) {
        return Boolean(
            el && (el.style.position === "absolute" || el.dataset.lineLeft || el.dataset.lineTop)
        );
    }

    makePinnedBoxInline(el) {
        if (!el || !this.isPinnedBox(el)) {
            return;
        }
        const rect = el.getBoundingClientRect();
        const range = this.rangeFromPoint(
            rect.left + Math.min(8, Math.max(1, rect.width / 2)),
            rect.top + Math.min(8, Math.max(2, rect.height / 2))
        );
        this.clearFieldPin(el);
        if (
            !range ||
            !this.isInEditor(range.commonAncestorContainer) ||
            el.contains(range.commonAncestorContainer)
        ) {
            return;
        }
        const host =
            range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
                ? range.commonAncestorContainer
                : range.commonAncestorContainer.parentElement;
        const insideLine = host?.closest?.(".o_vpk_we_fill_line");
        const insideField = host?.closest?.(".o_vpk_we_field_box");
        if (el.classList.contains("o_vpk_we_fill_line") && insideLine && insideLine !== el) {
            insideLine.after(el);
        } else if (insideField) {
            insideField.after(el);
        } else {
            range.insertNode(el);
        }
    }

    placeCaretAfter(el) {
        if (this.isFieldBox(el) && this.isPinnedBox(el)) {
            const rect = el.getBoundingClientRect();
            const line =
                this.fillLineAt(rect.right + 2, rect.top + rect.height / 2) ||
                this.fillLineAt(rect.left + 2, rect.top + rect.height / 2);
            if (line) {
                this.flattenFieldsIntoFillLine(line);
            } else {
                this.makePinnedBoxInline(el);
            }
        } else if (el?.classList?.contains("o_vpk_we_fill_line") && this.isPinnedBox(el)) {
            this.makePinnedBoxInline(el);
        }
        const next = el?.nextSibling;
        const afterSink = next?.classList?.contains("o_vpk_we_caret_sink") ? next.nextSibling : next;
        if (
            afterSink?.nodeType === Node.TEXT_NODE &&
            (afterSink.textContent || "").replace(/\u200b/g, "")
        ) {
            this.placeCaretInNode(afterSink, afterSink.textContent.length);
            return;
        }
        const sink = this.ensureCaretSinkAfter(el);
        if (!sink) {
            return;
        }
        if (sink.firstChild) {
            this.placeCaretInNode(sink.firstChild, sink.firstChild.textContent.length);
        } else {
            this.placeCaretInNode(sink, sink.childNodes.length);
        }
    }

    isCaretAtEndOf(el) {
        if (this.selectedLine === el) {
            const sel = document.getSelection();
            if (!sel || !sel.rangeCount) {
                return true;
            }
            const range = sel.getRangeAt(0);
            if (!el.contains(range.startContainer) && range.startContainer !== el) {
                return true;
            }
        }
        const sel = document.getSelection();
        if (!sel || !sel.rangeCount || !sel.isCollapsed) {
            return false;
        }
        const range = sel.getRangeAt(0);
        if (range.startContainer === el) {
            return range.startOffset >= el.childNodes.length;
        }
        if (range.startContainer.nodeType !== Node.TEXT_NODE || !el.contains(range.startContainer)) {
            return false;
        }
        if (range.startOffset < (range.startContainer.textContent || "").length) {
            return false;
        }
        let node = range.startContainer;
        while (node && node !== el) {
            if (node.nextSibling) {
                return false;
            }
            node = node.parentNode;
        }
        return true;
    }

    selectLine(lineEl) {
        this.selectedLine = lineEl;
        this.state.inFillLine = Boolean(lineEl) && !this.isFieldBox(lineEl);
        const cm = parseFloat(lineEl.dataset.lineCm || "0");
        if (cm > 0) {
            this.state.lineCm = cm;
        }
        if (lineEl.dataset.lineStyle) {
            this.state.lineStyle = lineEl.dataset.lineStyle;
        }
        this.updateLineOverlay();
    }

    clearSelectedLine() {
        this.selectedLine = null;
        this.state.lineBox = null;
        this.state.inFillLine = false;
    }

    updateLineOverlay() {
        const lineEl = this.selectedLine;
        const wrap = this.pageWrapRef.el;
        if (!lineEl || !wrap || !this.isInEditor(lineEl) || this.state.sourceMode) {
            this.state.lineBox = null;
            return;
        }
        const wrapRect = wrap.getBoundingClientRect();
        const rect = lineEl.getBoundingClientRect();
        const isField = this.isFieldBox(lineEl);
        const cm = parseFloat(lineEl.dataset.lineCm || "0") || Math.round(this.pxToCm(rect.width) * 10) / 10;
        const code = lineEl.dataset.fieldCode || "";
        this.state.lineBox = {
            left: rect.left - wrapRect.left,
            top: rect.top - wrapRect.top,
            width: Math.max(24, rect.width),
            height: Math.max(18, rect.height),
            cm: Math.round(cm * 10) / 10,
            kind: isField ? "field" : "line",
            label: isField ? `{{${code}}}` : `${Math.round(cm * 10) / 10} ซม.`,
        };
    }

    startLineResize(side, ev) {
        const lineEl = this.selectedLine;
        const wrap = this.pageWrapRef.el;
        if (!lineEl || !wrap || this.props.readonly || this.isFieldBox(lineEl)) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.pushHistorySnapshot();
        const startX = ev.clientX;
        const startW = lineEl.getBoundingClientRect().width || 120;
        const startMarginLeftPx =
            (parseFloat(window.getComputedStyle(lineEl).marginLeft) || 0) * this.zoomFactor;
        const pagePx = (this.editableRef.el?.getBoundingClientRect().width || 793.7);
        const pxPerCm = pagePx / 21.0;

        const onMove = (moveEv) => {
            const dx = moveEv.clientX - startX;
            if (side === "e") {
                const nextPx = Math.max(pxPerCm * 0.8, Math.min(pxPerCm * 18, startW + dx));
                const nextCm = Math.round((nextPx / pxPerCm) * 10) / 10;
                lineEl.dataset.lineCm = String(nextCm);
                lineEl.style.minWidth = `${nextCm}cm`;
                lineEl.style.width = `${nextCm}cm`;
                this.state.lineCm = nextCm;
            } else if (side === "w") {
                const nextPx = Math.max(pxPerCm * 0.8, Math.min(pxPerCm * 18, startW - dx));
                const nextCm = Math.round((nextPx / pxPerCm) * 10) / 10;
                lineEl.dataset.lineCm = String(nextCm);
                lineEl.style.minWidth = `${nextCm}cm`;
                lineEl.style.width = `${nextCm}cm`;
                this.state.lineCm = nextCm;
                if (lineEl.style.position === "absolute" || lineEl.dataset.lineLeft) {
                    const leftCm = parseFloat(lineEl.dataset.lineLeft || lineEl.style.left) || 0;
                    const nextLeft = Math.max(
                        0,
                        Math.round((leftCm + (startW - nextPx) / pxPerCm) * 100) / 100
                    );
                    lineEl.style.left = `${nextLeft}cm`;
                    lineEl.dataset.lineLeft = String(nextLeft);
                } else {
                    const nextMarginPx = Math.max(0, startMarginLeftPx + (startW - nextPx));
                    const nextMarginCm = Math.round((nextMarginPx / pxPerCm) * 20) / 20;
                    lineEl.style.marginLeft = nextMarginCm > 0 ? `${nextMarginCm}cm` : "";
                }
            }
            this.updateLineOverlay();
        };

        const onUp = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
            this.pushHistorySnapshot();
            this.onInput();
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    startLineMove(ev) {
        const lineEl = this.selectedLine;
        const wrap = this.pageWrapRef.el;
        if (!lineEl || !wrap || this.props.readonly) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.pushHistorySnapshot();
        const rect = lineEl.getBoundingClientRect();
        const grabX = ev.clientX - rect.left;
        const grabY = ev.clientY - rect.top;
        this.state.lineDragging = true;
        document.body.style.userSelect = "none";
        document.body.style.cursor = "grabbing";

        const pinFromBox = (box, altKey = false) => {
            const wrapRect = wrap.getBoundingClientRect();
            const pageRect = this.editableRef.el?.getBoundingClientRect();
            if (!box || !pageRect) {
                return false;
            }
            return this.pinFillLineOnPage(
                lineEl,
                box.left + wrapRect.left - pageRect.left,
                box.top + wrapRect.top - pageRect.top,
                { snap: this.isFieldBox(lineEl), altKey }
            );
        };

        pinFromBox(this.state.lineBox);

        const onMove = (moveEv) => {
            moveEv.preventDefault();
            const wrapRect = wrap.getBoundingClientRect();
            const left = moveEv.clientX - grabX - wrapRect.left;
            const top = moveEv.clientY - grabY - wrapRect.top;
            pinFromBox(
                {
                    ...(this.state.lineBox || {}),
                    left,
                    top,
                },
                moveEv.altKey
            );
            this.updateLineOverlay();
        };

        const onUp = (upEv) => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
            document.body.style.userSelect = "";
            document.body.style.cursor = "";
            this.state.lineDragging = false;
            this.didDragLine = true;
            const lineUnder =
                this.isFieldBox(lineEl) && !upEv.altKey
                    ? this.fillLineAt(upEv.clientX, upEv.clientY)
                    : null;
            if (lineUnder && lineUnder !== lineEl) {
                this.embedFieldInFillLine(lineEl, lineUnder, upEv.clientX);
            } else {
                pinFromBox(this.state.lineBox, upEv.altKey);
            }
            this.pushHistorySnapshot();
            this.onInput();
            this.selectLine(lineEl);
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    snapFieldTopToFillLine(fieldEl, leftPx, topPx) {
        const page = this.editableRef.el;
        if (!page || !fieldEl) {
            return topPx;
        }
        const pageRect = page.getBoundingClientRect();
        const fieldRect = fieldEl.getBoundingClientRect();
        const height = fieldRect.height || 18;
        const width = fieldRect.width || 40;
        const fieldLeft = leftPx;
        const fieldRight = leftPx + width;
        const fieldBottom = topPx + height;
        let best = null;
        for (const line of page.querySelectorAll(".o_vpk_we_fill_line")) {
            if (line === fieldEl) {
                continue;
            }
            const rect = line.getBoundingClientRect();
            const lineLeft = rect.left - pageRect.left;
            const lineRight = rect.right - pageRect.left;
            const lineBottom = rect.bottom - pageRect.top;
            const overlapsX = fieldRight > lineLeft - 12 && fieldLeft < lineRight + 12;
            if (!overlapsX) {
                continue;
            }
            const dy = Math.abs(fieldBottom - lineBottom);
            if (dy <= 18 && (!best || dy < best.dy)) {
                best = { dy, topPx: Math.max(0, lineBottom - height) };
            }
        }
        return best ? best.topPx : topPx;
    }

    pinFillLineOnPage(lineEl, leftPx, topPx, options = {}) {
        const page = this.editableRef.el;
        if (!page || !lineEl) {
            return false;
        }
        const snap = Boolean(options.snap) && !options.altKey;
        const next = lineEl.nextSibling;
        const trailing =
            this.isZwspNode(next) || next?.classList?.contains("o_vpk_we_caret_sink")
                ? next
                : null;
        const oldParent = lineEl.parentNode;
        if (lineEl.parentNode !== page) {
            if (!trailing) {
                this.ensureCaretSinkAfter(lineEl);
            }
            page.appendChild(lineEl);
        } else if (trailing) {
            trailing.remove();
        }
        if (
            oldParent &&
            oldParent !== page &&
            (oldParent.tagName === "TD" || oldParent.tagName === "TH") &&
            !(oldParent.textContent || "").replace(/[\u00a0\u200b\s]/g, "") &&
            !oldParent.querySelector("img, table, .o_vpk_we_fill_line, .o_vpk_we_field_box")
        ) {
            oldParent.appendChild(document.createTextNode("\u00a0"));
        }
        if (snap && this.isFieldBox(lineEl)) {
            topPx = this.snapFieldTopToFillLine(lineEl, leftPx, topPx);
        }
        const pagePx = page.getBoundingClientRect().width || 793.7;
        const pxPerCm = pagePx / 21.0;
        const leftCm = Math.max(0, Math.round((leftPx / pxPerCm) * 100) / 100);
        const topCm = Math.max(0, Math.round((topPx / pxPerCm) * 100) / 100);
        lineEl.style.position = "absolute";
        lineEl.style.left = `${leftCm}cm`;
        lineEl.style.top = `${topCm}cm`;
        lineEl.style.margin = "0";
        lineEl.style.zIndex = this.isFieldBox(lineEl) ? "4" : "3";
        lineEl.dataset.lineLeft = String(leftCm);
        lineEl.dataset.lineTop = String(topCm);
        return true;
    }

    nudgeFieldBox(fieldEl, dLeftCm, dTopCm) {
        const page = this.editableRef.el;
        if (!page || !fieldEl) {
            return;
        }
        this.pushHistorySnapshot();
        const pagePx = page.getBoundingClientRect().width || 793.7;
        const pxPerCm = pagePx / 21.0;
        const leftCm = Math.max(0, (parseFloat(fieldEl.dataset.lineLeft) || 0) + dLeftCm);
        const topCm = Math.max(0, (parseFloat(fieldEl.dataset.lineTop) || 0) + dTopCm);
        this.pinFillLineOnPage(fieldEl, leftCm * pxPerCm, topCm * pxPerCm, { snap: false });
        this.selectLine(fieldEl);
        this.pushHistorySnapshot();
        this.onInput();
    }

    startFieldVerticalMove(ev) {
        const fieldEl = this.selectedLine;
        const wrap = this.pageWrapRef.el;
        if (!this.isFieldBox(fieldEl) || !wrap || this.props.readonly) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.pushHistorySnapshot();
        const startY = ev.clientY;
        const startTop = this.state.lineBox?.top || 0;
        const startLeft = this.state.lineBox?.left || 0;
        this.state.lineDragging = true;
        document.body.style.userSelect = "none";
        document.body.style.cursor = "ns-resize";

        const onMove = (moveEv) => {
            moveEv.preventDefault();
            const wrapRect = wrap.getBoundingClientRect();
            const pageRect = this.editableRef.el?.getBoundingClientRect();
            if (!pageRect) {
                return;
            }
            const top = startTop + (moveEv.clientY - startY);
            this.pinFillLineOnPage(
                fieldEl,
                startLeft + wrapRect.left - pageRect.left,
                top + wrapRect.top - pageRect.top,
                { snap: true, altKey: moveEv.altKey }
            );
            this.updateLineOverlay();
        };

        const onUp = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
            document.body.style.userSelect = "";
            document.body.style.cursor = "";
            this.state.lineDragging = false;
            this.didDragLine = true;
            this.pushHistorySnapshot();
            this.onInput();
            this.selectLine(fieldEl);
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    selectImage(img) {
        this.selectedImage = img;
        const range = document.createRange();
        range.selectNode(img);
        const sel = document.getSelection();
        if (sel) {
            sel.removeAllRanges();
            sel.addRange(range);
        }
        this.savedRange = range.cloneRange();
        this.syncImageAlignmentState(img);
        this.updateImageOverlay();
    }

    clearSelectedImage() {
        this.selectedImage = null;
        this.state.imgBox = null;
    }

    deleteSelectedImage() {
        if (!this.selectedImage || this.props.readonly) {
            return;
        }
        this.pushHistorySnapshot();
        this.selectedImage.remove();
        this.clearSelectedImage();
        this.pushHistorySnapshot();
        this.onInput();
    }

    imageBlockParent(img) {
        const editable = this.editableRef.el;
        let block = img?.parentElement;
        while (
            block &&
            block !== editable &&
            !["P", "DIV", "TD", "TH", "LI", "H1", "H2", "H3", "H4", "CENTER"].includes(
                block.tagName
            )
        ) {
            block = block.parentElement;
        }
        if (!block || block === editable) {
            const p = document.createElement("p");
            img.replaceWith(p);
            p.appendChild(img);
            return p;
        }
        return block;
    }

    syncImageAlignmentState(img) {
        const block = this.imageBlockParent(img);
        const align = (
            block?.style?.textAlign ||
            block?.getAttribute("align") ||
            window.getComputedStyle(block).textAlign ||
            "left"
        ).toLowerCase();
        this.state.active = {
            ...this.state.active,
            justifyLeft: align === "left" || align === "start",
            justifyCenter: align === "center" || block?.tagName === "CENTER",
            justifyRight: align === "right" || align === "end",
            justifyFull: align === "justify",
        };
    }

    alignSelectedImage(command) {
        const img = this.selectedImage;
        if (!img || !this.isInEditor(img)) {
            return false;
        }
        if (this.isFloatingImage(img)) {
            this.setImageWrap("inline");
        }
        this.pushHistorySnapshot();
        let block = this.imageBlockParent(img);
        if (block.tagName === "CENTER") {
            const p = document.createElement("p");
            while (block.firstChild) {
                p.appendChild(block.firstChild);
            }
            block.replaceWith(p);
            block = p;
        }
        const map = {
            justifyLeft: "left",
            justifyCenter: "center",
            justifyRight: "right",
            justifyFull: "justify",
        };
        const align = map[command] || "left";
        block.setAttribute("align", align);
        block.style.textAlign = align;
        block.style.lineHeight = "";
        for (const frame of block.querySelectorAll('span[id^="Frame"]')) {
            if (!frame.textContent.trim()) {
                frame.remove();
            }
        }
        img.removeAttribute("align");
        img.style.display = "inline-block";
        img.style.float = "";
        this.syncImageAlignmentState(img);
        this.updateImageOverlay();
        this.pushHistorySnapshot();
        this.onInput();
        return true;
    }

    isFloatingImage(img) {
        return img?.dataset?.wrap === "front";
    }

    /** "front" = in front of text, anchored to its paragraph (moves with text). */
    setImageWrap(mode) {
        const img = this.selectedImage;
        if (!img || this.props.readonly || !this.isInEditor(img)) {
            return;
        }
        if ((mode === "front") === this.isFloatingImage(img)) {
            return;
        }
        this.pushHistorySnapshot();
        const block = this.imageBlockParent(img);
        if (mode === "front") {
            const blockRect = block.getBoundingClientRect();
            const rect = img.getBoundingClientRect();
            const left = this.pxToCm((rect.left - blockRect.left) / this.zoomFactor);
            const top = this.pxToCm((rect.top - blockRect.top) / this.zoomFactor);
            block.style.position = "relative";
            img.dataset.wrap = "front";
            img.style.position = "absolute";
            img.style.left = `${left.toFixed(2)}cm`;
            img.style.top = `${top.toFixed(2)}cm`;
            img.style.zIndex = "3";
            img.style.float = "";
            img.removeAttribute("align");
        } else {
            delete img.dataset.wrap;
            img.style.position = "";
            img.style.left = "";
            img.style.top = "";
            img.style.zIndex = "";
            if (!block.querySelector('img[data-wrap="front"]')) {
                block.style.position = "";
            }
        }
        this.state.imgBox = null;
        requestAnimationFrame(() => this.updateImageOverlay());
        this.pushHistorySnapshot();
        this.onInput();
    }

    startImageMove(ev) {
        const img = this.selectedImage;
        if (!img || this.props.readonly || !this.isFloatingImage(img)) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.pushHistorySnapshot();
        const startX = ev.clientX;
        const startY = ev.clientY;
        const startLeft = parseFloat(img.style.left) || 0;
        const startTop = parseFloat(img.style.top) || 0;
        document.body.style.userSelect = "none";

        const onMove = (moveEv) => {
            const dx = this.pxToCm((moveEv.clientX - startX) / this.zoomFactor);
            const dy = this.pxToCm((moveEv.clientY - startY) / this.zoomFactor);
            img.style.left = `${(startLeft + dx).toFixed(2)}cm`;
            img.style.top = `${(startTop + dy).toFixed(2)}cm`;
            this.updateImageOverlay();
        };

        const onUp = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
            document.body.style.userSelect = "";
            this.pushHistorySnapshot();
            this.onInput();
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    getImageRotation(img) {
        const deg = parseFloat(img?.dataset?.rotate || "0");
        return Number.isFinite(deg) ? deg : 0;
    }

    updateImageOverlay() {
        const img = this.selectedImage;
        const wrap = this.pageWrapRef.el;
        if (!img || !wrap || !this.isInEditor(img) || this.state.sourceMode) {
            this.state.imgBox = null;
            return;
        }
        const wrapRect = wrap.getBoundingClientRect();
        const width = (img.offsetWidth || img.clientWidth || 80) * this.zoomFactor;
        const height = (img.offsetHeight || img.clientHeight || 80) * this.zoomFactor;
        const rect = img.getBoundingClientRect();
        const cx = rect.left - wrapRect.left + rect.width / 2;
        const cy = rect.top - wrapRect.top + rect.height / 2;
        this.state.imgBox = {
            left: cx - width / 2,
            top: cy - height / 2,
            width,
            height,
            rotate: this.getImageRotation(img),
            floating: this.isFloatingImage(img),
        };
    }

    startImageResize(handle, ev) {
        const img = this.selectedImage;
        if (!img || this.props.readonly) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.pushHistorySnapshot();
        const startX = ev.clientX;
        const startY = ev.clientY;
        const startW = img.offsetWidth || img.naturalWidth || 100;
        const startH = img.offsetHeight || img.naturalHeight || 100;
        const ratio = startW / Math.max(1, startH);
        const corner = handle.length === 2;

        const onMove = (moveEv) => {
            const dx = (moveEv.clientX - startX) / this.zoomFactor;
            const dy = (moveEv.clientY - startY) / this.zoomFactor;
            let nextW = startW;
            let nextH = startH;
            if (handle.includes("e")) {
                nextW = Math.max(24, startW + dx);
            } else if (handle.includes("w")) {
                nextW = Math.max(24, startW - dx);
            }
            if (handle.includes("s")) {
                nextH = Math.max(24, startH + dy);
            } else if (handle.includes("n")) {
                nextH = Math.max(24, startH - dy);
            }
            if (corner) {
                nextH = Math.max(24, Math.round(nextW / ratio));
            }
            img.style.width = `${Math.round(nextW)}px`;
            img.style.height = `${Math.round(nextH)}px`;
            img.setAttribute("width", String(Math.round(nextW)));
            img.setAttribute("height", String(Math.round(nextH)));
            this.updateImageOverlay();
        };

        const onUp = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
            this.pushHistorySnapshot();
            this.onInput();
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    startImageRotate(ev) {
        const img = this.selectedImage;
        const wrap = this.pageWrapRef.el;
        if (!img || !wrap || this.props.readonly) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.pushHistorySnapshot();
        const rect = img.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;

        const onMove = (moveEv) => {
            const rad = Math.atan2(moveEv.clientY - cy, moveEv.clientX - cx);
            let deg = Math.round((rad * 180) / Math.PI + 90);
            if (moveEv.shiftKey) {
                deg = Math.round(deg / 15) * 15;
            }
            if (Math.abs(deg) <= 4) {
                deg = 0;
            }
            img.dataset.rotate = String(deg);
            img.style.transform = deg ? `rotate(${deg}deg)` : "";
            this.updateImageOverlay();
        };

        const onUp = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
            this.pushHistorySnapshot();
            this.onInput();
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    // ------------------------------------------------------------------
    // Page
    // ------------------------------------------------------------------

    get settings() {
        const data = this.props.record.data;
        const num = (key, fallback) =>
            typeof data[key] === "number" && data[key] > 0 ? data[key] : fallback;
        return {
            font: data.layout_font || "TH SarabunIT๙",
            size: num("layout_font_size", 16),
            top: num("layout_margin_top", 2.5),
            bottom: num("layout_margin_bottom", 2),
            left: num("layout_margin_left", 3),
            right: num("layout_margin_right", 2),
        };
    }

    get zoomFactor() {
        return (this.state.zoom || 100) / 100;
    }

    get zoomedWidthStyle() {
        // At 100% the page keeps its responsive width (max-width: 100%).
        if (this.state.zoom === 100) {
            return "";
        }
        return `width: ${(21 * this.zoomFactor).toFixed(3)}cm; max-width: none;`;
    }

    setZoom(percent) {
        const value = Math.max(50, Math.min(250, Math.round(Number(percent) || 100)));
        this.state.zoom = value;
        // overlays are measured in screen pixels; refresh them after layout
        requestAnimationFrame(() => {
            this.applyZoomLayout();
            this.updateImageOverlay();
            this.updateLineOverlay();
        });
    }

    applyZoomLayout() {
        // transform: scale() does not change the layout box, so size the wrapper
        const wrap = this.pageWrapRef.el;
        const page = this.editableRef.el;
        if (!wrap || !page) {
            return;
        }
        if (this.state.zoom === 100) {
            wrap.style.width = "";
            wrap.style.maxWidth = "";
            wrap.style.height = "";
            return;
        }
        wrap.style.width = `${(21 * this.zoomFactor).toFixed(3)}cm`;
        wrap.style.maxWidth = "none";
        wrap.style.height = page.offsetHeight ? `${page.offsetHeight * this.zoomFactor}px` : "";
    }

    zoomIn() {
        this.setZoom(Math.floor(this.state.zoom / 10) * 10 + 10);
    }

    zoomOut() {
        this.setZoom(Math.ceil(this.state.zoom / 10) * 10 - 10);
    }

    zoomReset() {
        this.setZoom(100);
    }

    zoomFitWidth() {
        const canvas = this.pageWrapRef.el?.closest(".o_vpk_we_canvas");
        if (!canvas) {
            return;
        }
        const pagePx = (21 / 2.54) * 96;
        const available = canvas.clientWidth - 40;
        this.setZoom(Math.floor((available / pagePx) * 100));
    }

    onZoomSelect(ev) {
        const value = ev.target.value;
        if (value === "fit") {
            this.zoomFitWidth();
        } else {
            this.setZoom(value);
        }
    }

    onCanvasWheel(ev) {
        if (!(ev.ctrlKey || ev.metaKey)) {
            return;
        }
        ev.preventDefault();
        if (ev.deltaY < 0) {
            this.zoomIn();
        } else if (ev.deltaY > 0) {
            this.zoomOut();
        }
    }

    get pageStyle() {
        const s = this.settings;
        const zoomStyle =
            this.state.zoom === 100
                ? []
                : [
                      `transform: scale(${this.zoomFactor})`,
                      "transform-origin: 0 0",
                      "margin: 0",
                      "width: 21cm",
                      "max-width: none",
                  ];
        return [
            ...zoomStyle,
            "position: relative",
            `padding: ${s.top}cm ${s.right}cm ${s.bottom}cm ${s.left}cm`,
            `font-family: "${s.font}", "TH Sarabun New", sans-serif`,
            `font-size: ${s.size}pt`,
        ].join("; ");
    }

    get placeholderFields() {
        const list = this.props.record.data.field_ids;
        if (!list || !list.records) {
            return [];
        }
        return list.records
            .map((rec) => ({ code: rec.data.code, name: rec.data.name }))
            .filter((field) => field.code);
    }

    // ------------------------------------------------------------------
    // Ruler (A4 = 21 cm)
    // ------------------------------------------------------------------

    get rulerMetrics() {
        const s = this.settings;
        const pageCm = 21.0;
        const leftMargin = Math.max(0.5, Math.min(8, s.left));
        const rightMargin = Math.max(0.5, Math.min(8, s.right));
        const rightEdge = pageCm - rightMargin;
        const ticks = [];
        for (let q = 0; q <= pageCm * 4; q++) {
            const cm = q * 0.25;
            const kind = q % 4 === 0 ? "major" : q % 2 === 0 ? "half" : "quarter";
            let label = "";
            if (kind === "major") {
                const dist = Math.round(Math.abs(cm - leftMargin));
                if (dist > 0 && cm >= 0.4 && cm <= pageCm - 0.4) {
                    label = String(dist);
                }
            }
            ticks.push({
                key: q,
                pct: (cm / pageCm) * 100,
                kind,
                label,
            });
        }
        const leftIndentX = Math.max(
            0,
            Math.min(pageCm, leftMargin + (this.state.leftIndentCm || 0))
        );
        const firstLineX = Math.max(
            0,
            Math.min(pageCm, leftIndentX + (this.state.firstLineIndentCm || 0))
        );
        const rightIndentX = Math.max(
            0,
            Math.min(pageCm, rightEdge - (this.state.rightIndentCm || 0))
        );
        return {
            pageCm,
            leftMargin,
            rightMargin,
            leftMarginPct: (leftMargin / pageCm) * 100,
            rightMarginPct: (rightMargin / pageCm) * 100,
            rightEdgePct: (rightEdge / pageCm) * 100,
            leftIndentPct: (leftIndentX / pageCm) * 100,
            firstLinePct: (firstLineX / pageCm) * 100,
            rightIndentPct: (rightIndentX / pageCm) * 100,
            guidePct:
                this.state.rulerGuideCm !== null
                    ? (this.state.rulerGuideCm / pageCm) * 100
                    : null,
            ticks,
        };
    }

    currentBlockElement() {
        const range = this.savedRange;
        if (!range || !this.isInEditor(range.commonAncestorContainer)) {
            return null;
        }
        let el = range.startContainer;
        if (el && el.nodeType === Node.TEXT_NODE) {
            el = el.parentElement;
        }
        const editable = this.editableRef.el;
        while (
            el &&
            el !== editable &&
            !["P", "DIV", "H1", "H2", "H3", "H4", "H5", "H6", "LI", "BLOCKQUOTE"].includes(
                el.tagName
            )
        ) {
            el = el.parentElement;
        }
        return el && el !== editable ? el : null;
    }

    pxToCm(px) {
        return (parseFloat(px) || 0) * (2.54 / 96);
    }

    syncParagraphIndents() {
        const block = this.currentBlockElement();
        if (!block) {
            this.state.firstLineIndentCm = 0;
            this.state.leftIndentCm = 0;
            this.state.rightIndentCm = 0;
            return;
        }
        const cs = window.getComputedStyle(block);
        this.state.leftIndentCm = Math.round(this.pxToCm(cs.marginLeft) * 20) / 20;
        this.state.rightIndentCm = Math.round(this.pxToCm(cs.marginRight) * 20) / 20;
        this.state.firstLineIndentCm = Math.round(this.pxToCm(cs.textIndent) * 20) / 20;
    }

    ensureBlockForRuler() {
        let block = this.currentBlockElement();
        if (block) {
            return block;
        }
        const editable = this.editableRef.el;
        if (!editable) {
            return null;
        }
        let first = editable.querySelector("p, div, h1, h2, h3, h4, li");
        if (!first) {
            first = document.createElement("p");
            while (editable.firstChild) {
                first.appendChild(editable.firstChild);
            }
            editable.appendChild(first);
        }
        return first;
    }

    startRulerDrag(kind, ev) {
        if (this.props.readonly || this.state.sourceMode) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        const rulerEl = this.rulerRef.el;
        if (!rulerEl) {
            return;
        }
        const rect = rulerEl.getBoundingClientRect();
        const pageCm = 21.0;
        const snap = (v) => Math.round(v * 8) / 8; // 0.125 cm steps
        const s = this.settings;
        const startFirstOffset = this.state.firstLineIndentCm || 0;
        const block =
            kind === "first" || kind === "hanging" || kind === "leftAll" || kind === "rightIndent"
                ? this.ensureBlockForRuler()
                : null;

        const onMove = (moveEv) => {
            const ratio = Math.max(0, Math.min(1, (moveEv.clientX - rect.left) / rect.width));
            const posCm = snap(ratio * pageCm);
            this.state.rulerGuideCm = posCm;

            if (kind === "leftMargin") {
                const nextLeft = Math.max(0.5, Math.min(8, posCm));
                this.props.record.update({
                    layout_margin_left: Math.round(nextLeft * 100) / 100,
                });
            } else if (kind === "rightMargin") {
                const nextRight = Math.max(0.5, Math.min(8, pageCm - posCm));
                this.props.record.update({
                    layout_margin_right: Math.round(nextRight * 100) / 100,
                });
            } else if (kind === "first" && block) {
                const base = s.left + (this.state.leftIndentCm || 0);
                const firstIndent = Math.max(-base + 0.25, Math.min(14, posCm - base));
                this.state.firstLineIndentCm = firstIndent;
                block.style.textIndent = `${firstIndent.toFixed(2)}cm`;
            } else if (kind === "hanging" && block) {
                const prevFirstAbs = s.left + (this.state.leftIndentCm || 0) + (this.state.firstLineIndentCm || 0);
                const nextLeftIndent = Math.max(0, Math.min(14, posCm - s.left));
                const nextFirstIndent = prevFirstAbs - (s.left + nextLeftIndent);
                this.state.leftIndentCm = nextLeftIndent;
                this.state.firstLineIndentCm = nextFirstIndent;
                block.style.marginLeft = `${nextLeftIndent.toFixed(2)}cm`;
                block.style.textIndent = `${nextFirstIndent.toFixed(2)}cm`;
            } else if (kind === "leftAll" && block) {
                const nextLeftIndent = Math.max(0, Math.min(14, posCm - s.left));
                this.state.leftIndentCm = nextLeftIndent;
                this.state.firstLineIndentCm = startFirstOffset;
                block.style.marginLeft = `${nextLeftIndent.toFixed(2)}cm`;
                block.style.textIndent = `${startFirstOffset.toFixed(2)}cm`;
            } else if (kind === "rightIndent" && block) {
                const rightEdge = pageCm - s.right;
                const nextRightIndent = Math.max(0, Math.min(14, rightEdge - posCm));
                this.state.rightIndentCm = nextRightIndent;
                block.style.marginRight = `${nextRightIndent.toFixed(2)}cm`;
            }
        };

        const onUp = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
            this.state.rulerGuideCm = null;
            if (block) {
                this.onInput();
            }
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    }

    // ------------------------------------------------------------------
    // Selection
    // ------------------------------------------------------------------

    isInEditor(node) {
        return Boolean(node && this.editableRef.el && this.editableRef.el.contains(node));
    }

    onSelectionChange() {
        const selection = document.getSelection();
        if (!selection || !selection.rangeCount) {
            return;
        }
        const range = selection.getRangeAt(0);
        if (!this.isInEditor(range.commonAncestorContainer)) {
            return;
        }
        this.savedRange = range.cloneRange();
        const active = {};
        for (const command of STATE_COMMANDS) {
            try {
                active[command] = document.queryCommandState(command);
            } catch {
                active[command] = false;
            }
        }
        this.state.active = active;
        let node = range.startContainer;
        if (node.nodeType === Node.TEXT_NODE) {
            node = node.parentElement;
        }
        if (node) {
            const style = window.getComputedStyle(node);
            this.state.currentFont = (style.fontFamily || "").split(",")[0].replace(/["']/g, "");
            const px = parseFloat(style.fontSize);
            this.state.currentSize = px ? String(Math.round((px * 72) / 96)) : "";
            this.state.inTable = Boolean(node.closest && node.closest("table"));
            const lineEl = node.closest ? node.closest(".o_vpk_we_fill_line") : null;
            const fieldEl = node.closest ? node.closest(".o_vpk_we_field_box") : null;
            this.state.inFillLine = Boolean(lineEl);
            if (lineEl) {
                this.selectLine(lineEl);
            } else if (fieldEl) {
                this.selectLine(fieldEl);
            } else if (this.selectedLine && !this.isFieldBox(this.selectedLine)) {
                this.clearSelectedLine();
            }
            this.syncParagraphIndents();
        } else {
            this.state.inTable = false;
            this.state.inFillLine = false;
        }
    }

    currentFillLineElement() {
        if (this.selectedLine && this.isInEditor(this.selectedLine)) {
            return this.selectedLine.classList.contains("o_vpk_we_fill_line")
                ? this.selectedLine
                : null;
        }
        const range = this.savedRange;
        if (!range || !this.isInEditor(range.commonAncestorContainer)) {
            return null;
        }
        let el = range.startContainer;
        if (el && el.nodeType === Node.TEXT_NODE) {
            el = el.parentElement;
        }
        return el && el.closest ? el.closest(".o_vpk_we_fill_line") : null;
    }

    currentTableContext() {
        const range = this.savedRange;
        if (!range || !this.isInEditor(range.commonAncestorContainer)) {
            return {};
        }
        let el = range.startContainer;
        if (el && el.nodeType === Node.TEXT_NODE) {
            el = el.parentElement;
        }
        if (!el || !el.closest) {
            return {};
        }
        const cell = el.closest("td, th");
        const row = el.closest("tr");
        const table = el.closest("table");
        return { cell, row, table };
    }

    restoreSelection() {
        const editable = this.editableRef.el;
        if (!editable) {
            return;
        }
        editable.focus();
        if (this.savedRange) {
            const selection = document.getSelection();
            selection.removeAllRanges();
            selection.addRange(this.savedRange);
        }
    }

    // ------------------------------------------------------------------
    // Commands
    // ------------------------------------------------------------------

    exec(command, value = null) {
        if (this.props.readonly || this.state.sourceMode) {
            return;
        }
        if (command === "undo") {
            this.undoAction();
            return;
        }
        if (command === "redo") {
            this.redoAction();
            return;
        }
        if (
            this.selectedImage &&
            ["justifyLeft", "justifyCenter", "justifyRight", "justifyFull"].includes(command)
        ) {
            this.alignSelectedImage(command);
            return;
        }
        this.pushHistorySnapshot();
        this.restoreSelection();
        document.execCommand("styleWithCSS", false, true);
        document.execCommand(command, false, value);
        if (["justifyLeft", "justifyCenter", "justifyRight", "justifyFull"].includes(command)) {
            const blk = this.currentBlockElement();
            if (blk) {
                const map = {
                    justifyLeft: "left",
                    justifyCenter: "center",
                    justifyRight: "right",
                    justifyFull: "justify",
                };
                blk.setAttribute("align", map[command]);
                blk.style.textAlign = map[command];
            }
        }
        this.state.menu = null;
        this.onSelectionChange();
        this.pushHistorySnapshot();
        this.onInput();
    }

    toggleMenu(name) {
        this.state.menu = this.state.menu === name ? null : name;
    }

    setFont(font) {
        this.exec("fontName", font);
    }

    setFontSize(size) {
        if (this.props.readonly || this.state.sourceMode) {
            return;
        }
        this.restoreSelection();
        document.execCommand("styleWithCSS", false, true);
        document.execCommand("fontSize", false, "7");
        const editable = this.editableRef.el;
        for (const el of editable.querySelectorAll('[style*="xxx-large"], font[size="7"]')) {
            el.removeAttribute("size");
            el.style.fontSize = `${size}pt`;
        }
        this.state.menu = null;
        this.onSelectionChange();
        this.onInput();
    }

    async copy() {
        this.exec("copy");
    }

    cut() {
        this.exec("cut");
    }

    async paste() {
        try {
            const text = await navigator.clipboard.readText();
            this.exec("insertText", text);
        } catch {
            this.notification.add(_t("เบราว์เซอร์ไม่อนุญาตให้วางจากปุ่ม กรุณากด Ctrl+V"), {
                type: "warning",
            });
        }
    }

    insertTable() {
        const rows = Math.max(1, Math.min(50, parseInt(this.state.tableRows) || 1));
        const cols = Math.max(1, Math.min(20, parseInt(this.state.tableCols) || 1));
        const cell =
            '<td style="border: 1px solid #000000; padding: 2px 6px; vertical-align: top;"><br></td>';
        const row = `<tr>${cell.repeat(cols)}</tr>`;
        const html =
            '<table style="width: 100%; border-collapse: collapse;" border="1" cellpadding="4">' +
            `<tbody>${row.repeat(rows)}</tbody></table><p><br></p>`;
        this.exec("insertHTML", html);
    }

    deleteCurrentColumn() {
        const { cell, table } = this.currentTableContext();
        if (!cell || !table) {
            this.notification.add(_t("กรุณาคลิกในช่องตารางที่ต้องการลบคอลัมน์ก่อน"), {
                type: "warning",
            });
            return;
        }
        const colIndex = cell.cellIndex;
        for (const tr of Array.from(table.rows)) {
            if (tr.cells[colIndex]) {
                tr.deleteCell(colIndex);
            }
        }
        const colgroup = table.querySelector("colgroup");
        if (colgroup && colgroup.children[colIndex]) {
            colgroup.children[colIndex].remove();
        }
        const hasAnyCells = Array.from(table.rows).some((tr) => tr.cells.length > 0);
        if (!hasAnyCells) {
            table.remove();
            this.state.inTable = false;
        }
        this.state.menu = null;
        this.onInput();
    }

    deleteCurrentRow() {
        const { row, table } = this.currentTableContext();
        if (!row || !table) {
            this.notification.add(_t("กรุณาคลิกในแถวตารางที่ต้องการลบก่อน"), {
                type: "warning",
            });
            return;
        }
        row.remove();
        if (!table.rows.length) {
            table.remove();
            this.state.inTable = false;
        }
        this.state.menu = null;
        this.onInput();
    }

    unwrapCurrentTable() {
        const { table } = this.currentTableContext();
        if (!table) {
            this.notification.add(_t("กรุณาคลิกในตารางที่ต้องการเอาออกก่อน"), {
                type: "warning",
            });
            return;
        }
        const frag = document.createDocumentFragment();
        for (const tr of Array.from(table.rows)) {
            const cellTexts = [];
            for (const td of Array.from(tr.cells)) {
                const txt = (td.innerText || td.textContent || "").trim();
                if (txt) {
                    cellTexts.push(txt.replace(/\s*\n+\s*/g, " "));
                }
            }
            if (cellTexts.length) {
                const p = document.createElement("p");
                p.textContent = cellTexts.join("        ");
                frag.appendChild(p);
            }
        }
        table.replaceWith(frag);
        this.state.inTable = false;
        this.state.menu = null;
        this.onInput();
    }

    deleteCurrentTable() {
        const { table } = this.currentTableContext();
        if (!table) {
            this.notification.add(_t("กรุณาคลิกในตารางที่ต้องการลบก่อน"), {
                type: "warning",
            });
            return;
        }
        table.remove();
        this.state.inTable = false;
        this.state.menu = null;
        this.onInput();
    }

    toggleTableGrid() {
        this.state.showTableGrid = !this.state.showTableGrid;
        this.state.menu = null;
    }

    insertPageBreak() {
        this.exec(
            "insertHTML",
            '<p class="o_vpk_page_break" style="page-break-before: always;"><br></p>'
        );
    }

    // ------------------------------------------------------------------
    // Fill Lines (เส้นประ / เส้นทึบสำหรับวางฟิลด์บนเส้น)
    // ------------------------------------------------------------------

    buildFillLineSpanHtml(cm, lineStyle, innerText = "\u00a0") {
        const widthCm = Math.max(1, Math.min(18, parseFloat(cm) || 6));
        const bStyle = lineStyle === "solid" ? "solid" : "dotted";
        const content = innerText || "\u00a0";
        return (
            `<span class="o_vpk_we_fill_line" data-line-cm="${widthCm}" data-line-style="${bStyle}" ` +
            `style="display: inline-block; min-width: ${widthCm}cm; border-bottom: 1px ${bStyle} #000000; ` +
            `padding: 0 4px; line-height: 1.05; text-align: left;">${content}</span>&#8203;`
        );
    }

    insertFillLine(presetCm = null) {
        if (this.props.readonly || this.state.sourceMode) {
            return;
        }
        const cm = presetCm !== null ? presetCm : parseFloat(this.state.lineCm) || 6;
        const lineStyle = this.state.lineStyle || "dotted";
        const code = (this.state.lineFieldCode || "").trim();
        this.pushHistorySnapshot();
        this.restoreSelection();
        const sel = document.getSelection();
        let selectedText = "";
        if (sel && sel.rangeCount && !sel.getRangeAt(0).collapsed) {
            selectedText = sel.toString().trim();
        }
        const inner = code ? `{{${code}}}` : selectedText || "\u00a0";
        const html = this.buildFillLineSpanHtml(cm, lineStyle, inner);
        document.execCommand("insertHTML", false, html);
        this.ensureCaretAnchorsAroundBoxes();
        this.state.menu = null;
        this.onSelectionChange();
        this.pushHistorySnapshot();
        this.onInput();
    }

    updateCurrentFillLine() {
        const lineEl = this.currentFillLineElement();
        if (!lineEl) {
            this.notification.add(_t("กรุณาคลิกบนเส้นที่ต้องการปรับก่อน"), {
                type: "warning",
            });
            return;
        }
        this.pushHistorySnapshot();
        const widthCm = Math.max(1, Math.min(18, parseFloat(this.state.lineCm) || 6));
        const bStyle = this.state.lineStyle === "solid" ? "solid" : "dotted";
        lineEl.dataset.lineCm = String(widthCm);
        lineEl.dataset.lineStyle = bStyle;
        lineEl.style.display = "inline-block";
        lineEl.style.minWidth = `${widthCm}cm`;
        lineEl.style.width = `${widthCm}cm`;
        lineEl.style.borderBottom = `1px ${bStyle} #000000`;
        const code = (this.state.lineFieldCode || "").trim();
        if (code) {
            lineEl.textContent = `{{${code}}}`;
        }
        this.state.menu = null;
        this.updateLineOverlay();
        this.pushHistorySnapshot();
        this.onInput();
    }

    unwrapCurrentFillLine() {
        const lineEl = this.currentFillLineElement();
        if (!lineEl) {
            this.notification.add(_t("กรุณาคลิกบนเส้นที่ต้องการเอาออกก่อน"), {
                type: "warning",
            });
            return;
        }
        this.pushHistorySnapshot();
        const text = (lineEl.textContent || "").replace(/\u00a0/g, " ").trim();
        lineEl.replaceWith(document.createTextNode(text));
        this.clearSelectedLine();
        this.state.menu = null;
        this.pushHistorySnapshot();
        this.onInput();
    }

    parsePlaceholderCode(token) {
        const match = String(token || "")
            .trim()
            .match(/^\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}$/);
        return match ? match[1] : "";
    }

    createFieldBoxEl(code) {
        const safe = String(code || "").replace(/[^a-zA-Z0-9_]/g, "");
        const span = document.createElement("span");
        span.className = "o_vpk_we_field_box";
        span.dataset.fieldCode = safe;
        span.setAttribute("contenteditable", "false");
        span.textContent = `{{${safe}}}`;
        return span;
    }

    buildFieldBoxHtml(code) {
        const safe = String(code || "").replace(/[^a-zA-Z0-9_]/g, "");
        return (
            `<span class="o_vpk_we_field_box" data-field-code="${safe}" ` +
            `contenteditable="false">{{${safe}}}</span>&#8203;`
        );
    }

    insertFieldBoxAtClient(code, clientX, clientY) {
        const page = this.editableRef.el;
        if (!page || !code) {
            return null;
        }
        const span = this.createFieldBoxEl(code);
        page.appendChild(span);
        const pageRect = page.getBoundingClientRect();
        this.pinFillLineOnPage(span, clientX - pageRect.left, clientY - pageRect.top, {
            snap: true,
        });
        this.selectLine(span);
        return span;
    }

    insertPlaceholder(code) {
        const lineEl = this.currentFillLineElement();
        if (lineEl) {
            this.pushHistorySnapshot();
            const current = (lineEl.textContent || "").replace(/\u00a0/g, "").trim();
            lineEl.textContent = current ? `${current} {{${code}}}` : `{{${code}}}`;
            this.state.menu = null;
            this.pushHistorySnapshot();
            this.onInput();
            return;
        }
        this.exec("insertHTML", this.buildFieldBoxHtml(code));
        this.ensureCaretAnchorsAroundBoxes();
    }

    onFieldDragStart(ev, code) {
        const token = `{{${code}}}`;
        if (ev.dataTransfer) {
            ev.dataTransfer.effectAllowed = "copy";
            ev.dataTransfer.setData("application/x-vpk-field-code", code);
            ev.dataTransfer.setData("application/x-vpk-placeholder", token);
            ev.dataTransfer.setData("text/plain", token);
        }
    }

    rangeFromPoint(x, y) {
        if (document.caretRangeFromPoint) {
            return document.caretRangeFromPoint(x, y);
        }
        if (document.caretPositionFromPoint) {
            const pos = document.caretPositionFromPoint(x, y);
            if (pos && pos.offsetNode) {
                const range = document.createRange();
                range.setStart(pos.offsetNode, pos.offset);
                range.collapse(true);
                return range;
            }
        }
        return null;
    }

    onEditorDragOver(ev) {
        if (this.props.readonly) {
            return;
        }
        const types = ev.dataTransfer ? Array.from(ev.dataTransfer.types || []) : [];
        if (
            types.includes("application/x-vpk-field-code") ||
            types.includes("application/x-vpk-placeholder") ||
            types.includes("text/plain")
        ) {
            ev.preventDefault();
            ev.dataTransfer.dropEffect = "copy";
            this.state.dragOver = true;
            const range = this.rangeFromPoint(ev.clientX, ev.clientY);
            if (range && this.isInEditor(range.commonAncestorContainer)) {
                const sel = document.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                this.savedRange = range.cloneRange();
            }
        }
    }

    onEditorDragLeave() {
        this.state.dragOver = false;
    }

    onEditorDrop(ev) {
        this.state.dragOver = false;
        if (this.props.readonly) {
            return;
        }
        const token =
            ev.dataTransfer?.getData("application/x-vpk-placeholder") ||
            ev.dataTransfer?.getData("text/plain");
        const code =
            ev.dataTransfer?.getData("application/x-vpk-field-code") ||
            this.parsePlaceholderCode(token);
        if (!token && !code) {
            return;
        }
        if (this.state.sourceMode && this.sourceRef.el) {
            ev.preventDefault();
            const insert = token || `{{${code}}}`;
            const ta = this.sourceRef.el;
            const start = ta.selectionStart ?? ta.value.length;
            const end = ta.selectionEnd ?? start;
            ta.value = ta.value.slice(0, start) + insert + ta.value.slice(end);
            ta.focus();
            ta.setSelectionRange(start + insert.length, start + insert.length);
            this.onInput();
            return;
        }
        if (!code && !(token || "").startsWith("{{")) {
            return;
        }
        ev.preventDefault();
        const fieldToken = code ? `{{${code}}}` : token;
        const targetLine = ev.target?.closest?.(".o_vpk_we_fill_line");
        if (targetLine && this.isInEditor(targetLine) && code) {
            this.pushHistorySnapshot();
            this.flattenFieldsIntoFillLine(targetLine);
            const span = this.createFieldBoxEl(code);
            targetLine.appendChild(span);
            this.placeCaretAfter(span);
            this.pushHistorySnapshot();
            this.onInput();
            return;
        }
        if (code && this.editableRef.el) {
            this.pushHistorySnapshot();
            this.editableRef.el.focus();
            this.insertFieldBoxAtClient(code, ev.clientX, ev.clientY);
            this.pushHistorySnapshot();
            this.onInput();
            return;
        }
        const range = this.rangeFromPoint(ev.clientX, ev.clientY);
        const editable = this.editableRef.el;
        if (editable) {
            this.pushHistorySnapshot();
            editable.focus();
            const sel = document.getSelection();
            if (range && this.isInEditor(range.commonAncestorContainer)) {
                sel.removeAllRanges();
                sel.addRange(range);
                this.savedRange = range.cloneRange();
            }
            document.execCommand("insertText", false, fieldToken);
            this.onSelectionChange();
            this.pushHistorySnapshot();
            this.onInput();
        }
    }

    pickImage() {
        this.imageInputRef.el?.click();
    }

    onImageSelected(ev) {
        const file = ev.target.files && ev.target.files[0];
        ev.target.value = "";
        if (!file) {
            return;
        }
        const reader = new FileReader();
        reader.onload = () => this.exec("insertImage", reader.result);
        reader.readAsDataURL(file);
    }

    toggleSource() {
        if (this.state.sourceMode) {
            const html = this.sourceRef.el.value;
            this.state.sourceMode = false;
            this.editableRef.el.innerHTML = html || "<p><br></p>";
            this.promoteUnderlineCellsToFillLines();
        } else {
            this.sourceRef.el.value = this.editableRef.el.innerHTML;
            this.state.sourceMode = true;
        }
        this.state.menu = null;
        this.onInput();
    }

    // ------------------------------------------------------------------
    // Find / replace
    // ------------------------------------------------------------------

    toggleFind() {
        this.state.findBar = !this.state.findBar;
        this.state.findMessage = "";
        this.findIndex = -1;
    }

    onFindKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.findNext();
        }
    }

    findMatches() {
        const text = this.state.findText;
        const matches = [];
        if (!text) {
            return matches;
        }
        const walker = document.createTreeWalker(this.editableRef.el, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
            const node = walker.currentNode;
            let index = node.data.indexOf(text);
            while (index >= 0) {
                matches.push([node, index]);
                index = node.data.indexOf(text, index + text.length);
            }
        }
        return matches;
    }

    findNext() {
        const matches = this.findMatches();
        if (!matches.length) {
            this.state.findMessage = _t("ไม่พบข้อความ");
            this.findIndex = -1;
            return;
        }
        this.findIndex = (this.findIndex + 1) % matches.length;
        const [node, index] = matches[this.findIndex];
        const range = document.createRange();
        range.setStart(node, index);
        range.setEnd(node, index + this.state.findText.length);
        const selection = document.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        this.savedRange = range.cloneRange();
        node.parentElement?.scrollIntoView({ block: "center", behavior: "smooth" });
        this.state.findMessage = `${this.findIndex + 1} / ${matches.length}`;
    }

    replaceOne() {
        const range = this.savedRange;
        if (range && this.isInEditor(range.commonAncestorContainer) &&
            range.toString() === this.state.findText && this.state.findText) {
            range.deleteContents();
            range.insertNode(document.createTextNode(this.state.replaceText));
            this.findIndex -= 1;
            this.onInput();
        }
        this.findNext();
    }

    replaceAll() {
        const text = this.state.findText;
        if (!text) {
            return;
        }
        let count = 0;
        const walker = document.createTreeWalker(this.editableRef.el, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) {
            nodes.push(walker.currentNode);
        }
        for (const node of nodes) {
            const parts = node.data.split(text);
            if (parts.length > 1) {
                count += parts.length - 1;
                node.data = parts.join(this.state.replaceText);
            }
        }
        this.state.findMessage = _t("แทนที่แล้ว %s ตำแหน่ง", count);
        this.findIndex = -1;
        this.onInput();
    }

    // ------------------------------------------------------------------
    // Preview / print
    // ------------------------------------------------------------------

    pageDocument() {
        const s = this.settings;
        const faces = ["TH Sarabun New", "TH SarabunIT๙"]
            .map(
                (family) => `
@font-face { font-family: "${family}"; src: url("${SARABUN_PATH}/THSarabunNew-Regular.ttf"); }
@font-face { font-family: "${family}"; font-weight: bold; src: url("${SARABUN_PATH}/THSarabunNew-Bold.ttf"); }
@font-face { font-family: "${family}"; font-style: italic; src: url("${SARABUN_PATH}/THSarabunNew-Italic.ttf"); }`
            )
            .join("");
        return `<!DOCTYPE html><html><head><meta charset="utf-8"/>
<title>${this.props.record.data.name || "Word layout"}</title>
<style>${faces}
@page { size: A4; margin: 0; }
html { background: #e9ecef; }
body { font-family: "${s.font}", "TH Sarabun New", sans-serif; font-size: ${s.size}pt; margin: 0; line-height: 1.15; }
.page { background: #fff; width: 21cm; min-height: 29.7cm; box-sizing: border-box; margin: 1cm auto;
        padding: ${s.top}cm ${s.right}cm ${s.bottom}cm ${s.left}cm; box-shadow: 0 0 6px rgba(0,0,0,.25);
        position: relative; color: #000; }
p { margin: 0; }
img { max-width: 100%; }
table { width: 100%; border-collapse: collapse; border: none; }
.o_vpk_we_fill_line { display: inline-block; vertical-align: baseline; padding: 0 4px; line-height: 1.05;
        min-height: 1.05em; border-bottom: 1px dotted #000; }
.o_vpk_we_fill_line[data-line-style="solid"] { border-bottom-style: solid; }
.o_vpk_we_fill_line[data-line-left], .o_vpk_we_fill_line[style*="absolute"],
.o_vpk_we_field_box[data-line-left], .o_vpk_we_field_box[style*="absolute"] { position: absolute; }
.o_vpk_we_field_box { display: inline-block; box-sizing: border-box; white-space: nowrap; line-height: 1.05; padding: 0 4px; }
@media print {
  html { background: #fff; }
  .page { margin: 0; box-shadow: none; }
  .o_vpk_we_field_box { background: transparent !important; border: 1px solid transparent !important; color: inherit !important; padding: 0 4px; line-height: 1.05; }
  .o_vpk_we_line_frame, .o_vpk_we_img_frame, .o_vpk_we_guide_line { display: none !important; }
  .o_vpk_we_caret_sink { display: inline; width: 0; min-width: 0; padding: 0; margin: 0; }
}
</style></head><body><div class="page">${this.currentHtml()}</div></body></html>`;
    }

    openPreview(print = false) {
        const win = window.open("", "_blank");
        if (!win) {
            this.notification.add(_t("เบราว์เซอร์บล็อกหน้าต่างใหม่ กรุณาอนุญาต pop-up"), {
                type: "warning",
            });
            return;
        }
        win.document.open();
        win.document.write(this.pageDocument());
        win.document.close();
        if (print) {
            const ready = win.document.fonts ? win.document.fonts.ready : Promise.resolve();
            ready.then(() => {
                win.focus();
                win.print();
            });
        }
    }
}

registry.category("fields").add("vpk_word_editor", {
    component: WordEditorField,
    supportedTypes: ["html"],
    extractProps: ({ options }) => ({
        showSave: Boolean(options && options.showSave),
    }),
});
