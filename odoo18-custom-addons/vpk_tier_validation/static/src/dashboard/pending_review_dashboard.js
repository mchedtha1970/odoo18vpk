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
            ready: false,
        });
        this.viewProps = null;

        onWillStart(async () => {
            const [count, actionData] = await Promise.all([
                this.orm.call("tier.review", "get_my_pending_count", [], {}),
                this.actionService.loadAction(
                    "vpk_tier_validation.action_vpk_my_pending_reviews"
                ),
            ]);
            this.state.count = count;

            const viewMode = "kanban";
            const kanbanView = actionData.views.find((v) => v[1] === viewMode);
            const searchView = actionData.views.find((v) => v[1] === "search");
            this.viewProps = {
                resModel: actionData.res_model,
                type: viewMode,
                viewId: kanbanView ? kanbanView[0] : false,
                views: [
                    [kanbanView ? kanbanView[0] : false, viewMode],
                    [searchView ? searchView[0] : false, "search"],
                ],
                domain: actionData.domain || [],
                context: { ...actionData.context, lang: user.context.lang },
                display: { controlPanel: false },
                className: "o_vpk_pending_review_dashboard_view",
            };
            this.state.ready = true;
        });
    }

    get display() {
        return {
            controlPanel: {},
        };
    }

    openAllReviews() {
        this.actionService.doAction("vpk_tier_validation.action_vpk_my_pending_reviews");
    }
}

registry.category("actions").add("vpk_pending_review_dashboard", PendingReviewDashboard);
