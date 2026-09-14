/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { applyThemeConfig, DEFAULT_THEME_CONFIG } from "./theme_utils";

export const SIDEBAR_WIDTH_PRESETS = [
    { id: "compact", label: "Compact", width: 220 },
    { id: "default", label: "Default", width: 288 },
    { id: "wide", label: "Wide", width: 340 },
    { id: "extra", label: "Extra Wide", width: 400 },
];

export const SIDEBAR_COLLAPSED_WIDTH_PRESETS = [
    { id: "narrow", label: "Narrow", width: 56 },
    { id: "default", label: "Default", width: 72 },
    { id: "wide", label: "Wide", width: 96 },
];

export class ThemeConfigPanel extends Component {
    static template = "vpk_sidebar_menu.ThemeConfigPanel";
    static props = {
        close: Function,
        initialTab: { type: String, optional: true },
    };

    setup() {
        this.sidebarWidthPresets = SIDEBAR_WIDTH_PRESETS;
        this.sidebarCollapsedWidthPresets = SIDEBAR_COLLAPSED_WIDTH_PRESETS;
        this.state = useState({
            activeTab: this.props.initialTab || "general",
            draft: { ...DEFAULT_THEME_CONFIG },
            saved: { ...DEFAULT_THEME_CONFIG },
            loading: true,
        });

        onWillStart(async () => {
            try {
                const config = await rpc("/vpk/theme/config", {});
                this.state.draft = { ...DEFAULT_THEME_CONFIG, ...config };
                this.state.draft.sidebar_width = Number(this.state.draft.sidebar_width);
                this.state.draft.sidebar_collapsed_width = Number(
                    this.state.draft.sidebar_collapsed_width
                );
                this.state.saved = { ...this.state.draft };
            } catch (e) {
                console.error("VPK Theme: failed to load config", e);
            } finally {
                this.state.loading = false;
            }
        });
    }

    get tabs() {
        return [
            { id: "general", label: "General Settings" },
            { id: "colors", label: "Colors" },
            { id: "sidebar_size", label: "Sidebar Size" },
            { id: "font_family", label: "Font Family" },
            { id: "font_size", label: "Font Size" },
            { id: "loaders", label: "Loaders" },
        ];
    }

    setActiveTab(tabId) {
        this.state.activeTab = tabId;
    }

    setDraftValue(key, value) {
        this.state.draft = { ...this.state.draft, [key]: value };
        applyThemeConfig(this.state.draft);
    }

    onRangeDraftValue(key, ev) {
        const value = Number.parseInt(ev.target.value, 10);
        this.setDraftValue(
            key,
            Number.isFinite(value) ? value : DEFAULT_THEME_CONFIG[key]
        );
    }

    isSidebarWidthPreset(width) {
        return Number(this.state.draft.sidebar_width) === Number(width);
    }

    isSidebarCollapsedWidthPreset(width) {
        return Number(this.state.draft.sidebar_collapsed_width) === Number(width);
    }

    setSidebarWidthPreset(width) {
        this.setDraftValue("sidebar_width", Number(width));
    }

    setSidebarCollapsedWidthPreset(width) {
        this.setDraftValue("sidebar_collapsed_width", Number(width));
    }

    get isSidebarDefaultSize() {
        return (
            Number(this.state.draft.sidebar_width) ===
                Number(DEFAULT_THEME_CONFIG.sidebar_width) &&
            Number(this.state.draft.sidebar_collapsed_width) ===
                Number(DEFAULT_THEME_CONFIG.sidebar_collapsed_width)
        );
    }

    get isThemeDefault() {
        const draft = this.state.draft;
        return Object.keys(DEFAULT_THEME_CONFIG).every(
            (key) => draft[key] === DEFAULT_THEME_CONFIG[key]
        );
    }

    onResetSidebarDefaultSize() {
        this.state.draft = {
            ...this.state.draft,
            sidebar_width: DEFAULT_THEME_CONFIG.sidebar_width,
            sidebar_collapsed_width: DEFAULT_THEME_CONFIG.sidebar_collapsed_width,
        };
        applyThemeConfig(this.state.draft);
    }

    onResetDefaults() {
        this.state.draft = { ...DEFAULT_THEME_CONFIG };
        applyThemeConfig(this.state.draft);
    }

    onDiscard() {
        this.state.draft = { ...this.state.saved };
        applyThemeConfig(this.state.saved);
        this.props.close();
    }

    async onApply() {
        try {
            const saved = await rpc("/vpk/theme/config/save", { ...this.state.draft });
            this.state.saved = { ...DEFAULT_THEME_CONFIG, ...saved };
            this.state.draft = { ...this.state.saved };
            applyThemeConfig(this.state.saved);
            this.props.close();
        } catch (e) {
            console.error("VPK Theme: failed to save config", e);
        }
    }
}
