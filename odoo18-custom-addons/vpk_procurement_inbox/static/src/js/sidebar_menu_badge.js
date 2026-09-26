/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const BADGE_MENU_XMLIDS = new Set([
    "vpk_procurement_inbox.menu_procurement_inbox_dashboard",
    "vpk_procurement_inbox.menu_procurement_inbox_dashboard_pr",
    "vpk_tier_validation.menu_purchase_request_sent_to_procurement",
    "vpk_tier_validation.menu_purchase_request_sent_to_procurement_purchase",
]);

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.procurementInboxBadge = useState({ count: 0 });
        this._vpkProcurementInboxTimer = null;
        onMounted(() => {
            this._loadProcurementInboxCount();
            this._vpkProcurementInboxTimer = setInterval(
                () => this._loadProcurementInboxCount(),
                60000
            );
        });
        onWillUnmount(() => {
            if (this._vpkProcurementInboxTimer) {
                clearInterval(this._vpkProcurementInboxTimer);
            }
        });
    },

    async _loadProcurementInboxCount() {
        try {
            const count = await this.orm.call(
                "purchase.request",
                "get_procurement_inbox_count",
                [],
                {}
            );
            this.procurementInboxBadge.count = count;
        } catch (e) {
            // module may not be loaded yet for every user
        }
    },

    getMenuBadge(menu) {
        const count = this.procurementInboxBadge?.count || 0;
        if (count && menu?.xmlid && BADGE_MENU_XMLIDS.has(menu.xmlid)) {
            return count;
        }
        return super.getMenuBadge(menu);
    },
});
