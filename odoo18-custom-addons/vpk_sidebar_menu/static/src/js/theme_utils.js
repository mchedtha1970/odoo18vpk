/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { syncVpkViewportLayout } from "./layout_utils";

const THEME_STYLE_CLASSES = [
    "vpk_theme_rounded",
    "vpk_theme_standard",
    "vpk_theme_square",
];
const FONT_FAMILY_CLASSES = [
    "vpk_font_default",
    "vpk_font_inter",
    "vpk_font_ibm_plex_thai",
    "vpk_font_anuphan",
    "vpk_font_kanit",
    "vpk_font_sarabun",
    "vpk_font_prompt",
    "vpk_font_roboto",
];
const FONT_SIZE_CLASSES = [
    "vpk_font_size_small",
    "vpk_font_size_medium",
    "vpk_font_size_large",
];
const LOADER_CLASSES = [
    "vpk_loader_default",
    "vpk_loader_dots",
    "vpk_loader_bars",
];

const FONT_FAMILY_VALUES = {
    default: "",
    inter: "'Inter', 'Noto Sans Thai', sans-serif",
    ibm_plex_thai: "'IBM Plex Sans Thai', sans-serif",
    anuphan: "'Anuphan', sans-serif",
    kanit: "'Kanit', sans-serif",
    sarabun: "'Sarabun', sans-serif",
    prompt: "'Prompt', sans-serif",
    roboto: "'Roboto', sans-serif",
};

const FONT_SIZE_VALUES = {
    small: {
        base: "12px", sm: "11px", md: "12px", lg: "14px", xl: "18px",
        theadPad: "0.4rem", headerHeight: "2rem", fieldHeight: "30px",
    },
    medium: {
        base: "13px", sm: "11px", md: "13px", lg: "15px", xl: "20px",
        theadPad: "0.5rem", headerHeight: "2.25rem", fieldHeight: "34px",
    },
    large: {
        base: "14px", sm: "12px", md: "14px", lg: "16px", xl: "22px",
        theadPad: "0.6rem", headerHeight: "2.5rem", fieldHeight: "38px",
    },
};

// rounded = guideline default: rounded-xl cards, rounded-md buttons/inputs
const THEME_BORDER_RADIUS = {
    rounded: { lg: "12px", md: "6px", sm: "4px" },
    standard: { lg: "8px", md: "4px", sm: "3px" },
    square: { lg: "0", md: "0", sm: "0" },
};

const BADGE_RADIUS = {
    pill: "9999px",
    rounded: "6px",
    square: "0",
};

export const DEFAULT_THEME_CONFIG = {
    theme_style: "rounded",
    menu_position: "vertical",
    chatter_position: "bottom",
    tree_form_split_view: false,
    list_view_density: "comfortable",
    list_view_sticky_header: false,
    sidebar_color: "#2563eb",
    sidebar_active_color: "#1d4ed8",
    sidebar_text_color: "#ffffff",
    sidebar_bg_style: "light",
    sidebar_bg_top: "#15803d",
    sidebar_bg_bottom: "#14532d",
    font_family: "inter",
    font_size: "medium",
    loader_style: "default",
    badge_style: "pill",
    sidebar_width: 256,
    sidebar_collapsed_width: 80,
};

const GOOGLE_FONTS_URL =
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Thai:wght@400;500;600;700&family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&family=Anuphan:wght@300;400;500;600;700&family=Kanit:wght@300;400;500;600;700&family=Prompt:wght@300;400;500;600;700&family=Roboto:wght@300;400;500;700&family=Sarabun:wght@300;400;500;600;700&display=swap";
const SYSTRAY_THEME_STYLE_ID = "vpk-systray-theme-styles";
const NOTEBOOK_THEME_STYLE_ID = "vpk-notebook-theme-styles";
const NOTEBOOK_MIN_HEIGHT_PX = 400;
let notebookResizeListenerAdded = false;

export function getNotebookLockedHeight(notebookEl) {
    if (!notebookEl) {
        return 0;
    }
    return parseFloat(notebookEl.dataset.vpkMaxHeight || "0") || 0;
}

function getNotebookHeightFloor() {
    const vh = window.visualViewport?.height || window.innerHeight || 800;
    return Math.max(NOTEBOOK_MIN_HEIGHT_PX, Math.round(vh * 0.38));
}

