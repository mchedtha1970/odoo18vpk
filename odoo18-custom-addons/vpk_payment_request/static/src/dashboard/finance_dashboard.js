/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const MODEL = "vpk.document.studio.document";
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

export class PaymentRequestFinanceDashboard extends Component {
    static template = "vpk_payment_request.FinanceDashboard";
    static props = ["*"];

    setup() {
        ensurePromptFont();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            ready: false,
            busyId: false,
            filter: "to_finance",
            search: "",
            data: { kpis: [], rows: [] },
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.data = await this.orm.call(MODEL, "get_payment_finance_dashboard", []);
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
            if (this.state.filter === "overdue" && !row.overdue) {
                return false;
            }
            if (
                this.state.filter !== "overdue" &&
                this.state.filter !== "all" &&
                row.state !== this.state.filter
            ) {
                return false;
            }
            if (!query) {
                return true;
            }
            return [row.name, row.po_name, row.po_disbursement_label, row.vendor, row.wa, row.bill_name, row.kb_name, row.kb_state_label]
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

    waitingLabel(row) {
        return row.waiting_days ? `${row.waiting_days} วัน` : "วันนี้";
    }

    async openDisbursementCoverWizard() {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "ใบปะหน้าการขออนุมัติเบิกจ่ายจาก GFMIS",
            res_model: "vpk.disbursement.cover.wizard",
            views: [[false, "form"]],
            target: "new",
        });
    }

    async openCreateMultiVoucherWizard() {
        await this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: "สร้างใบสำคัญจ่าย (รวมหลายใบตั้งหนี้ที่อนุมัติและ POST แล้ว)",
                res_model: "vpk.payment.voucher.create.wizard",
                views: [[false, "form"]],
                target: "new",
            },
            {
                onClose: () => this.loadData(),
            }
        );
    }

    async openMemoVoucher(row) {
        if (!row.bill_id && !row.memo_voucher_id) {
            return;
        }
        const result = await this.orm.call(
            MODEL,
            "action_create_or_open_payment_voucher",
            [[row.id]]
        );
        if (result && result.type) {
            await this.actionService.doAction(result, {
                onClose: () => this.loadData(),
            });
        }
    }

    async openPayment(row) {
        if (!row.can_register_payment || this.state.busyId) {
            return;
        }
        this.state.busyId = row.id;
        try {
            const result = await this.orm.call(MODEL, "action_open_register_payment", [[row.id]]);
            if (result && result.type === "ir.actions.client" && result.tag === "display_notification") {
                const params = result.params || {};
                this.notification.add(params.message || "ยืนยันรายการจ่ายแล้ว", {
                    title: params.title,
                    type: params.type || "success",
                });
            } else if (result && result.type) {
                await this.actionService.doAction(result);
            }
            await this.loadData();
        } finally {
            this.state.busyId = false;
        }
    }

    async openDraftPayment(row) {
        if (!row.draft_payment_id) {
            return;
        }
        const result = await this.orm.call(MODEL, "action_open_draft_payment_voucher", [[row.id]]);
        if (result && result.type) {
            await this.actionService.doAction(result, {
                onClose: () => this.loadData(),
            });
        }
    }

    async openBill(row) {
        const result = await this.orm.call(MODEL, "action_open_ap_bill", [[row.id]]);
        if (result && result.type) {
            await this.actionService.doAction(result);
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

    openDisbursementForm(row) {
        if (!row.kb_id) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.kb_name || "ใบขอเบิกเงิน",
            res_model: "vpk.disbursement.form",
            res_id: row.kb_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry
    .category("actions")
    .add("vpk_payment_request_finance_dashboard", PaymentRequestFinanceDashboard);
