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
const STORAGE_KEY = "vpk_procurement_inbox_view";
const REFRESH_METHODS = new Set([
    "action_claim_procurement",
    "action_unclaim_procurement",
    "action_open_procurement_work",
    "action_verify_procurement",
    "action_open_return_for_revision_wizard",
    "action_send_to_egp",
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

function loadViewPrefs() {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function saveViewPrefs(viewMode, groupBy) {
    try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ viewMode, groupBy }));
    } catch {
        // Ignore private-mode / quota errors.
    }
}

export class ProcurementInboxDashboard extends Component {
    static template = "vpk_procurement_inbox.ProcurementInboxDashboard";
    static components = { Layout, View };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        const prefs = loadViewPrefs();
        this.state = useState({
            stats: {
                total: 0,
                in_progress: 0,
                unassigned: 0,
                claimed: 0,
                mine: 0,
                overdue: 0,
                urgent: 0,
                amount_total: 0,
                has_urgency: false,
                by_department: [],
                by_method: [],
                by_owner: [],
                by_aging: [],
            },
            ready: false,
            activeFilter: "total",
            viewMode: prefs.viewMode || "board",
            groupBy: prefs.groupBy || "procurement_inbox_stage",
            extraFilter: { kind: null, id: null, label: "" },
        });
        this.viewProps = null;
        this.groupByOptions = [
            { value: "procurement_inbox_stage", label: "สถานะงาน" },
            { value: "department_id", label: "หน่วยงาน" },
            { value: "procurement_owner_id", label: "ผู้รับงาน" },
            { value: "procurement_method_id", label: "วิธีการจัดซื้อ" },
        ];
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

    get display() {
        return { controlPanel: {} };
    }

    get viewKey() {
        const extra = this.state.extraFilter || {};
        return [
            this.state.viewMode,
            this.state.groupBy,
            this.state.activeFilter,
            extra.kind || "",
            extra.id ?? "",
        ].join("|");
    }

    get extraFilterLabel() {
        return this.state.extraFilter?.label || "";
    }

    scheduleRefresh() {
        if (!this.state.ready) {
            return;
        }
        clearTimeout(this._refreshTimer);
        this._refreshTimer = setTimeout(() => this.reload(), 80);
    }

    async reload() {
        const filter = this.state.activeFilter || "total";
        const [stats, actionData] = await Promise.all([
            this.orm.call("purchase.request", "get_procurement_inbox_stats", [], {}),
            this.actionService.loadAction("vpk_procurement_inbox.action_procurement_inbox"),
        ]);
        this.state.stats = {
            by_department: [],
            by_method: [],
            by_owner: [],
            by_aging: [],
            amount_total: 0,
            ...stats,
        };
        await this._setViewProps(actionData, filter);
        this.viewProps = { ...this.viewProps };
        this.state.ready = true;
    }

    _groupByFields() {
        if (this.state.viewMode === "cards") {
            return [];
        }
        return this.state.groupBy ? [this.state.groupBy] : [];
    }

    async _setViewProps(actionData, filter) {
        const extra = this.state.extraFilter?.kind
            ? {
                  kind: this.state.extraFilter.kind,
                  id: this.state.extraFilter.id,
              }
            : {};
        const domain = await this.orm.call(
            "purchase.request",
            "get_procurement_inbox_domain",
            [filter],
            { extra }
        );
        const viewMode = this.state.viewMode === "list" ? "list" : "kanban";
        const selectedView = actionData.views.find((v) => v[1] === viewMode);
        const searchView = actionData.views.find((v) => v[1] === "search");
        this.viewProps = {
            resModel: actionData.res_model,
            type: viewMode,
            viewId: selectedView ? selectedView[0] : false,
            views: [
                [selectedView ? selectedView[0] : false, viewMode],
                [searchView ? searchView[0] : false, "search"],
            ],
            domain,
            groupBy: this._groupByFields(),
            context: { ...actionData.context, lang: user.context.lang },
            display: { controlPanel: false },
            className: "o_vpk_procurement_inbox_dashboard_view",
        };
        this.state.activeFilter = filter;
        saveViewPrefs(this.state.viewMode, this.state.groupBy);
    }

    async applyView() {
        const actionData = await this.actionService.loadAction(
            "vpk_procurement_inbox.action_procurement_inbox"
        );
        await this._setViewProps(actionData, this.state.activeFilter);
        this.viewProps = { ...this.viewProps };
    }

    async selectFilter(filter) {
        this.state.activeFilter = filter;
        await this.applyView();
    }

    async setViewMode(viewMode) {
        this.state.viewMode = viewMode;
        if (viewMode === "board" && !this.state.groupBy) {
            this.state.groupBy = "procurement_inbox_stage";
        }
        await this.applyView();
    }

    async onGroupByChange(ev) {
        this.state.groupBy = ev.target.value;
        if (this.state.viewMode === "cards") {
            this.state.viewMode = "board";
        }
        await this.applyView();
    }

    async selectBreakdown(kind, row) {
        const extra = this.state.extraFilter;
        if (extra.kind === kind && extra.id === row.id) {
            this.state.extraFilter = { kind: null, id: null, label: "" };
        } else {
            this.state.extraFilter = {
                kind,
                id: row.id,
                label: row.name,
            };
        }
        await this.applyView();
    }

    async clearExtraFilter() {
        this.state.extraFilter = { kind: null, id: null, label: "" };
        await this.applyView();
    }

    isBreakdownActive(kind, row) {
        return (
            this.state.extraFilter?.kind === kind &&
            this.state.extraFilter?.id === row.id
        );
    }

    barStyle(row, rows) {
        const max = Math.max(1, ...rows.map((item) => item.count || 0));
        const pct = Math.max(8, Math.round(((row.count || 0) / max) * 100));
        return `width: ${pct}%`;
    }

    formatAmount(value) {
        const amount = Number(value || 0);
        return amount.toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    openList() {
        const actionXml = {
            total: "vpk_procurement_inbox.action_procurement_inbox",
            in_progress: "vpk_procurement_inbox.action_procurement_inbox",
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