function updateNotebookThemeStyles() {
    let style = document.getElementById(NOTEBOOK_THEME_STYLE_ID);
    if (!style) {
        style = document.createElement("style");
        style.id = NOTEBOOK_THEME_STYLE_ID;
        document.head.appendChild(style);
    }
    const floor = getNotebookHeightFloor();
    style.textContent = `
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_sheet_bg:has(.o_notebook) {
    width: 100% !important;
    max-width: 100% !important;
    align-self: stretch !important;
}
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_renderer .o_form_sheet .o_notebook,
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_sheet .o_notebook {
    --notebook-margin-x: 0 !important;
    --notebook-padding-x: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
}
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_renderer .o_form_sheet .o_notebook > .o_notebook_content,
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_sheet .o_notebook > .o_notebook_content {
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
    min-height: var(--vpk-notebook-min-height, ${floor}px) !important;
    box-sizing: border-box !important;
}
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_renderer .o_form_sheet .o_notebook > .o_notebook_content > .tab-pane,
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_sheet .o_notebook > .o_notebook_content > .tab-pane {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    flex: 1 1 auto !important;
    padding: var(--formView-sheet-padding-y, 1rem) 0 !important;
    margin: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    min-height: var(--vpk-notebook-min-height, ${floor}px) !important;
    box-sizing: border-box !important;
}
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_renderer .o_form_sheet .o_notebook .tab-pane > *,
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_sheet .o_notebook .tab-pane > * {
    width: 100% !important;
    max-width: 100% !important;
    align-self: stretch !important;
}
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_renderer .o_form_sheet .o_notebook .tab-pane .o_group.row > :only-child,
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_sheet .o_notebook .tab-pane .o_group.row > :only-child {
    flex: 0 0 100% !important;
    max-width: 100% !important;
    width: 100% !important;
}
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_renderer .o_form_sheet .o_notebook .o_list_renderer,
html body.o_web_client.o_vpk_sidebar_menu .o_form_view .o_form_sheet .o_notebook .o_list_renderer {
    --ListRenderer-margin-x: 0 !important;
    --ListRenderer-table-padding-x: var(--formView-sheet-padding-x, 1rem) !important;
    margin: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
}
`;
}

export function normalizeNotebookListMargins(notebookEl) {
    if (!notebookEl) {
        return;
    }
    for (const list of notebookEl.querySelectorAll(".o_list_renderer")) {
        list.style.setProperty("--ListRenderer-margin-x", "0", "important");
        list.style.setProperty("--ListRenderer-table-padding-x", "0", "important");
        list.style.margin = "0";
        list.style.width = "100%";
        list.style.maxWidth = "100%";
    }
}

/** Align notebook tabs to the same sheet-width content box (no bleed / no broken columns). */
export function applyVpkNotebookLayout(notebookEl) {
    if (!notebookEl || !document.body.classList.contains("o_vpk_sidebar_menu")) {
        return;
    }
    const sheet = notebookEl.closest(".o_form_sheet");
    if (!sheet) {
        return;
    }
    notebookEl.classList.add("o_vpk_notebook_unified");

    const cs = getComputedStyle(sheet);
    const padL = parseFloat(cs.paddingLeft) || 0;
    const padR = parseFloat(cs.paddingRight) || 0;
    const setImp = (el, prop, val) => el.style.setProperty(prop, val, "important");

    setImp(notebookEl, "box-sizing", "border-box");
    setImp(notebookEl, "width", "100%");
    setImp(notebookEl, "max-width", "100%");
    setImp(notebookEl, "margin-left", "0");
    setImp(notebookEl, "margin-right", "0");
    setImp(notebookEl, "--notebook-margin-x", "0");
    setImp(notebookEl, "--notebook-padding-x", "0");

    normalizeNotebookListMargins(notebookEl);

    for (const header of notebookEl.querySelectorAll(".o_notebook_headers")) {
        setImp(header, "padding-left", `${padL}px`);
        setImp(header, "padding-right", `${padR}px`);
    }

    const content = notebookEl.querySelector(".o_notebook_content");
    if (content) {
        setImp(content, "display", "flex");
        setImp(content, "flex-direction", "column");
        setImp(content, "width", "100%");
        setImp(content, "max-width", "100%");
        const lockedMin = getNotebookLockedHeight(notebookEl) || getNotebookHeightFloor();
        setImp(content, "min-height", `${lockedMin}px`);
    }

    const pane = notebookEl.querySelector(".tab-pane");
    if (pane) {
        setImp(pane, "display", "flex");
        setImp(pane, "flex-direction", "column");
        setImp(pane, "align-items", "stretch");
        setImp(pane, "margin", "0");
        setImp(pane, "padding-left", "0");
        setImp(pane, "padding-right", "0");
        setImp(pane, "width", "100%");
        setImp(pane, "max-width", "100%");
        setImp(pane, "box-sizing", "border-box");
        const lockedMin = getNotebookLockedHeight(notebookEl) || getNotebookHeightFloor();
        setImp(pane, "min-height", `${lockedMin}px`);
    }

    for (const child of notebookEl.querySelectorAll(".tab-pane > *")) {
        setImp(child, "width", "100%");
        setImp(child, "max-width", "100%");
        setImp(child, "align-self", "stretch");
    }

    for (const onlyCol of notebookEl.querySelectorAll(".tab-pane .o_group.row > :only-child")) {
        setImp(onlyCol, "flex", "0 0 100%");
        setImp(onlyCol, "max-width", "100%");
        setImp(onlyCol, "width", "100%");
    }

    for (const list of notebookEl.querySelectorAll(".o_list_renderer")) {
        setImp(list, "--ListRenderer-margin-x", "0");
        setImp(list, "--ListRenderer-table-padding-x", `${padL || 16}px`);
        setImp(list, "margin", "0");
        setImp(list, "width", "100%");
    }
}

