/** @odoo-module **/

import { Component, EventBus, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { View } from "@web/views/view";
import { useBus, useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { ListController } from "@web/views/list/list_controller";
import { FormController } from "@web/views/form/form_controller";

const inboxBus = new EventBus();
const REFRESH_METHODS = new Set([
    "action_claim_procurement",
    "action_unclaim_procurement",
    "action_open_procurement_work",
]);

function notifyInboxChanged(controller, clickParams) {
    if (
        controller.props.resModel === "purchase.request" &&
        REFRESH_METHODS.has(clickParams?.name)
    ) {
        inboxBus.trigger("refresh");
    }
}

for (const Controller of [KanbanController, ListController, FormController]) {
    patch(Controller.prototype, {
        async afterExecuteActionButton(clickParams) {
            const result = await super.afterExecuteActionButton(...arguments);
            notifyInboxChanged(this, clickParams);
            return result;
        },
    });
}

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
                claimed: 0,
                mine: 0,
                overdue: 0,
                urgent: 0,
                has_urgency: false,
            },
            ready: false,
            activeFilter: "total",
        });
        this.viewProps = null;
        this.busService = useService("bus_service");
        this._onRemoteRefresh = () => this.scheduleRefresh();

        onWillStart(async () => {
            await this.reload();
        });
        onMounted(() => {
            this.busService.subscribe(
                "vpk_procurement_inbox/updated",
                this._onRemoteRefresh
            );
        });
        onWillUnmount(() => {
            this.busService.unsubscribe(
                "vpk_procurement_inbox/updated",
                this._onRemoteRefresh
            );
            clearTimeout(this._refreshTimer);
        });
        useBus(inboxBus, "refresh", () => this.scheduleRefresh());
    }

    scheduleRefresh() {
        if (!this.state.ready) {
            return;
        }
        clearTimeout(this._refreshTimer);
        this._refreshTimer = setTimeout(() => this.reload(), 80);
    }

    get display() {
        return { controlPanel: {} };
    }

    async reload() {
        const filter = this.state.activeFilter || "total";
        const [stats, actionData] = await Promise.all([
            this.orm.call("purchase.request", "get_procurement_inbox_stats", [], {}),
            this.actionService.loadAction("vpk_procurement_inbox.action_procurement_inbox"),
        ]);
        this.state.stats = stats;
        await this._setViewProps(actionData, filter);
        this.viewProps = { ...this.viewProps };
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
            claimed: "vpk_procurement_inbox.action_procurement_inbox_claimed",
            mine: "vpk_procurement_inbox.action_procurement_inbox_mine",
            overdue: "vpk_procurement_inbox.action_procurement_inbox_overdue",
            urgent: "vpk_procurement_inbox.action_procurement_inbox",
        }[this.state.activeFilter];
        this.actionService.doAction(actionXml);
    }
}

registry.category("actions").add("vpk_procurement_inbox_dashboard", ProcurementInboxDashboard);
