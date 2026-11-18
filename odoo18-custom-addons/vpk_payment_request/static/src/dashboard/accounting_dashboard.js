/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const MODEL = "account.payment";

export class PaymentAccountingDashboard extends Component {
    static template = "vpk_payment_request.AccountingDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            ready: false,
            busyId: false,
            search: "",
            data: { kpis: [], rows: [] },
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.data = await this.orm.call(MODEL, "get_payment_accounting_dashboard", []);
        this.state.ready = true;
    }

    onSearch(ev) {
        this.state.search = ev.target.value || "";
    }

    get currentKpi() {
        return this.state.data.kpis[0];
    }

    get visibleRows() {
        const query = (this.state.search || "").trim().toLowerCase();
        return this.state.data.rows.filter((row) => {
            if (!query) {
                return true;
            }
            return [
                row.name,
                row.vendor,
                row.bill_name,
                row.po_name,
                row.wa_name,
                row.contract_name,
                row.request_name,
                row.journal,
                row.method,
            ]
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
        const date = new Date(value.replace(" ", "T") + (value.length > 10 ? "Z" : ""));
        return date.toLocaleDateString("th-TH", {
            day: "numeric",
            month: "short",
            year: "2-digit",
        });
    }

    openPayment(row) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.name || "รายการชำระเงิน",
            res_model: MODEL,
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    postPayment(row) {
        this.dialog.add(ConfirmationDialog, {
            title: "บันทึกบัญชี",
            body: `บันทึก (POST) รายการชำระเงิน ${row.name || ""} ของ ${row.vendor} จำนวน ฿${this.formatMoney(row.amount)}?`,
            confirmLabel: "บันทึกบัญชี",
            cancelLabel: "ยกเลิก",
            confirm: () => this._doPost(row),
        });
    }

    async _doPost(row) {
        if (this.state.busyId) {
            return;
        }
        this.state.busyId = row.id;
        try {
            const result = await this.orm.call(MODEL, "action_accounting_post_payment", [[row.id]]);
            this.notification.add(`${row.name || row.vendor}: บันทึกบัญชีแล้ว`, { type: "success" });
            if (result && result.type && result.tag !== "display_notification") {
                await this.actionService.doAction(result);
            }
            await this.loadData();
        } finally {
            this.state.busyId = false;
        }
    }
}

registry
    .category("actions")
    .add("vpk_payment_request_accounting_dashboard", PaymentAccountingDashboard);