export function lockNotebookMinHeight(notebookEl, heightPx) {
    if (!notebookEl || !heightPx) {
        return;
    }
    const floor = getNotebookHeightFloor();
    const prev = getNotebookLockedHeight(notebookEl);
    const next = Math.max(prev, floor, Math.ceil(heightPx));
    notebookEl.dataset.vpkMaxHeight = String(next);
    const minHeight = `${next}px`;
    const setImp = (el, prop, val) => el?.style.setProperty(prop, val, "important");
    setImp(notebookEl.querySelector(".o_notebook_content"), "min-height", minHeight);
    setImp(notebookEl.querySelector(".tab-pane"), "min-height", minHeight);
    document.documentElement.style.setProperty("--vpk-notebook-min-height", minHeight);
}

export function applyAllFormNotebooks(rootEl) {
    if (!rootEl) {
        return;
    }
    for (const notebook of rootEl.querySelectorAll(".o_notebook")) {
        applyVpkNotebookLayout(notebook);
    }
}

function updateSystrayThemeStyles() {
    let style = document.getElementById(SYSTRAY_THEME_STYLE_ID);
    if (!style) {
        style = document.createElement("style");
        style.id = SYSTRAY_THEME_STYLE_ID;
        document.head.appendChild(style);
    }
    style.textContent = `
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray {
    display: grid !important;
    grid-template-columns: repeat(7, 30px) !important;
    justify-content: center !important;
    justify-items: center !important;
    align-items: center !important;
    column-gap: 2px !important;
    row-gap: 2px !important;
    padding: 0 12px 8px !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray .o_vpk_systray_primary,
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray .o_vpk_systray_secondary {
    display: contents !important;
}
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray .o_vpk_systray_item {
    width: 30px !important;
    max-width: 30px !important;
    padding: 0 !important;
    margin: 0 !important;
    --NavBar-entry-padding-left: 0 !important;
    --NavBar-entry-padding-right: 0 !important;
}
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray .o_vpk_systray_item a,
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray .o_vpk_systray_item button,
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray .o_vpk_systray_item .dropdown-toggle,
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray .o_vpk_systray_item .o_MessagingMenu_toggler,
body.o_web_client.o_vpk_sidebar_menu .o_vpk_sidebar_systray .o_vpk_systray_item .o_nav_entry {
    width: 30px !important;
    height: 30px !important;
    padding: 0 !important;
    margin: 0 !important;
    --NavBar-entry-padding-left: 0 !important;
    --NavBar-entry-padding-right: 0 !important;
}
`;
}

function ensureGoogleFonts() {
    if (document.getElementById("vpk-google-fonts")) {
        return;
    }
    const link = document.createElement("link");
    link.id = "vpk-google-fonts";
    link.rel = "stylesheet";
    link.href = GOOGLE_FONTS_URL;
    document.head.appendChild(link);
}

function replaceBodyClass(body, classes, activeClass) {
    for (const cls of classes) {
        body.classList.remove(cls);
    }
    if (activeClass) {
        body.classList.add(activeClass);
    }
}

