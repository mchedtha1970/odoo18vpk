/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { View } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class ProcurementInboxDashboard extends Component {
    static template = "vpk_procurement_inbox.ProcurementInboxDashboard";
    static components = { Layout, View };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            stats: {
                total: 0,
                unassigned: 0,
                mine: 0,
                overdue: 0,
                urgent: 0,
                has_urgency: false,
            },
            ready: false,
            activeFilter: "total",
        });
        this.viewProps = null;

        onWillStart(async () => {
            await this.reload();
        });
    }

    get display() {
        return { controlPanel: {} };
    }

    async reload() {
        const [stats, actionData] = await Promise.all([
            this.orm.call("purchase.request", "get_procurement_inbox_stats", [], {}),
            this.actionService.loadAction("vpk_procurement_inbox.action_procurement_inbox"),
        ]);
        this.state.stats = stats;
        await this._setViewProps(actionData, "total");
        this.state.ready = true;
    }

    async _setViewProps(actionData, filter) {
        const domain = await this.orm.call(
            "purchase.request",
            "get_procurement_inbox_domain",
            [filter],
            {}
        );
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
            domain,
            context: { ...actionData.context, lang: user.context.lang },
            display: { controlPanel: false },
            className: "o_vpk_procurement_inbox_dashboard_view",
        };
        this.state.activeFilter = filter;
    }

    async selectFilter(filter) {
        const actionData = await this.actionService.loadAction(
            "vpk_procurement_inbox.action_procurement_inbox"
        );
        await this._setViewProps(actionData, filter);
        this.viewProps = { ...this.viewProps };
    }

    openList() {
        const actionXml = {
            total: "vpk_procurement_inbox.action_procurement_inbox",
            unassigned: "vpk_procurement_inbox.action_procurement_inbox_unassigned",
            mine: "vpk_procurement_inbox.action_procurement_inbox_mine",
            overdue: "vpk_procurement_inbox.action_procurement_inbox_overdue",
            urgent: "vpk_procurement_inbox.action_procurement_inbox",
        }[this.state.activeFilter];
        this.actionService.doAction(actionXml);
    }
}

registry.category("actions").add("vpk_procurement_inbox_dashboard", ProcurementInboxDashboard);
