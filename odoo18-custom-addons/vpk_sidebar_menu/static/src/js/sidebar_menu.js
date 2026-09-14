/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { WebClient } from "@web/webclient/webclient";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { imageUrl } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { ThemeConfigPanel } from "./theme_config_panel";
import { applyThemeConfig, DEFAULT_THEME_CONFIG } from "./theme_utils";
import { bindVpkViewportLayout, syncVpkViewportLayout, bindVpkWizardResize } from "./layout_utils";
import "@vpk_sidebar_menu/js/text_field_patch";
import "@vpk_sidebar_menu/js/form_layout_patch";
import "@vpk_sidebar_menu/js/form_dropdown_patch";

const userMenuRegistry = registry.category("user_menuitems");

const BODY_CLASS = "o_vpk_sidebar_menu";
const HIDDEN_SYSTRAY_KEYS = new Set(["web.user_menu", "burger_menu"]);

const SECONDARY_SYSTRAY_KEYS = [
    "web.debug_mode_menu",
    "mail.messaging_menu",
    "base_tier_validation.ReviewerMenu",
    "vpk.profile_edit",
    "mail.activity_menu",
];
const systrayRegistry = registry.category("systray");

function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) {
        return "Good Morning";
    }
    if (hour < 17) {
        return "Good Afternoon";
    }
    return "Good Evening";
}

patch(NavBar, {
    components: {
        ...NavBar.components,
        ThemeConfigPanel,
        Dropdown,
        DropdownItem,
        CheckBox,
    },
});

