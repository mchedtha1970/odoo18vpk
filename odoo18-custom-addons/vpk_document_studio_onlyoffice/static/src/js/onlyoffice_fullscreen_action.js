/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { cookie } from "@web/core/browser/cookie";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class OnlyOfficeFullscreenAction extends Component {
    static template = "vpk_document_studio_onlyoffice.FullscreenEditor";
    static props = ["*"];

    setup() {
        const params = this.props.action?.params || {};
        const key = params.attachment_id || params.document_id || "doc";
        this.editorId = `vpk_onlyoffice_fullscreen_${key}`;
        this.state = useState({ loading: true, error: "" });
        this.editorRef = useRef("editor");
        this.docEditor = null;
        onMounted(() => this.startEditor());
        onWillUnmount(() => this.destroyEditor());
    }

    async startEditor() {
        const params = this.props.action?.params || {};
        const args = {};
        if (params.document_id) {
            args.document_id = params.document_id;
        } else if (params.attachment_id) {
            args.attachment_id = params.attachment_id;
        } else {
            this.state.loading = false;
            this.state.error = "ไม่พบไฟล์ที่จะเปิดใน OnlyOffice";
            return;
        }
        try {
            const response = await rpc("/onlyoffice/editor/get_config", args);
            const config = response.editorConfig;
            const theme = cookie.get("color_scheme");
            config.editorConfig.customization = {
                ...(config.editorConfig.customization || {}),
                uiTheme: theme ? `default-${theme}` : "default-light",
            };
            config.width = "100%";
            config.height = "100%";
            config.type = "desktop";
            if (!window.DocsAPI) {
                await this.loadDocsAPI(response.docApiJS);
            }
            if (!window.DocsAPI) {
                throw new Error("window.DocsAPI is null");
            }
            this.state.loading = false;
            await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            this.destroyEditor();
            this.docEditor = new window.DocsAPI.DocEditor(this.editorId, config);
        } catch (error) {
            console.error("OnlyOffice fullscreen error:", error);
            this.state.loading = false;
            this.state.error = "เปิด OnlyOffice ไม่สำเร็จ กรุณารีเฟรชหน้าแล้วลองอีกครั้ง";
        }
    }

    loadDocsAPI(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.body.appendChild(script);
        });
    }

    destroyEditor() {
        try {
            this.docEditor?.destroyEditor?.();
        } catch (_err) {
            // Editor may already be gone.
        }
        this.docEditor = null;
    }
}

registry.category("actions").add("onlyoffice_editor", OnlyOfficeFullscreenAction, { force: true });
