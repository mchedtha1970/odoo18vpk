/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { View } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export class PendingReviewDashboard extends Component {
    static template = "vpk_tier_validation.PendingReviewDashboard";
    static components = { Layout, View };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            count: 0,
            pendingCount: 0,
            approvedCount: 0,
            totalCount: 0,
            filter: "all",
            ready: false,
        });
        this.baseViewConfig = null;
        this.domains = {
            all: [],
            pending: [],
            approved: [],
        };

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        this.state.ready = false;
        const [counts, actionData] = await Promise.all([
            this.orm.call("tier.review", "get_my_review_counts", [], {}),
            this.actionService.loadAction(
                "vpk_tier_validation.action_vpk_my_pending_reviews"
            ),
        ]);
        this.state.pendingCount = counts.pending_count || 0;
        this.state.approvedCount = counts.approved_count || 0;
        this.state.totalCount = counts.total_count || 0;
        this.state.count = this.state.pendingCount;
        this.domains = {
            all: counts.all_domain || actionData.domain || [],
            pending: counts.pending_domain || [],
            approved: counts.approved_domain || [],
        };

        const viewMode = "kanban";
        const kanbanView = actionData.views.find((v) => v[1] === viewMode);
        const searchView = actionData.views.find((v) => v[1] === "search");
        this.baseViewConfig = {
            resModel: actionData.res_model,
            type: viewMode,
            viewId: kanbanView ? kanbanView[0] : false,
            views: [
                [kanbanView ? kanbanView[0] : false, viewMode],
                [searchView ? searchView[0] : false, "search"],
            ],
            context: { ...actionData.context, lang: user.context.lang },
            display: { controlPanel: false },
            className: "o_vpk_pending_review_dashboard_view",
        };
        this.state.ready = true;
    }

    get currentViewProps() {
        if (!this.baseViewConfig) {
            return null;
        }
        return {
            ...this.baseViewConfig,
            domain: this.domains[this.state.filter] || this.domains.all,
        };
    }

    get currentCount() {
        if (this.state.filter === "pending") {
            return this.state.pendingCount;
        }
        if (this.state.filter === "approved") {
            return this.state.approvedCount;
        }
        return this.state.totalCount;
    }

    setFilter(filterKey) {
        this.state.filter = filterKey;
    }

    get display() {
        return {
            controlPanel: {},
        };
    }

    openAllReviews() {
        this.actionService.doAction("vpk_tier_validation.action_vpk_my_pending_reviews");
    }

    openApprovedReviews() {
        this.actionService.doAction("vpk_tier_validation.action_vpk_my_approved_reviews");
    }
}

registry.category("actions").add("vpk_pending_review_dashboard", PendingReviewDashboard);