patch(WebClient.prototype, {
    setup() {
        super.setup(...arguments);
        this.ui = useService("ui");
        onMounted(async () => {
            document.body.classList.add(BODY_CLASS);
            bindVpkViewportLayout();
            bindVpkWizardResize();
            applyThemeConfig(DEFAULT_THEME_CONFIG);
            try {
                const config = await rpc("/vpk/theme/config", {});
                applyThemeConfig(config);
            } catch (e) {
                console.error("VPK Theme: failed to load config on startup", e);
            }
        });
        onWillUnmount(() => {
            document.body.classList.remove(BODY_CLASS);
        });
        useEffect(
            () => {
                syncVpkViewportLayout();
            },
            () => [this.ui.size]
        );
    },
});

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.companyService = useService("company");
        this.sidebarState = useState({
            mobileOpen: false,
            collapsed: false,
            expandedMenus: {},
            themePanelOpen: false,
            themePanelTab: "general",
        });
        this.userName = user.name;
        const { partnerId, writeDate } = user;
        this.userAvatar = imageUrl("res.partner", partnerId, "avatar_128", {
            unique: writeDate,
        });
        this.greeting = getGreeting();

        useEffect(
            () => {
                document.body.classList.toggle(
                    "o_vpk_sidebar_collapsed",
                    this.sidebarState.collapsed && !this.ui.isSmall
                );
                syncVpkViewportLayout();
                const currentApp = this.menuService.getCurrentApp();
                if (currentApp) {
                    this.sidebarState.expandedMenus = {
                        ...this.sidebarState.expandedMenus,
                        [currentApp.id]: true,
                    };
                }
            },
            () => [
                this.sidebarState.collapsed,
                this.ui.isSmall,
                this.currentApp?.id,
            ]
        );
    },

    get currentCompany() {
        return this.companyService.currentCompany;
    },

    set currentCompany(_) {},

    get companyLogoUrl() {
        const company = this.currentCompany;
        return company ? `/web/image/res.company/${company.id}/logo` : false;
    },

    get apps() {
        return this.menuService.getApps();
    },

    getUserMenuElements() {
        return userMenuRegistry
            .getAll()
            .map((element) => element(this.env))
            .filter((element) => (element.show ? element.show() : true))
            .sort((x, y) => (x.sequence || 100) - (y.sequence || 100));
    },

    get userMenuResourcesTitle() {
        return _t("Supporting Documents");
    },

    getSystrayItemByKey(key) {
        const item = systrayRegistry.get(key, false);
        if (!item) {
            return null;
        }
        const entry = { key, ...item };
        if ("isDisplayed" in entry && !entry.isDisplayed(this.env)) {
            return null;
        }
        return entry;
    },

    get systrayItems() {
        return systrayRegistry
            .getEntries()
            .map(([key, value]) => ({ key, ...value }))
            .filter((item) =>
                ("isDisplayed" in item ? item.isDisplayed(this.env) : true)
            )
            .filter((item) => !HIDDEN_SYSTRAY_KEYS.has(item.key))
            .reverse();
    },

    set systrayItems(_) {},

    get secondarySystraySlots() {
        const slots = [];
        for (const key of SECONDARY_SYSTRAY_KEYS) {
            if (key === "vpk.profile_edit") {
                slots.push({ key, isEdit: true });
                continue;
            }
            const item = this.getSystrayItemByKey(key);
            if (item) {
                slots.push(item);
            } else if (key === "web.debug_mode_menu") {
                slots.push({ key: "vpk.debug_placeholder", empty: true });
            }
        }
        return slots;
    },

    isAppActive(app) {
        const current = this.menuService.getCurrentApp();
        return current && current.id === app.id;
    },

    appHasSubMenus(app) {
        const tree = this.menuService.getMenuAsTree(app.id);
        return tree.childrenTree && tree.childrenTree.length > 0;
    },

    getAppChildren(app) {
        return this.menuService.getMenuAsTree(app.id).childrenTree || [];
    },

    isMenuExpanded(menuId) {
        return !!this.sidebarState.expandedMenus[menuId];
    },

    toggleMenuExpand(menuId) {
        const next = { ...this.sidebarState.expandedMenus };
        if (next[menuId]) {
            delete next[menuId];
        } else {
            next[menuId] = true;
        }
        this.sidebarState.expandedMenus = next;
    },

    onRootAppClick(app, ev) {
        ev.preventDefault();
        if (this.appHasSubMenus(app)) {
            const wasExpanded = this.isMenuExpanded(app.id);
            if (wasExpanded) {
                const next = { ...this.sidebarState.expandedMenus };
                delete next[app.id];
                this.sidebarState.expandedMenus = next;
            } else {
                this.sidebarState.expandedMenus = { [app.id]: true };
                this.menuService.setCurrentMenu(app);
                if (app.actionID) {
                    this.onNavBarDropdownItemSelection(app);
                }
            }
        } else if (app.actionID) {
            this.sidebarState.expandedMenus = {};
            this.onNavBarDropdownItemSelection(app);
        } else {
            this.menuService.setCurrentMenu(app);
        }
        if (this.ui.isSmall) {
            this.sidebarState.mobileOpen = false;
        }
    },

    onSubMenuToggle(menu, ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.toggleMenuExpand(menu.id);
    },

    onSubMenuClick(menu, ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (menu.actionID) {
            this.onNavBarDropdownItemSelection(menu);
        }
        if (this.ui.isSmall) {
            this.sidebarState.mobileOpen = false;
        }
    },

    toggleSidebarCollapse(ev) {
        if (ev) {
            ev.preventDefault();
        }
        this.sidebarState.collapsed = !this.sidebarState.collapsed;
    },

    toggleMobileSidebar(ev) {
        ev.preventDefault();
        this.sidebarState.mobileOpen = !this.sidebarState.mobileOpen;
    },

    closeMobileSidebar() {
        this.sidebarState.mobileOpen = false;
    },

    openThemePanel(ev, tabId = "general") {
        if (ev) {
            ev.preventDefault();
        }
        this.sidebarState.themePanelTab = tabId || "general";
        this.sidebarState.themePanelOpen = true;
    },

    openSidebarSizePanel(ev) {
        this.openThemePanel(ev, "sidebar_size");
    },

    closeThemePanel() {
        this.sidebarState.themePanelOpen = false;
        this.sidebarState.themePanelTab = "general";
    },

    onQuickDebug(ev) {
        ev.preventDefault();
        const debugBtn = document.querySelector(
            ".o_vpk_systray_secondary .o_debug_manager button, .o_vpk_systray_secondary .o_debug_manager .dropdown-toggle"
        );
        if (debugBtn) {
            debugBtn.click();
        }
    },

    onQuickEdit(ev) {
        ev.preventDefault();
        this.actionService.doAction("base.action_res_users_my");
    },

    onQuickNotes(ev) {
        ev.preventDefault();
        this.actionService.doAction("mail.action_discuss");
    },

});
