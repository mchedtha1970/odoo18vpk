/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const MODEL = "vpk.document.studio.document";

export class PaymentRequestApDashboard extends Component {
    static template = "vpk_payment_request.ApDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            ready: false,
            busyId: false,
            filter: "wait_ap",
            search: "",
            data: { kpis: [], rows: [], waiting_purchase_send: 0, currency_symbol: "฿" },
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.data = await this.orm.call(MODEL, "get_payment_ap_dashboard", []);
        this.state.ready = true;
    }

    setFilter(key) {
        this.state.filter = key;
    }

    onSearch(ev) {
        this.state.search = ev.target.value || "";
    }

    get currentKpi() {
        return this.state.data.kpis.find((kpi) => kpi.key === this.state.filter);
    }

    get visibleRows() {
        const query = (this.state.search || "").trim().toLowerCase();
        return this.state.data.rows.filter((row) => {
            if (this.state.filter !== "all" && row.state !== this.state.filter) {
                return false;
            }
            if (!query) {
                return true;
            }
            return [row.name, row.po_name, row.vendor, row.wa, row.bill_name, row.state_label]
                .join(" ")
                .toLowerCase()
                .includes(query);
        });
    }

    formatMoney(value) {
        return (value || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    formatDate(value) {
        if (!value) {
            return "—";
        }
        const date = new Date(value.replace(" ", "T") + "Z");
        return date.toLocaleDateString("th-TH", {
            day: "numeric",
            month: "short",
            year: "2-digit",
        });
    }

    waitingLabel(row) {
        if (row.state === "to_finance") {
            return this.formatDate(row.finance_sent_on);
        }
        return row.waiting_days ? `${row.waiting_days} วัน` : "วันนี้";
    }

    async createBill(row) {
        await this.runRowAction(row, "action_create_ap_bill", true);
    }

    async openBill(row) {
        await this.runRowAction(row, "action_open_ap_bill", true);
    }

    sendToFinance(row) {
        this.dialog.add(ConfirmationDialog, {
            title: "ส่งการเงิน",
            body: `ส่ง ${row.name} (${row.vendor}) ให้การเงินทำรายการจ่าย?\nรายการจะไปรอที่ Dashboard การเงิน`,
            confirmLabel: "ส่งการเงิน",
            cancelLabel: "ยกเลิก",
            confirm: () =>
                this.runRowAction(row, "action_send_to_finance", false, "ส่งการเงินแล้ว รอทำจ่ายที่ Dashboard การเงิน"),
        });
    }

    async runRowAction(row, method, openResult, successMessage) {
        if (this.state.busyId) {
            return;
        }
        this.state.busyId = row.id;
        try {
            const result = await this.orm.call(MODEL, method, [[row.id]]);
            if (successMessage) {
                this.notification.add(`${row.name}: ${successMessage}`, { type: "success" });
            }
            if (openResult && result && result.type) {
                await this.actionService.doAction(result);
                return;
            }
            await this.loadData();
        } finally {
            this.state.busyId = false;
        }
    }

    openDocument(row) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.name,
            res_model: MODEL,
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPurchaseOrder(row) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.po_name,
            res_model: "purchase.order",
            res_id: row.po_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("vpk_payment_request_ap_dashboard", PaymentRequestApDashboard);
