/** @odoo-module **/

import { Component, onPatched, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const PROMPT_STYLE_ID = "vpk-approval-prompt-style";
const PROMPT_FONT_BASE = "/vpk_tier_validation/static/src/fonts";

function promptFace(weight, kind, range) {
    return `
        @font-face {
            font-family: "VPK Prompt";
            font-style: normal;
            font-weight: ${weight};
            font-display: swap;
            src: url("${PROMPT_FONT_BASE}/prompt-${kind}-${weight}.woff2") format("woff2");
            unicode-range: ${range};
        }
    `;
}

function ensurePromptFont() {
    if (document.getElementById(PROMPT_STYLE_ID)) {
        return;
    }
    const thai = "U+0E01-0E5B, U+200C-200D, U+25CC";
    const latin = "U+0000-00FF, U+2000-206F, U+20AC, U+2122";
    const style = document.createElement("style");
    style.id = PROMPT_STYLE_ID;
    style.textContent = [400, 500, 600, 700]
        .map((weight) => promptFace(weight, "thai", thai) + promptFace(weight, "latin", latin))
        .join("") + `
        body.o_web_client .o_vpk_approval_board,
        body.o_web_client .o_vpk_approval_board *:not(.fa):not(.oi),
        body.o_web_client .o_vpk_approval_board h1,
        body.o_web_client .o_vpk_approval_board h1.o_vpk_approval_title,
        body.o_web_client .o_vpk_approval_board .o_vpk_approval_head p {
            font-family: "VPK Prompt", "Prompt", sans-serif !important;
        }
    `;
    document.head.appendChild(style);
}

export class ApprovalStatusBoard extends Component {
    static template = "vpk_tier_validation.ApprovalStatusBoard";
    static props = ["*"];

    setup() {
        ensurePromptFont();
        onPatched(() => this.applyPromptFont());
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            ready: false,
            filter: "all",
            progress: "all",
            data: { updated_at: "", total: 0, open_count: 0, done_count: 0, types: [] },
        });
        onWillStart(() => this.loadData());
    }

    applyPromptFont() {
        const root = document.querySelector(".o_vpk_approval_board");
        if (!root) {
            return;
        }
        const nodes = root.querySelectorAll(
            ".o_vpk_approval_head, .o_vpk_approval_head h1, .o_vpk_approval_head p"
        );
        for (const node of nodes) {
            node.style.setProperty("font-family", '"VPK Prompt", sans-serif', "important");
            node.style.setProperty("font-weight", node.tagName === "H1" ? "500" : "400", "important");
        }
    }

    async loadData() {
        this.state.ready = false;
        this.state.data = await this.orm.call(
            "tier.review",
            "get_approval_status_board",
            [],
            {}
        );
        const keys = this.state.data.types.map((item) => item.key);
        if (this.state.filter !== "all" && !keys.includes(this.state.filter)) {
            this.state.filter = "all";
        }
        this.state.ready = true;
        requestAnimationFrame(() => this.applyPromptFont());
    }

    get visibleTypes() {
        return this.state.data.types
            .filter((item) => this.state.filter === "all" || item.key === this.state.filter)
            .map((item) => {
                const documents = item.documents.filter(
                    (card) => this.state.progress === "all" || card.progress === this.state.progress
                );
                return { ...item, documents, count: documents.length };
            })
            .filter((item) => item.documents.length);
    }

    setFilter(key) {
        this.state.filter = key;
    }

    setProgress(progress) {
        this.state.progress = progress;
    }

    async openDocument(card) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: card.name,
            res_model: card.model,
            res_id: card.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("vpk_approval_status_board", ApprovalStatusBoard);
