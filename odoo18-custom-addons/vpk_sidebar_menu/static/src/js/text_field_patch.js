/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";
import * as autoresize from "@web/core/utils/autoresize";

const originalUseAutoresize = autoresize.useAutoresize;

function setTextareaHeight(el, heightPx) {
    el.style.setProperty("height", `${heightPx}px`, "important");
}

function setupVpkTextarea(el, options = {}) {
    const minH = options.minimumHeight === 0 ? 36 : Math.max(options.minimumHeight || 80, 80);

    const apply = () => {
        el.style.setProperty("resize", "vertical", "important");
        el.style.setProperty("overflow-y", "auto", "important");
        el.style.setProperty("min-height", `${minH}px`, "important");
        el.style.setProperty("max-height", "none", "important");
        el.parentElement?.style.setProperty("height", "auto", "important");
    };

    const syncHeight = () => {
        apply();
        if (el.dataset.vpkManualHeight) {
            return;
        }
        const current = el.offsetHeight || minH;
        el.style.removeProperty("height");
        const target = Math.max(el.scrollHeight, minH, current);
        setTextareaHeight(el, target);
        apply();
    };

    setTextareaHeight(el, minH);
    apply();
    syncHeight();

    el.addEventListener("input", syncHeight);

    let resizeStartHeight = null;
    const onPointerDown = (ev) => {
        const rect = el.getBoundingClientRect();
        if (ev.clientY >= rect.bottom - 16) {
            resizeStartHeight = el.offsetHeight;
        }
    };
    const onPointerUp = () => {
        if (resizeStartHeight !== null && el.offsetHeight !== resizeStartHeight) {
            el.dataset.vpkManualHeight = "1";
            setTextareaHeight(el, el.offsetHeight);
        }
        resizeStartHeight = null;
        apply();
    };

    el.addEventListener("pointerdown", onPointerDown);
    el.addEventListener("pointerup", onPointerUp);

    return () => {
        el.removeEventListener("input", syncHeight);
        el.removeEventListener("pointerdown", onPointerDown);
        el.removeEventListener("pointerup", onPointerUp);
    };
}

patch(autoresize, {
    useAutoresize(ref, options = {}) {
        const proxyRef = {
            get el() {
                const el = ref.el;
                return el instanceof HTMLTextAreaElement ? null : el;
            },
        };
        originalUseAutoresize(proxyRef, options);

        useEffect((el) => {
            if (!(el instanceof HTMLTextAreaElement)) {
                return;
            }
            return setupVpkTextarea(el, options);
        }, () => [ref.el]);
    },
});
