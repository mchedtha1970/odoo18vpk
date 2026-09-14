/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

const BODY_CLASS = "o_vpk_sidebar_menu";
const MOBILE_QUERY = "(max-width: 767.98px)";

function parsePx(value, fallback) {
    const parsed = parseFloat(String(value).trim());
    return Number.isFinite(parsed) ? parsed : fallback;
}

function getViewportWidth() {
    return document.documentElement.clientWidth || window.innerWidth;
}

function measureSidebarWidth(collapsed) {
    const el = document.querySelector(".o_vpk_sidebar_primary");
    if (el) {
        return Math.round(el.getBoundingClientRect().width);
    }
    return collapsed ? 72 : 288;
}

let lastMainWidth = 0;

export function syncVpkViewportLayout() {
    const body = document.body;
    const root = document.documentElement;
    if (!body.classList.contains(BODY_CLASS)) {
        return;
    }

    const isMobile = window.matchMedia(MOBILE_QUERY).matches;
    const fullscreen = body.classList.contains("o_fullscreen");
    const collapsed = body.classList.contains("o_vpk_sidebar_collapsed");

    let sidebarOffset = 0;
    if (!fullscreen && !isMobile) {
        sidebarOffset = measureSidebarWidth(collapsed);
    }

    const viewportWidth = getViewportWidth();
    const mainWidth = Math.max(0, viewportWidth - sidebarOffset);

    root.style.setProperty("--vpk-viewport-width", `${viewportWidth}px`);
    root.style.setProperty("--vpk-main-offset", `${sidebarOffset}px`);
    root.style.setProperty("--vpk-main-width", `${mainWidth}px`);

    // Re-evaluate form chatter layout (mailLayout) when usable width changes
    if (Math.abs(mainWidth - lastMainWidth) >= 1) {
        lastMainWidth = mainWidth;
        browser.dispatchEvent(new Event("resize"));
    }
}

let resizeBound = false;
let wizardResizeBound = false;
let rafId = 0;

const WIZARD_MODAL_SELECTOR = ".o_dialog > .modal.o_technical_modal:not(.o_modal_full)";
const WIZARD_RESIZE_HANDLE_PX = 18;
const WIZARD_MIN_WIDTH = 360;
const WIZARD_MIN_HEIGHT = 200;

function wizardResizeEdges(ev, contentEl) {
    const rect = contentEl.getBoundingClientRect();
    const margin = WIZARD_RESIZE_HANDLE_PX;
    return {
        right: ev.clientX >= rect.right - margin,
        bottom: ev.clientY >= rect.bottom - margin,
    };
}

function lockWizardPixelSize(modalEl, dialogEl, contentEl) {
    const width = contentEl.offsetWidth;
    const height = contentEl.offsetHeight;
    modalEl.classList.add("vpk-wizard-resize-active");
    contentEl.style.width = `${width}px`;
    contentEl.style.height = `${height}px`;
    contentEl.style.maxWidth = "95vw";
    contentEl.style.maxHeight = "90vh";
    dialogEl.style.width = `${width}px`;
    dialogEl.style.maxWidth = "95vw";
    dialogEl.style.height = "auto";
    return { width, height };
}

function applyWizardSize(dialogEl, contentEl, width, height) {
    const maxW = Math.min(window.innerWidth * 0.95, window.innerWidth - 16);
    const maxH = Math.min(window.innerHeight * 0.9, window.innerHeight - 16);
    const nextW = Math.min(maxW, Math.max(WIZARD_MIN_WIDTH, width));
    const nextH = Math.min(maxH, Math.max(WIZARD_MIN_HEIGHT, height));
    contentEl.style.width = `${nextW}px`;
    contentEl.style.height = `${nextH}px`;
    dialogEl.style.width = `${nextW}px`;
}

function onWizardResizePointerDown(ev) {
    if (ev.button !== 0) {
        return;
    }
    if (ev.target.closest("button, a, input, select, textarea, .btn-close, .o_field_widget")) {
        return;
    }
    const contentEl = ev.target.closest(`${WIZARD_MODAL_SELECTOR} .modal-content`);
    if (!contentEl) {
        return;
    }
    const edges = wizardResizeEdges(ev, contentEl);
    if (!edges.right && !edges.bottom) {
        return;
    }
    const modalEl = contentEl.closest(WIZARD_MODAL_SELECTOR);
    const dialogEl = modalEl?.querySelector(":scope > .modal-dialog");
    if (!modalEl || !dialogEl) {
        return;
    }

    ev.preventDefault();
    ev.stopPropagation();

    const startX = ev.clientX;
    const startY = ev.clientY;
    const { width: startW, height: startH } = lockWizardPixelSize(modalEl, dialogEl, contentEl);
    const resizeX = edges.right;
    const resizeY = edges.bottom;

    const onMove = (moveEv) => {
        const nextW = resizeX ? startW + (moveEv.clientX - startX) : startW;
        const nextH = resizeY ? startH + (moveEv.clientY - startY) : startH;
        applyWizardSize(dialogEl, contentEl, nextW, nextH);
    };
    const onUp = () => {
        document.removeEventListener("pointermove", onMove, true);
        document.removeEventListener("pointerup", onUp, true);
        document.body.classList.remove("vpk-wizard-resizing");
    };
    document.body.classList.add("vpk-wizard-resizing");
    document.addEventListener("pointermove", onMove, true);
    document.addEventListener("pointerup", onUp, true);
}

export function bindVpkWizardResize() {
    if (wizardResizeBound) {
        return;
    }
    wizardResizeBound = true;
    document.addEventListener("pointerdown", onWizardResizePointerDown, true);
}

function scheduleSyncVpkViewportLayout() {
    if (rafId) {
        return;
    }
    rafId = browser.requestAnimationFrame(() => {
        rafId = 0;
        syncVpkViewportLayout();
    });
}

export function bindVpkViewportLayout() {
    syncVpkViewportLayout();
    if (resizeBound) {
        return;
    }
    resizeBound = true;

    browser.addEventListener("resize", scheduleSyncVpkViewportLayout);
    browser.addEventListener("orientationchange", scheduleSyncVpkViewportLayout);

    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", scheduleSyncVpkViewportLayout);
    }

    const sidebar = document.querySelector(".o_vpk_sidebar_primary");
    if (sidebar && typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(scheduleSyncVpkViewportLayout);
        ro.observe(sidebar);
    }

    if (typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(scheduleSyncVpkViewportLayout);
        ro.observe(document.documentElement);
    }

    const body = document.body;
    if (body && typeof MutationObserver !== "undefined") {
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === "attributes" && mutation.attributeName === "class") {
                    scheduleSyncVpkViewportLayout();
                    break;
                }
            }
        });
        observer.observe(body, { attributes: true, attributeFilter: ["class"] });
    }
}
