/** @odoo-module **/
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";

// OCA report_xlsx already handles report_type=xlsx via xlsx_handler.
// Keep this only as a fallback for the kit's legacy /xlsx_report route.
const handlers = registry.category("ir.actions.report handlers");
if (!handlers.contains("xlsx")) {
    handlers.add("xlsx", async (action, options, env) => {
        if (action.report_type !== "xlsx") {
            return false;
        }
        env.services.ui.block();
        try {
            await download({
                url: "/xlsx_report",
                data: action.data,
            });
        } finally {
            env.services.ui.unblock();
        }
        return true;
    });
}
