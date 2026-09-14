/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { AlignPlugin } from "@html_editor/main/align_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

const ALIGN_TOOLBAR_GROUPS = [
    withSequence(21, { id: "align" }),
    withSequence(22, { id: "indent" }),
];

const ALIGN_TOOLBAR_ITEMS = [
    {
        id: "align_left",
        groupId: "align",
        commandId: "alignLeft",
        title: _t("Align Left"),
        icon: "fa-align-left",
    },
    {
        id: "align_center",
        groupId: "align",
        commandId: "alignCenter",
        title: _t("Align Center"),
        icon: "fa-align-center",
    },
    {
        id: "align_right",
        groupId: "align",
        commandId: "alignRight",
        title: _t("Align Right"),
        icon: "fa-align-right",
    },
    {
        id: "indent",
        groupId: "indent",
        commandId: "tab",
        title: _t("Increase Indent"),
        icon: "fa-indent",
    },
    {
        id: "outdent",
        groupId: "indent",
        commandId: "shiftTab",
        title: _t("Decrease Indent"),
        icon: "fa-outdent",
    },
];

class VpkAlignPlugin extends AlignPlugin {
    static id = "align";
    static dependencies = ["selection"];

    resources = {
        user_commands: [
            { id: "alignLeft", run: () => this.align("left") },
            { id: "alignRight", run: () => this.align("right") },
            { id: "alignCenter", run: () => this.align("center") },
        ],
        toolbar_groups: ALIGN_TOOLBAR_GROUPS,
        toolbar_items: ALIGN_TOOLBAR_ITEMS,
    };
}

class MemoToolbarFallbackPlugin extends Plugin {
    static id = "memoToolbarFallback";

    resources = {
        toolbar_groups: ALIGN_TOOLBAR_GROUPS,
        toolbar_items: ALIGN_TOOLBAR_ITEMS,
    };
}

function installAlignToolbar() {
    const alignPluginIndex = MAIN_PLUGINS.findIndex((pluginClass) => pluginClass.id === "align");
    if (alignPluginIndex >= 0) {
        MAIN_PLUGINS[alignPluginIndex] = VpkAlignPlugin;
        return;
    }
    const toolbarPluginIndex = MAIN_PLUGINS.findIndex((pluginClass) => pluginClass.id === "toolbar");
    const insertAt = toolbarPluginIndex >= 0 ? toolbarPluginIndex : MAIN_PLUGINS.length;
    MAIN_PLUGINS.splice(insertAt, 0, MemoToolbarFallbackPlugin);
}

installAlignToolbar();