export function applyThemeConfig(config) {
    const body = document.body;
    const root = document.documentElement;
    if (!body) {
        return;
    }
    const cfg = { ...DEFAULT_THEME_CONFIG, ...config };

    replaceBodyClass(body, THEME_STYLE_CLASSES, `vpk_theme_${cfg.theme_style}`);
    replaceBodyClass(body, FONT_FAMILY_CLASSES, `vpk_font_${cfg.font_family}`);
    replaceBodyClass(body, FONT_SIZE_CLASSES, `vpk_font_size_${cfg.font_size}`);
    replaceBodyClass(body, LOADER_CLASSES, `vpk_loader_${cfg.loader_style}`);

    body.classList.toggle("vpk_chatter_right", cfg.chatter_position === "right");
    body.classList.toggle("vpk_chatter_bottom", cfg.chatter_position === "bottom");
    body.classList.toggle("vpk_list_compact", cfg.list_view_density === "compact");
    body.classList.toggle("vpk_list_sticky_header", cfg.list_view_sticky_header);
    body.classList.toggle("vpk_tree_split_view", cfg.tree_form_split_view);
    body.classList.toggle("vpk_menu_horizontal", cfg.menu_position === "horizontal");
    body.classList.toggle("vpk_menu_vertical", cfg.menu_position === "vertical");
    body.classList.toggle("vpk_sidebar_gradient", cfg.sidebar_bg_style === "gradient");
    root.style.setProperty("--vpk-sidebar-bg-top", cfg.sidebar_bg_top);
    root.style.setProperty("--vpk-sidebar-bg-bottom", cfg.sidebar_bg_bottom);

    root.style.setProperty("--vpk-primary", cfg.sidebar_color);
    root.style.setProperty("--vpk-primary-hover", cfg.sidebar_active_color);
    root.style.setProperty("--vpk-on-primary", cfg.sidebar_text_color);
    // Legacy token names, still read by vpk_budget / vpk_tier_validation / vpk_stock_warehouse
    root.style.setProperty("--vpk-sidebar-bg-start", cfg.sidebar_color);
    root.style.setProperty("--vpk-sidebar-bg-end", cfg.sidebar_active_color);
    root.style.setProperty("--vpk-sidebar-bg-gradient", cfg.sidebar_color);
    root.style.setProperty("--vpk-sidebar-bg", cfg.sidebar_color);
    root.style.setProperty("--vpk-sidebar-text", cfg.sidebar_text_color);
    root.style.setProperty("--vpk-primary-color", cfg.sidebar_color);
    root.style.setProperty("--vpk-primary-color-dark", cfg.sidebar_active_color);
    root.style.setProperty("--o-brand-primary", cfg.sidebar_color);
    root.style.setProperty("--o-action", cfg.sidebar_color);
    root.style.setProperty("--vpk-sidebar-width", `${cfg.sidebar_width}px`);
    root.style.setProperty(
        "--vpk-sidebar-width-collapsed",
        `${cfg.sidebar_collapsed_width}px`
    );

    const fontFamily = FONT_FAMILY_VALUES[cfg.font_family] || "";
    const fontSizes = FONT_SIZE_VALUES[cfg.font_size] || FONT_SIZE_VALUES.medium;
    if (fontFamily) {
        ensureGoogleFonts();
        root.style.setProperty("--vpk-font-family", fontFamily);
        root.style.setProperty("--bs-body-font-family", fontFamily);
        body.style.fontFamily = fontFamily;
    } else {
        root.style.removeProperty("--vpk-font-family");
        root.style.removeProperty("--bs-body-font-family");
        body.style.removeProperty("font-family");
    }
    root.style.setProperty("--vpk-font-size", fontSizes.base);
    root.style.setProperty("--vpk-font-size-sm", fontSizes.sm);
    root.style.setProperty("--vpk-font-size-md", fontSizes.md);
    root.style.setProperty("--vpk-font-size-lg", fontSizes.lg);
    root.style.setProperty("--vpk-font-size-xl", fontSizes.xl);
    root.style.setProperty("--vpk-list-thead-padding-y", fontSizes.theadPad);
    root.style.setProperty("--vpk-list-header-height", fontSizes.headerHeight);
    root.style.setProperty("--vpk-list-thead-line-height", "1.45");
    root.style.setProperty("--vpk-field-height", fontSizes.fieldHeight);
    root.style.setProperty("--vpk-field-border-color", "var(--vpk-border)");

    const radius = THEME_BORDER_RADIUS[cfg.theme_style] || THEME_BORDER_RADIUS.standard;
    root.style.setProperty("--vpk-border-radius-lg", radius.lg);
    root.style.setProperty("--vpk-border-radius-md", radius.md);
    root.style.setProperty("--vpk-border-radius-sm", radius.sm);
    root.style.setProperty("--vpk-badge-radius", BADGE_RADIUS[cfg.badge_style] || BADGE_RADIUS.pill);
    root.style.setProperty("--vpk-box-shadow-common", "var(--vpk-shadow-sm)");
    root.style.setProperty("--vpk-form-body-bg", "var(--vpk-app-bg)");
    root.style.setProperty("--vpk-form-surface-bg", "var(--vpk-surface)");
    root.style.setProperty("--vpk-notebook-min-height", `${getNotebookHeightFloor()}px`);

    document.getElementById("vpk-button-theme-styles")?.remove();
    updateSystrayThemeStyles();
    updateNotebookThemeStyles();
    syncVpkViewportLayout();
    applyAllFormNotebooks(document.querySelector(".o_action_manager") || document.body);
    if (!notebookResizeListenerAdded) {
        window.addEventListener("resize", () => updateNotebookThemeStyles());
        notebookResizeListenerAdded = true;
    }
    // Re-render open forms so mailLayout() picks up chatter position change
    browser.dispatchEvent(new Event("resize"));
}
