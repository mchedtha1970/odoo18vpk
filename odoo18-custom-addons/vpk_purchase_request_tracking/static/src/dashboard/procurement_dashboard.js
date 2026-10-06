/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";

const FILTERS = [
    { key: "all", label: "ทั้งหมด" },
    { key: "progress", label: "กำลังดำเนินการ" },
    { key: "late", label: "ล่าช้า" },
    { key: "approve", label: "รออนุมัติ" },
    { key: "done", label: "เสร็จสิ้น" },
];

export class VpkProcurementDashboard extends Component {
    static template = "vpk_purchase_request_tracking.ProcurementDashboard";
    static components = { Layout };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            ready: false,
            tab: "overview",
            filter: "all",
            search: "",
            data: this.emptyData(),
        });
        onWillStart(() => this.loadData());
    }

    get display() {
        return { controlPanel: {} };
    }

    emptyData() {
        return {
            fiscal_year: "",
            year_options: [],
            as_of_label: "",
            kpis: {},
            stages: [],
            quarters: [],
            quarter_max: 1,
            methods: [],
            alerts: [],
            projects: [],
            project_total: 0,
            contracts: [],
            open_stage_count: 0,
        };
    }

    async loadData(fiscalYear = false) {
        this.state.ready = false;
        this.state.data = await this.orm.call(
            "purchase.request",
            "get_procurement_dashboard_data",
            [],
            { fiscal_year: fiscalYear || undefined }
        );
        this.state.ready = true;
    }

    onYearChange(ev) {
        this.loadData(ev.target.value);
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    setFilter(key) {
        this.state.filter = key;
    }

    onSearch(ev) {
        this.state.search = ev.target.value || "";
    }

    formatCount(value) {
        return new Intl.NumberFormat("th-TH").format(value || 0);
    }

    formatBaht(value) {
        return new Intl.NumberFormat("th-TH", {
            maximumFractionDigits: 0,
        }).format(value || 0);
    }

    formatMillion(value) {
        const amount = value || 0;
        if (Math.abs(amount) >= 1000000) {
            return `${new Intl.NumberFormat("th-TH", {
                maximumFractionDigits: 1,
            }).format(amount / 1000000)} ล้าน`;
        }
        return this.formatBaht(amount);
    }

    formatSigned(value) {
        const amount = value || 0;
        const sign = amount > 0 ? "+" : "";
        return `${sign}${this.formatCount(amount)}`;
    }

    barHeight(amount) {
        const max = this.state.data.quarter_max || 1;
        return `${Math.max((amount || 0) / max * 100, amount ? 4 : 0)}%`;
    }

    methodWidth(item) {
        return `${Math.max(item.width || 0, item.amount ? 4 : 0)}%`;
    }

    stageWidth(item) {
        return `${Math.max(item.width || 0, item.count ? 6 : 0)}%`;
    }

    paidStyle() {
        const pct = Math.max(0, Math.min(this.state.data.kpis.paid_pct || 0, 100));
        return `background: conic-gradient(#1e3a5f ${pct}%, #e6ebf2 ${pct}%);`;
    }

    filterCount(key) {
        const projects = this.state.data.projects || [];
        if (key === "all") {
            return this.state.data.project_total || projects.length;
        }
        return projects.filter((project) => project.status_key === key).length;
    }

    get visibleProjects() {
        const query = (this.state.search || "").trim().toLowerCase();
        return (this.state.data.projects || []).filter((project) => {
            const statusOk = this.state.filter === "all" || project.status_key === this.state.filter;
            if (!statusOk) {
                return false;
            }
            if (!query) {
                return true;
            }
            return [project.name, project.description, project.department, project.method]
                .join(" ")
                .toLowerCase()
                .includes(query);
        });
    }

    get filters() {
        return FILTERS;
    }

    openProject(projectId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "purchase.request",
            res_id: projectId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    createRequest() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "คำขอซื้อ/จ้าง",
            res_model: "purchase.request",
            views: [[false, "form"]],
            target: "current",
        });
    }

    exportReport() {
        this.actionService.doAction("vpk_purchase_request_tracking.action_pr_po_report_export_wizard");
    }

    dots(project) {
        return [0, 1, 2, 3, 4, 5, 6].map((index) => {
            if (index < project.stage_index) {
                return "done";
            }
            if (index === project.stage_index) {
                return project.status_key === "done" ? "done" : "current";
            }
            return "todo";
        });
    }
}

registry.category("actions").add("vpk_procurement_dashboard", VpkProcurementDashboard);
