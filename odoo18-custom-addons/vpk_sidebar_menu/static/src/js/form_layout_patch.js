/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormController } from "@web/views/form/form_controller";
import { Notebook } from "@web/core/notebook/notebook";
import { useEffect } from "@odoo/owl";
import {
    applyAllFormNotebooks,
    applyVpkNotebookLayout,
    getNotebookLockedHeight,
    lockNotebookMinHeight,
    normalizeNotebookListMargins,
} from "./theme_utils";

const BODY_CLASS = "o_vpk_sidebar_menu";
const NOTEBOOK_MIN_HEIGHT = 400;
const SIDE_CHATTER_MIN_MAIN = 900;

function getEffectiveMainWidth() {
    const styles = getComputedStyle(document.documentElement);
    const fromVar = parseFloat(styles.getPropertyValue("--vpk-main-width"));
    if (Number.isFinite(fromVar) && fromVar > 0) {
        return fromVar;
    }
    const sidebar = document.querySelector(".o_vpk_sidebar_primary");
    const sidebarW = sidebar ? sidebar.getBoundingClientRect().width : 0;
    const viewport =
        window.visualViewport?.width || document.documentElement.clientWidth || window.innerWidth;
    return Math.max(0, viewport - sidebarW);
}

function getViewportNotebookFloor() {
    const vh = window.visualViewport?.height || window.innerHeight || 800;
    return Math.max(NOTEBOOK_MIN_HEIGHT, Math.round(vh * 0.38));
}

function measureNotebookPaneHeight(notebookEl, paneEl) {
    const locked = getNotebookLockedHeight(notebookEl);
    const floor = getViewportNotebookFloor();
    const measured = Math.ceil(
        Math.max(
            paneEl.scrollHeight || 0,
            paneEl.offsetHeight || 0,
            paneEl.getBoundingClientRect().height || 0
        )
    );
    return Math.max(floor, locked, measured);
}

function syncNotebookContentHeight(notebook) {
    const paneEl = notebook.activePane?.el;
    const notebookEl = notebook.el;
    if (!paneEl || !notebookEl) {
        return;
    }
    const pageId = notebook.state.currentPage;
    if (!pageId) {
        return;
    }

    const lockedBefore = getNotebookLockedHeight(notebookEl);
    if (lockedBefore) {
        lockNotebookMinHeight(notebookEl, lockedBefore);
    }
    applyVpkNotebookLayout(notebookEl);

    const height = measureNotebookPaneHeight(notebookEl, paneEl);
    notebook._vpkTabHeights[pageId] = height;
    const maxHeight = Math.max(
        getViewportNotebookFloor(),
        ...Object.values(notebook._vpkTabHeights)
    );
    lockNotebookMinHeight(notebookEl, maxHeight);
    normalizeNotebookListMargins(notebookEl);
}

function scheduleNotebookLayout(notebook) {
    if (!notebook.el) {
        return;
    }
    applyVpkNotebookLayout(notebook.el);
    syncNotebookContentHeight(notebook);
    requestAnimationFrame(() => syncNotebookContentHeight(notebook));
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        if (!document.body.classList.contains(BODY_CLASS)) {
            return;
        }
        useEffect(
            (rootEl) => {
                if (!rootEl) {
                    return;
                }
                let timer;
                const run = () => {
                    clearTimeout(timer);
                    timer = setTimeout(() => applyAllFormNotebooks(rootEl), 30);
                };
                run();
                const observer = new MutationObserver(run);
                observer.observe(rootEl, { childList: true, subtree: true });
                const onResize = () => run();
                window.addEventListener("resize", onResize);
                return () => {
                    clearTimeout(timer);
                    observer.disconnect();
                    window.removeEventListener("resize", onResize);
                };
            },
            () => [this.rootRef.el, this.model?.root?.resId]
        );
    },
});

patch(FormRenderer.prototype, {
    mailLayout(hasAttachmentContainer) {
        const layout = super.mailLayout(hasAttachmentContainer);
        const body = document.body;
        if (!body.classList.contains(BODY_CLASS)) {
            return layout;
        }

        const mainWidth = getEffectiveMainWidth();
        const wantsBottom = body.classList.contains("vpk_chatter_bottom");
        const wantsRight = body.classList.contains("vpk_chatter_right");

        if (wantsBottom || mainWidth < SIDE_CHATTER_MIN_MAIN) {
            if (layout === "SIDE_CHATTER" || layout === "EXTERNAL_COMBO_XXL") {
                return "BOTTOM_CHATTER";
            }
        }

        if (wantsRight && !wantsBottom && mainWidth >= SIDE_CHATTER_MIN_MAIN) {
            if (layout === "BOTTOM_CHATTER") {
                return "SIDE_CHATTER";
            }
        }

        return layout;
    },
});

patch(Notebook.prototype, {
    setup() {
        super.setup(...arguments);
        this._vpkTabHeights = {};

        useEffect(
            () => {
                const paneEl = this.activePane?.el;
                if (!paneEl || !this.el) {
                    return;
                }

                lockNotebookMinHeight(this.el, getViewportNotebookFloor());
                scheduleNotebookLayout(this);

                const resizeObserver = new ResizeObserver(() => scheduleNotebookLayout(this));
                resizeObserver.observe(paneEl);

                return () => resizeObserver.disconnect();
            },
            () => [this.state.currentPage]
        );
    },

    activatePage(pageIndex) {
        super.activatePage(pageIndex);
        queueMicrotask(() => {
            if (this.el) {
                scheduleNotebookLayout(this);
            }
        });
    },
});
