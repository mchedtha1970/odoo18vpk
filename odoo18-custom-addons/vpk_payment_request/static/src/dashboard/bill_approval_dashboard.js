/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const MODEL = "account.move";
const PROMPT_FONT_ID = "vpk-flow-prompt-font";
const PROMPT_FONT_URL =
    "https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap";

function ensurePromptFont() {
    if (document.getElementById(PROMPT_FONT_ID)) {
        return;
    }
    const link = document.createElement("link");
    link.id = PROMPT_FONT_ID;
    link.rel = "stylesheet";
    link.href = PROMPT_FONT_URL;
    document.head.appendChild(link);
}

export class BillApprovalDashboard extends Component {
    static template = "vpk_payment_request.BillApprovalDashboard";
    static props = ["*"];

    setup() {
        ensurePromptFont();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            ready: false,
            busyId: false,
            filter: "pending",
            search: "",
            data: { kpis: [], rows: [], currency_symbol: "฿" },
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.data = await this.orm.call(MODEL, "get_ap_bill_approval_dashboard", []);
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
            return [
                row.name,
                row.ref,
                row.request_name,
                row.po_name,
                row.wa_name,
                row.vendor,
                row.approver_names,
                row.state_label,
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

    openBill(row) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.name || "ใบเรียกเก็บ",
            res_model: "account.move",
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRequest(row) {
        if (!row.request_id) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.request_name || "ใบขออนุมัติเบิกจ่าย",
            res_model: "vpk.document.studio.document",
            res_id: row.request_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPurchaseOrder(row) {
        if (!row.po_id) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.po_name || "ใบสั่งซื้อ",
            res_model: "purchase.order",
            res_id: row.po_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    approveBill(row) {
        this.dialog.add(ConfirmationDialog, {
            title: "อนุมัติตั้งเจ้าหนี้",
            body: `ยืนยันอนุมัติใบเรียกเก็บ ${row.name} (${row.vendor}) จำนวน ฿${this.formatMoney(row.amount)}?`,
            confirmLabel: "อนุมัติตั้งเจ้าหนี้",
            cancelLabel: "ยกเลิก",
            confirm: () =>
                this._runBillAction(
                    row,
                    "action_accounting_approve_bill",
                    `${row.name}: บัญชีอนุมัติแล้ว`
                ),
        });
    }

    rejectBill(row) {
        this.dialog.add(ConfirmationDialog, {
            title: "ไม่อนุมัติตั้งเจ้าหนี้",
            body: `ยืนยันไม่อนุมัติใบเรียกเก็บ ${row.name} (${row.vendor})?`,
            confirmLabel: "ไม่อนุมัติ",
            cancelLabel: "ยกเลิก",
            confirm: () =>
                this._runBillAction(
                    row,
                    "action_accounting_reject_bill",
                    `${row.name}: บันทึกไม่อนุมัติแล้ว`
                ),
        });
    }

    postBill(row) {
        this.dialog.add(ConfirmationDialog, {
            title: "POST ตั้งเจ้าหนี้",
            body: `ยืนยัน POST ใบเรียกเก็บ ${row.name} (${row.vendor}) จำนวน ฿${this.formatMoney(row.amount)} เข้าบัญชีแยกประเภท?`,
            confirmLabel: "POST ตั้งเจ้าหนี้",
            cancelLabel: "ยกเลิก",
            confirm: () =>
                this._runBillAction(
                    row,
                    "action_accounting_post_bill",
                    `${row.name}: POST ตั้งเจ้าหนี้แล้ว`
                ),
        });
    }

    async _runBillAction(row, method, message) {
        if (this.state.busyId) {
            return;
        }
        this.state.busyId = row.id;
        try {
            await this.orm.call(MODEL, method, [[row.id]]);
            this.notification.add(message, { type: "success" });
            await this.loadData();
        } finally {
            this.state.busyId = false;
        }
    }
}

registry
    .category("actions")
    .add("vpk_payment_request_bill_approval_dashboard", BillApprovalDashboard);
