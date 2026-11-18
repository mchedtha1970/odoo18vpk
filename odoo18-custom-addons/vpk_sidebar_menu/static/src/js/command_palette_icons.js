/** @odoo-module **/

import { registry } from "@web/core/registry";
import "@web/webclient/menus/menu_providers";
import { getAppLineIcon } from "./line_icons";

const providers = registry.category("command_provider");
const menuProvider = providers.get("menu");

providers.add(
    "menu",
    {
        ...menuProvider,
        async provide(env, options) {
            const result = await menuProvider.provide(env, options);
            const appsByName = new Map(env.services.menu.getApps().map((app) => [app.name, app]));
            for (const command of result) {
                const app = command.category === "apps" && appsByName.get(command.name);
                if (app) {
                    command.props = {
                        webIcon: { iconClass: `vpk-li vpk-li-${getAppLineIcon(app)}` },
                    };
                }
            }
            return result;
        },
    },
    { force: true }
);
