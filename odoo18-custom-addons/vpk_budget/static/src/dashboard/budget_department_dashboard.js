/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";

export class VpkBudgetDepartmentDashboard extends Component {
    static template = "vpk_budget.BudgetDepartmentDashboard";
    static components = { Layout };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            ready: false,
            fiscalYear: false,
            departmentId: false,
            data: {
                fiscal_year: "",
                year_options: [],
                departments: [],
                selected_department_id: 0,
                selected_department_name: "",
                cards: [],
                project_rows: [],
                category_breakdown: [],
                recent_requests: [],
            },
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    get display() {
        return { controlPanel: {} };
    }

    async loadData(fiscalYear = false, departmentId = false) {
        this.state.ready = false;
        this.state.data = await this.orm.call(
            "budget.budget",
            "get_department_budget_dashboard",
            [],
            {
                fiscal_year: fiscalYear || this.state.fiscalYear || undefined,
                department_id:
                    departmentId === false
                        ? this.state.departmentId || undefined
                        : departmentId,
            }
        );
        this.state.fiscalYear = this.state.data.fiscal_year;
        this.state.departmentId = this.state.data.selected_department_id;
        this.state.ready = true;
    }

    async onYearChange(ev) {
        this.state.fiscalYear = ev.target.value;
        await this.loadData(ev.target.value, this.state.departmentId);
    }

    async selectDepartment(departmentId) {
        this.state.departmentId = departmentId;
        await this.loadData(this.state.fiscalYear, departmentId);
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
        return `${(value || 0).toFixed(2)}%`;
    }

    formatDate(value) {
        if (!value) {
            return "";
        }
        return new Date(value).toLocaleDateString("th-TH");
    }

    usageWidth(value) {
        return `${Math.min(value || 0, 100)}%`;
    }

    cardValue(card) {
        if (card.is_percent) {
            return this.formatPercent(card.amount);
        }
        return `฿${this.formatAmount(card.amount)}`;
    }

    categoryStyle() {
        const items = this.state.data.category_breakdown || [];
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
}

registry
    .category("actions")
    .add("vpk_budget_department_dashboard", VpkBudgetDepartmentDashboard);
