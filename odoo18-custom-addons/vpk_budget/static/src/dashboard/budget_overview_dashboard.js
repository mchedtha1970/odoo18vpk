/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";

export class VpkBudgetOverviewDashboard extends Component {
    static template = "vpk_budget.BudgetOverviewDashboard";
    static components = { Layout };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            ready: false,
            data: {
                fiscal_year: "",
                year_options: [],
                cards: [],
                form_kpis: [],
                form_breakdown: [],
                allocation_breakdown: [],
                department_rows: [],
                recent_requests: [],
                trend: { actual_points: [], plan_points: [], max: 1 },
            },
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    get display() {
        return { controlPanel: {} };
    }

    async loadData(fiscalYear = false) {
        this.state.ready = false;
        this.state.data = await this.orm.call(
            "budget.budget",
            "get_annual_expenditure_overview",
            [],
            { fiscal_year: fiscalYear || undefined }
        );
        this.state.ready = true;
    }

    async onYearChange(ev) {
        await this.loadData(ev.target.value);
    }

    formatAmount(amount) {
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount || 0);
    }

    formatShortAmount(amount) {
        const value = amount || 0;
        if (Math.abs(value) >= 1000000) {
            return `${(value / 1000000).toFixed(value % 1000000 === 0 ? 0 : 1)}M`;
        }
        return this.formatAmount(value);
    }

    formatPercent(value) {
        return `${(value || 0).toFixed(1)}%`;
    }

    usageWidth(value) {
        return `${Math.min(value || 0, 100)}%`;
    }

    formatDate(value) {
        if (!value) {
            return "";
        }
        const date = new Date(value);
        return date.toLocaleDateString("th-TH");
    }

    allocationStyle() {
        const items = this.state.data.allocation_breakdown || [];
        return this._donutStyle(items);
    }

    formBreakdownStyle() {
        const items = this.state.data.form_breakdown || [];
        return this._donutStyle(items);
    }

    _donutStyle(items) {
        const total = items.reduce((sum, item) => sum + (item.amount || 0), 0);
        if (!total) {
            return "background: #e5e7eb;";
        }
        let start = 0;
        const stops = items.map((item) => {
            const size = ((item.amount || 0) / total) * 100;
            const stop = `${item.color} ${start}% ${start + size}%`;
            start += size;
            return stop;
        });
        return `background: conic-gradient(${stops.join(", ")});`;
    }

    openFormRequests(formTypeId) {
        const domain = [["fiscal_year", "=", this.state.data.fiscal_year]];
        if (formTypeId) {
            domain.push(["form_type_id", "=", formTypeId]);
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "คำของบประมาณ",
            res_model: "departmental.budget.request",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
        });
    }

    trendPoint(points, index, amount) {
        const max = this.state.data.trend.max || 1;
        const x = points.length <= 1 ? 0 : (index / (points.length - 1)) * 100;
        const y = 100 - ((amount || 0) / max) * 100;
        return `${x},${y}`;
    }

    get actualPolyline() {
        const points = this.state.data.trend.actual_points || [];
        return points
            .map((point, index) => this.trendPoint(points, index, point.amount))
            .join(" ");
    }

    get planPolyline() {
        const points = this.state.data.trend.plan_points || [];
        return points
            .map((point, index) => this.trendPoint(points, index, point.amount))
            .join(" ");
    }

    get actualAreaPath() {
        const points = this.state.data.trend.actual_points || [];
        if (!points.length) {
            return "";
        }
        return `M0,100 L${this.actualPolyline} L100,100 Z`;
    }

    openBudgets() {
        this.actionService.doAction("base_account_budget.act_budget_view");
    }

    openBudgetLines() {
        this.actionService.doAction("base_account_budget.act_budget_lines_view");
    }

    openRequest(requestId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "คำของบประมาณ",
            res_model: "departmental.budget.request",
            res_id: requestId,
            views: [[false, "form"]],
        });
    }

    openRequests() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "คำของบประมาณ",
            res_model: "departmental.budget.request",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [["fiscal_year", "=", this.state.data.fiscal_year]],
        });
    }
}

registry
    .category("actions")
    .add("vpk_budget_overview_dashboard", VpkBudgetOverviewDashboard);
