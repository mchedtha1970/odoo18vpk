/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";

export class VpkBudgetDashboard extends Component {
    static template = "vpk_budget.BudgetDashboard";
    static components = { Layout };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.openRequests = this.openRequests.bind(this);
        this.openRequest = this.openRequest.bind(this);
        this.onYearChange = this.onYearChange.bind(this);
        this.onDepartmentChange = this.onDepartmentChange.bind(this);
        this.state = useState({
            ready: false,
            departmentId: 0,
            data: {
                fiscal_year: "",
                year_options: [],
                department_id: 0,
                departments: [],
                cards: [],
                state_breakdown: [],
                category_breakdown: [],
                department_rows: [],
                recent_requests: [],
                allocation_gap: { rows: [], requested: 0, allocated: 0, gap: 0, percent: 0, max: 1 },
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    get display() {
        return { controlPanel: {} };
    }

    async loadData(fiscalYear = false, departmentId = undefined) {
        this.state.ready = false;
        const year = fiscalYear || this.state.data.fiscal_year;
        const department =
            departmentId === undefined ? this.state.departmentId : departmentId;
        this.state.data = await this.orm.call(
            "departmental.budget.request",
            "get_budget_dashboard_data",
            [],
            {
                fiscal_year: year || undefined,
                department_id: department || undefined,
            }
        );
        this.state.departmentId = this.state.data.department_id || 0;
        this.state.ready = true;
    }

    async onYearChange(ev) {
        await this.loadData(ev.target.value, this.state.departmentId);
    }

    async onDepartmentChange(ev) {
        await this.loadData(this.state.data.fiscal_year, Number(ev.target.value) || 0);
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
            return `${this.formatAmount(value / 1000000)}M`;
        }
        return this.formatAmount(value);
    }

    get gap() {
        return this.state.data.allocation_gap || { rows: [], max: 1 };
    }

    gapWidth(amount) {
        const max = this.gap.max || 1;
        const width = Math.max(0, Math.min(100, ((amount || 0) / max) * 100));
        return `width:${width}%;`;
    }

    categoryStyle() {
        const categories = this.state.data.category_breakdown || [];
        const total = categories.reduce((sum, item) => sum + (item.amount || 0), 0);
        if (!total) {
            return "background: #ece7dc;";
        }
        let start = 0;
        const stops = categories.map((item) => {
            const size = ((item.amount || 0) / total) * 100;
            const stop = `${item.color} ${start}% ${start + size}%`;
            start += size;
            return stop;
        });
        return `background: conic-gradient(${stops.join(", ")});`;
    }

    departmentDomain() {
        const departmentId = this.state.departmentId;
        if (!departmentId) {
            return [];
        }
        if (departmentId === -1) {
            return [["analytic_account_id", "=", false]];
        }
        return [["analytic_account_id", "=", departmentId]];
    }

    openRequests(domain = []) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "คำของบประมาณ",
            res_model: "departmental.budget.request",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["fiscal_year", "=", this.state.data.fiscal_year],
                ...this.departmentDomain(),
                ...domain,
            ],
        });
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
}

registry.category("actions").add("vpk_budget_dashboard", VpkBudgetDashboard);
