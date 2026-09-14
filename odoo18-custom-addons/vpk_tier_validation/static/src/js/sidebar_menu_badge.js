/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const BADGE_MENU_XMLIDS = new Set([
    "vpk_tier_validation.menu_vpk_tier_validation_root",
    "vpk_tier_validation.menu_vpk_my_pending_reviews",
    "vpk_tier_validation.menu_vpk_pending_review_dashboard",
]);

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.busService = useService("bus_service");
        this.pendingReviewBadge = useState({ count: 0 });
        this._vpkPendingReviewBusHandler = () => this._loadPendingReviewCount();
        onMounted(() => {
            this._loadPendingReviewCount();
            this.busService.subscribe(
                "base.tier.validation/updated",
                this._vpkPendingReviewBusHandler
            );
        });
        onWillUnmount(() => {
            this.busService.unsubscribe(
                "base.tier.validation/updated",
                this._vpkPendingReviewBusHandler
            );
        });
    },

    async _loadPendingReviewCount() {
        try {
            const count = await this.orm.call(
                "tier.review",
                "get_my_pending_count",
                [],
                {}
            );
            this.pendingReviewBadge.count = count;
        } catch (e) {
            console.error("VPK Tier: failed to load pending review count", e);
        }
    },

    getMenuBadge(menu) {
        const count = this.pendingReviewBadge?.count || 0;
        if (count && menu?.xmlid && BADGE_MENU_XMLIDS.has(menu.xmlid)) {
            return count;
        }
        return 0;
    },
});
