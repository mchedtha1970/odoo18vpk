/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { PlChart } from "./pl_chart";

const COLORS = {
    blue: "#2f80ed",
    teal: "#0f766e",
    green: "#006442",
    amber: "#d97706",
    rose: "#b42318",
    gray: "#94a3b8",
    grayDark: "#64748b",
    violet: "#7c3aed",
    cyan: "#0891b2",
};

const DONUT_PALETTE = [COLORS.blue, COLORS.teal, COLORS.amber, COLORS.violet, COLORS.cyan, COLORS.rose];

export class VpkPlPerformanceDashboard extends Component {
    static template = "vpk_hospital_balance_sheet.PlPerformanceDashboard";
    static components = { Layout, PlChart };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            ready: false,
            tab: "overview",
            compare: true,
            fiscalYear: false,
            analyticId: 0,
            data: this.emptyData(),
        });
        onWillStart(() => this.loadData());
    }

    get display() {
        return { controlPanel: false };
    }

    emptyData() {
        return {
            fiscal_year: "",
            fiscal_year_be: null,
            compare_year: null,
            compare_year_be: null,
            compare: false,
            year_options: [],
            year_option_labels: [],
            analytic_id: 0,
            analytics: [{ id: 0, name: "ทุกหน่วยงาน" }],
            as_of_label: "",
            period_label: "",
            company_name: "",
            unposted_count: 0,
            kpis: {},
            revenue_structure: [],
            expense_structure: [],
            lines: [],
            prev_lines: [],
            yoy_categories: [],
            months: [],
            months_prev: [],
            departments: [],
            report_action_xmlid: "vpk_hospital_balance_sheet.action_profit_and_loss",
        };
    }

    async loadData(fiscalYear = undefined, compare = undefined, analyticId = undefined) {
        this.state.ready = false;
        const year = fiscalYear === undefined ? this.state.fiscalYear : fiscalYear;
        const cmp = compare === undefined ? this.state.compare : compare;
        const analytic = analyticId === undefined ? this.state.analyticId : analyticId;
        this.state.data = await this.orm.call(
            "account.report",
            "get_pl_dashboard_data",
            [],
            {
                fiscal_year: year || undefined,
                compare: cmp,
                analytic_id: analytic || undefined,
            }
        );
        this.state.fiscalYear = this.state.data.fiscal_year;
        this.state.compare = this.state.data.compare;
        this.state.analyticId = this.state.data.analytic_id || 0;
        this.state.ready = true;
    }

    onYearChange(ev) {
        this.loadData(Number(ev.target.value), this.state.compare, this.state.analyticId);
    }

    onAnalyticChange(ev) {
        this.loadData(this.state.fiscalYear, this.state.compare, Number(ev.target.value) || 0);
    }

    onCompareToggle(ev) {
        this.loadData(this.state.fiscalYear, Boolean(ev.target.checked), this.state.analyticId);
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    formatBaht(value) {
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value || 0);
    }

    formatMillion(value) {
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 1,
            maximumFractionDigits: 1,
        }).format((value || 0) / 1000000);
    }

    formatPct(value, digits = 1) {
        if (value === null || value === undefined) {
            return "—";
        }
        const sign = value > 0 ? "+" : "";
        return `${sign}${Number(value).toFixed(digits)}%`;
    }

    yoyClass(value) {
        if (value === null || value === undefined || value === 0) {
            return "is-flat";
        }
        return value > 0 ? "is-up" : "is-down";
    }

    lineKindClass(kind) {
        if (kind === "revenue_total" || kind === "expense_total") {
            return "is-total";
        }
        if (kind === "result") {
            return "is-result";
        }
        return "";
    }

    openFullReport() {
        this.actionService.doAction(this.state.data.report_action_xmlid);
    }

    filterByDepartment(departmentId) {
        if (!departmentId || departmentId < 0) {
            return;
        }
        this.loadData(this.state.fiscalYear, this.state.compare, departmentId);
        this.state.tab = "overview";
    }

    toMillion(value) {
        return Math.round(((value || 0) / 1000000) * 10) / 10;
    }

    // ----- Chart.js configs -------------------------------------------------

    get revenueDonutLabels() {
        return (this.state.data.revenue_structure || []).map((r) => r.label);
    }

    get revenueDonutDatasets() {
        const rows = this.state.data.revenue_structure || [];
        return [
            {
                label: "รายได้",
                data: rows.map((r) => this.toMillion(r.amount)),
                backgroundColor: rows.map((_, i) => DONUT_PALETTE[i % DONUT_PALETTE.length]),
                hoverOffset: 10,
            },
        ];
    }

    get revenueDonutCenter() {
        const total = (this.state.data.revenue_structure || []).reduce(
            (sum, r) => sum + Math.abs(r.amount || 0),
            0
        );
        return `${this.formatMillion(total)}\nล้านบาท`;
    }

    get expenseDonutLabels() {
        return (this.state.data.expense_structure || []).map((r) => r.label);
    }

    get expenseDonutDatasets() {
        const rows = this.state.data.expense_structure || [];
        return [
            {
                label: "ค่าใช้จ่าย",
                data: rows.map((r) => this.toMillion(r.amount)),
                backgroundColor: rows.map((_, i) => DONUT_PALETTE[i % DONUT_PALETTE.length]),
                hoverOffset: 10,
            },
        ];
    }

    get expenseDonutCenter() {
        const total = (this.state.data.expense_structure || []).reduce(
            (sum, r) => sum + Math.abs(r.amount || 0),
            0
        );
        return `${this.formatMillion(total)}\nล้านบาท`;
    }

    get monthLabels() {
        return (this.state.data.months || []).map((m) => m.label);
    }

    get monthlyLineDatasets() {
        const months = this.state.data.months || [];
        const datasets = [
            {
                label: `รายได้ ${this.state.data.fiscal_year_be || this.state.data.fiscal_year}`,
                data: months.map((m) => this.toMillion(m.revenue)),
                borderColor: COLORS.blue,
                backgroundColor: "rgba(47, 128, 237, 0.12)",
                fill: true,
            },
            {
                label: `ค่าใช้จ่าย ${this.state.data.fiscal_year_be || this.state.data.fiscal_year}`,
                data: months.map((m) => this.toMillion(m.expense)),
                borderColor: COLORS.amber,
                backgroundColor: "rgba(217, 119, 6, 0.10)",
                fill: true,
            },
        ];
        if (this.state.data.compare && (this.state.data.months_prev || []).length) {
            datasets.push(
                {
                    label: `รายได้ ${this.state.data.compare_year_be || this.state.data.compare_year}`,
                    data: (this.state.data.months_prev || []).map((m) => this.toMillion(m.revenue)),
                    borderColor: COLORS.gray,
                    borderDash: [6, 4],
                    fill: false,
                },
                {
                    label: `ค่าใช้จ่าย ${this.state.data.compare_year_be || this.state.data.compare_year}`,
                    data: (this.state.data.months_prev || []).map((m) => this.toMillion(m.expense)),
                    borderColor: COLORS.grayDark,
                    borderDash: [6, 4],
                    fill: false,
                }
            );
        }
        return datasets;
    }

    get netBarDatasets() {
        const months = this.state.data.months || [];
        return [
            {
                label: "ผลสุทธิ",
                data: months.map((m) => this.toMillion(m.net)),
                backgroundColor: months.map((m) =>
                    (m.net || 0) >= 0 ? COLORS.green : COLORS.rose
                ),
            },
        ];
    }

    get yoySummaryLabels() {
        return ["รายได้", "ค่าใช้จ่าย", "ผลสุทธิ"];
    }

    get yoySummaryDatasets() {
        const k = this.state.data.kpis || {};
        return [
            {
                label: `ปีงบ ${this.state.data.compare_year_be || this.state.data.compare_year || ""}`,
                data: [
                    this.toMillion(k.prev_revenue),
                    this.toMillion(k.prev_expense),
                    this.toMillion(k.prev_net),
                ],
                backgroundColor: COLORS.gray,
            },
            {
                label: `ปีงบ ${this.state.data.fiscal_year_be || this.state.data.fiscal_year || ""}`,
                data: [
                    this.toMillion(k.revenue),
                    this.toMillion(k.expense),
                    this.toMillion(k.net),
                ],
                backgroundColor: COLORS.blue,
            },
        ];
    }

    get yoyCategoryLabels() {
        return (this.state.data.yoy_categories || []).map((r) => r.label);
    }

    get yoyCategoryDatasets() {
        const rows = this.state.data.yoy_categories || [];
        return [
            {
                label: `ปีงบ ${this.state.data.compare_year_be || this.state.data.compare_year || ""}`,
                data: rows.map((r) => this.toMillion(r.previous)),
                backgroundColor: COLORS.gray,
            },
            {
                label: `ปีงบ ${this.state.data.fiscal_year_be || this.state.data.fiscal_year || ""}`,
                data: rows.map((r) => this.toMillion(r.current)),
                backgroundColor: COLORS.teal,
            },
        ];
    }

    get departmentLabels() {
        return (this.state.data.departments || []).map((d) => d.name);
    }

    get departmentDatasets() {
        const depts = this.state.data.departments || [];
        return [
            {
                label: "รายได้",
                data: depts.map((d) => this.toMillion(d.revenue)),
                backgroundColor: COLORS.blue,
            },
            {
                label: "ค่าใช้จ่าย",
                data: depts.map((d) => this.toMillion(d.expense)),
                backgroundColor: COLORS.amber,
            },
        ];
    }

    onDepartmentChartClick(payload) {
        const dept = (this.state.data.departments || [])[payload.index];
        if (dept) {
            this.filterByDepartment(dept.id);
        }
    }
}

registry.category("actions").add("vpk_pl_performance_dashboard", VpkPlPerformanceDashboard);
