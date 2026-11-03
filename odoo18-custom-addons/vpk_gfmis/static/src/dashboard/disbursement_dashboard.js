/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";

const FILTERS = [
    { key: "all", label: "ทั้งหมด" },
    { key: "progress", label: "กำลังดำเนินการ" },
    { key: "approve", label: "รออนุมัติ" },
    { key: "done", label: "จ่ายแล้ว" },
    { key: "draft", label: "ร่าง" },
];

export class VpkDisbursementDashboard extends Component {
    static template = "vpk_gfmis.DisbursementDashboard";
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
            documents: [],
            waiting: [],
            open_stage_count: 0,
        };
    }

    async loadData(fiscalYear = false) {
        this.state.ready = false;
        this.state.data = await this.orm.call(
            "gfmis.document",
            "get_disbursement_dashboard_data",
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
        return `background: conic-gradient(#0f766e ${pct}%, #e6ebf2 ${pct}%);`;
    }

    filterCount(key) {
        const documents = this.state.data.documents || [];
        if (key === "all") {
            return documents.filter((item) => item.status_key !== "cancel").length;
        }
        return documents.filter((item) => item.status_key === key).length;
    }

    get filters() {
        return FILTERS;
    }

    get visibleDocuments() {
        const query = (this.state.search || "").trim().toLowerCase();
        return (this.state.data.documents || []).filter((item) => {
            const statusOk = this.state.filter === "all"
                ? item.status_key !== "cancel"
                : item.status_key === this.state.filter;
            if (!statusOk) {
                return false;
            }
            if (!query) {
                return true;
            }
            return [
                item.name,
                item.po_name,
                item.vendor,
                item.form,
                item.reference,
                item.status_label,
            ]
                .join(" ")
                .toLowerCase()
                .includes(query);
        });
    }

    dots(item) {
        return [0, 1, 2, 3, 4].map((index) => {
            if (index < item.stage_index) {
                return "done";
            }
            if (index === item.stage_index) {
                return item.status_key === "done" ? "done" : "current";
            }
            return "todo";
        });
    }

    openDocument(documentId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "ใบเบิกเงิน",
            res_model: "gfmis.document",
            res_id: documentId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPurchaseOrder(orderId, ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "ใบสั่งซื้อ",
            res_model: "purchase.order",
            res_id: orderId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    createDocument() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "ใบเบิกเงิน",
            res_model: "gfmis.document",
            views: [[false, "form"]],
            context: { default_doc_class: "request" },
            target: "current",
        });
    }
}

registry.category("actions").add("vpk_disbursement_dashboard", VpkDisbursementDashboard);
