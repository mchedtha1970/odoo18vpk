/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class OnlyOfficeEditorField extends Component {
    static template = "vpk_document_studio_onlyoffice.OnlyOfficeEditorField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.editorRef = useRef("editor");
        this.wrapRef = useRef("wrap");
        this.state = useState({
            loading: true,
            error: "",
            editorId: `vpk_onlyoffice_doceditor_${this.props.record.resId || "new"}`,
        });
        this.docEditor = null;
        this.script = null;
        this.started = false;
        this.observer = null;
        onMounted(() => this.watchVisible());
        onWillUnmount(() => {
            this.observer?.disconnect();
            this.destroyEditor();
        });
    }

    get editorId() {
        return this.state.editorId;
    }

    watchVisible() {
        const el = this.wrapRef.el;
        if (!el) {
            this.startEditor();
            return;
        }
        this.observer = new IntersectionObserver(
            (entries) => {
                const visible = entries.some((entry) => entry.isIntersecting && entry.intersectionRatio > 0.4);
                if (visible && !this.started) {
                    this.started = true;
                    this.startEditor();
                }
            },
            { threshold: [0, 0.4, 1] }
        );
        this.observer.observe(el);
    }

    async startEditor() {
        const recordId = this.props.record.resId;
        if (!recordId) {
            this.state.loading = false;
            this.state.error = "บันทึกแบบฟอร์มก่อน จึงจะแก้ไฟล์ Word ได้";
            return;
        }
        try {
            const attachmentId = await this.orm.call(
                this.props.record.resModel,
                "onlyoffice_word_attachment_id",
                [recordId]
            );
            const response = await rpc("/onlyoffice/editor/get_config", {
                attachment_id: attachmentId,
            });
            const config = response.editorConfig;
            const host = this.editorRef.el;
            const height = Math.max(host?.clientHeight || 0, this.wrapRef.el?.clientHeight || 0, 640);
            config.width = "100%";
            config.height = `${height}px`;
            config.type = "desktop";
            config.events = {
                ...(config.events || {}),
                onError: (event) => {
                    console.error("OnlyOffice onError", event);
                    this.state.error = "เปิดไฟล์ Word ใน OnlyOffice ไม่สำเร็จ";
                },
            };
            if (!window.DocsAPI) {
                await this.loadDocsAPI(response.docApiJS);
            }
            if (!window.DocsAPI) {
                throw new Error("window.DocsAPI is null");
            }
            await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            this.state.loading = false;
            this.destroyEditor();
            this.docEditor = new window.DocsAPI.DocEditor(this.editorId, config);
        } catch (error) {
            console.error("OnlyOffice editor error:", error);
            this.state.loading = false;
            this.state.error = "เปิด OnlyOffice ไม่สำเร็จ กรุณาบันทึกแบบฟอร์มแล้วเปิดแท็บนี้อีกครั้ง";
        }
    }

    loadDocsAPI(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.body.appendChild(script);
            this.script = script;
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

registry.category("fields").add("vpk_onlyoffice_editor", {
    component: OnlyOfficeEditorField,
    supportedTypes: ["boolean"],
});
