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
            fiscalYear: false,
            fundSourceId: 0,
            data: this._emptyData(),
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    get display() {
        return { controlPanel: false };
    }

    _emptyData() {
        return {
            fiscal_year: "",
            year_options: [],
            fund_source_id: 0,
            fund_sources: [],
            company_name: "",
            org_label: "",
            as_of_label: "",
            fy_end_label: "",
            remaining_days: 0,
            allocated: 0,
            actual: 0,
            committed: 0,
            remaining: 0,
            actual_pct: 0,
            committed_pct: 0,
            remaining_pct: 0,
            plan_pct: 0,
            vs_plan: 0,
            operating_pct: 0,
            investment_pct: 0,
            yoy_allocated_pct: 0,
            po_count: 0,
            expiring_count: 0,
            department_rows: [],
            expense_types: [],
            projects: [],
            project_total: 0,
            alerts: [],
            trend: {
                actual_points: [],
                committed_points: [],
                plan_points: [],
                max: 1,
                current_index: 0,
                q3_index: 8,
                q3_pct: 0,
            },
        };
    }

    async loadData(fiscalYear = false, fundSourceId = undefined) {
        this.state.ready = false;
        const year = fiscalYear === false ? this.state.fiscalYear : fiscalYear;
        const fund =
            fundSourceId === undefined ? this.state.fundSourceId : fundSourceId;
        this.state.data = await this.orm.call(
            "budget.budget",
            "get_annual_expenditure_overview",
            [],
            {
                fiscal_year: year || undefined,
                fund_source_id: fund || undefined,
            }
        );
        this.state.fiscalYear = this.state.data.fiscal_year;
        this.state.fundSourceId = this.state.data.fund_source_id || 0;
        this.state.ready = true;
    }

    async onYearChange(ev) {
        await this.loadData(ev.target.value, this.state.fundSourceId);
    }

    async onFundChange(ev) {
        await this.loadData(this.state.fiscalYear, Number(ev.target.value) || 0);
    }

    formatMillion(amount) {
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format((amount || 0) / 1000000);
    }

    formatMillionAxis(amount) {
        const value = (amount || 0) / 1000000;
        if (value >= 100) {
            return value.toFixed(0);
        }
        return value.toFixed(value >= 10 ? 0 : 1);
    }

    formatPercent(value, digits = 1) {
        return `${(value || 0).toFixed(digits)}%`;
    }

    usageWidth(value) {
        return `${Math.min(Math.max(value || 0, 0), 100)}%`;
    }

    abs(value) {
        return Math.abs(value || 0);
    }

    vsPlanLabel() {
        const gap = this.state.data.vs_plan || 0;
        if (gap >= 0) {
            return `สูงกว่าเป้า ${gap.toFixed(1)} จุด`;
        }
        return `ต่ำกว่าเป้า ${Math.abs(gap).toFixed(1)} จุด`;
    }

    yoyLabel(value) {
        const amount = value || 0;
        if (amount > 0) {
            return `เพิ่มขึ้นจากปีก่อน +${amount.toFixed(1)}%`;
        }
        if (amount < 0) {
            return `ลดลงจากปีก่อน ${amount.toFixed(1)}%`;
        }
        return "เทียบปีก่อนคงที่";
    }

    barWidth(row) {
        return this.usageWidth(row.usage_pct);
    }

    openBudgets() {
        this.actionService.doAction("base_account_budget.act_budget_view");
    }

    openBudgetLines() {
        this.actionService.doAction("base_account_budget.act_budget_lines_view");
    }

    openPurchaseOrders() {
        this.actionService.doAction("purchase.purchase_form_action");
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

    exportReport() {
        window.print();
    }

    get chartBox() {
        return { left: 46, top: 16, right: 628, bottom: 228, width: 582, height: 212 };
    }

    get yTicks() {
        const max = this.state.data.trend.max || 1;
        return [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const amount = max * ratio;
            const y = this.chartBox.bottom - ratio * this.chartBox.height;
            return { y, label: this.formatMillionAxis(amount) };
        });
    }

    _polyline(points) {
        const list = points || [];
        const max = this.state.data.trend.max || 1;
        const box = this.chartBox;
        return list
            .map((point, index) => {
                const x =
                    list.length <= 1
                        ? box.left
                        : box.left + (index / (list.length - 1)) * box.width;
                const y = box.bottom - ((point.amount || 0) / max) * box.height;
                return `${x},${y}`;
            })
            .join(" ");
    }

    get actualPolyline() {
        return this._polyline(this.state.data.trend.actual_points);
    }

    get committedPolyline() {
        return this._polyline(this.state.data.trend.committed_points);
    }

    get planPolyline() {
        return this._polyline(this.state.data.trend.plan_points);
    }

    get actualAreaPath() {
        const points = this.actualPolyline;
        if (!points) {
            return "";
        }
        const box = this.chartBox;
        return `M${box.left},${box.bottom} L${points} L${box.right},${box.bottom} Z`;
    }

    get currentPoint() {
        const points = this.state.data.trend.actual_points || [];
        const index = Math.min(
            this.state.data.trend.current_index || 0,
            Math.max(points.length - 1, 0)
        );
        if (!points.length) {
            return { x: 0, y: 0, visible: false, label: "" };
        }
        const max = this.state.data.trend.max || 1;
        const box = this.chartBox;
        const x =
            points.length <= 1
                ? box.left
                : box.left + (index / (points.length - 1)) * box.width;
        const y = box.bottom - ((points[index].amount || 0) / max) * box.height;
        return {
            x,
            y,
            visible: true,
            label: this.formatPercent(this.state.data.actual_pct),
        };
    }

    get q3Line() {
        const points = this.state.data.trend.actual_points || [];
        const index = Math.min(this.state.data.trend.q3_index || 8, 11);
        const box = this.chartBox;
        const x =
            points.length <= 1
                ? box.left
                : box.left + (index / Math.max(points.length - 1, 1)) * box.width;
        return { x, y1: box.top, y2: box.bottom };
    }
}

registry
    .category("actions")
    .add("vpk_budget_overview_dashboard", VpkBudgetOverviewDashboard);
