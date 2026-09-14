/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useInputField } from "@web/views/fields/input_field_hook";
import { Component, useEffect, useRef } from "@odoo/owl";

const LOCAL_TINYMCE_BASE = "/hospital_budget_customization/static/lib/tinymce";
const OFFICIAL_FONT_STACK = "'TH Sarabun New','Sarabun',sans-serif";
const OFFICIAL_PARAGRAPH_STYLE = "margin:0 0 10px 0; line-height:1.8;";

let tinyMCELoadPromise = null;

function loadTinyMCE() {
    if (window.tinymce) {
        return Promise.resolve(window.tinymce);
    }
    if (tinyMCELoadPromise) {
        return tinyMCELoadPromise;
    }
    tinyMCELoadPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = `${LOCAL_TINYMCE_BASE}/tinymce.min.js`;
        script.onload = () => resolve(window.tinymce);
        script.onerror = () =>
            reject(new Error("Unable to load local TinyMCE library from module assets."));
        document.head.appendChild(script);
    });
    return tinyMCELoadPromise;
}

function getDefaultOfficialTemplate() {
    return (
        "<p>ด้วยหน่วยงานมีความประสงค์ขออนุมัติจัดซื้อพัสดุเพื่อใช้ในการปฏิบัติงาน</p>" +
        "<p><strong>เหตุผลและความจำเป็น</strong> เนื่องจากมีความจำเป็นในการใช้งานตามภารกิจของหน่วยงาน</p>" +
        "<p><strong>รายละเอียดพัสดุที่ขอซื้อ</strong> โปรดระบุรายการ/คุณลักษณะ/จำนวน</p>" +
        "<p>จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติ</p>"
    );
}

export class TinymceHtmlField extends Component {
    static template = "vpk_sidebar_menu.TinymceHtmlField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        minHeight: { type: Number, optional: true },
        officialPreset: { type: Boolean, optional: true },
        templateMenu: { type: Boolean, optional: true },
        defaultTemplate: { type: Boolean, optional: true },
    };
    static defaultProps = {
        minHeight: 320,
        officialPreset: false,
        templateMenu: true,
        defaultTemplate: false,
    };

    setup() {
        this.textareaRef = useRef("textarea");
        this.editor = null;

        useInputField({
            getValue: () => {
                if (this.editor) {
                    return this.editor.getContent({ format: "html" });
                }
                return this.textareaRef.el?.value || "";
            },
            refName: "textarea",
        });

        useEffect(
            (el) => {
                if (!el || this.props.readonly) {
                    return;
                }
                let cancelled = false;
                let editor = null;

                const syncToRecord = () => {
                    if (!editor || !el) {
                        return;
                    }
                    el.value = editor.getContent({ format: "html" });
                    el.dispatchEvent(new InputEvent("input", { bubbles: true }));
                };

                const initEditor = async () => {
                    try {
                        const tinymce = await loadTinyMCE();
                        if (cancelled || !el.isConnected) {
                            return;
                        }
                        if (!el.id) {
                            el.id = `vpk_tinymce_${this.props.name}_${Date.now()}`;
                        }
                        const config = this._buildTinyMCEConfig(el, syncToRecord);
                        const editors = await tinymce.init(config);
                        editor = editors?.[0] || tinymce.get(el.id);
                        if (cancelled || !editor) {
                            return;
                        }
                        this.editor = editor;
                    } catch {
                        if (!cancelled && el) {
                            el.style.resize = "vertical";
                            el.style.minHeight = `${this.props.minHeight}px`;
                            el.style.overflowY = "auto";
                        }
                    }
                };

                initEditor();

                return () => {
                    cancelled = true;
                    if (editor) {
                        editor.remove();
                    }
                    this.editor = null;
                };
            },
            () => [this.textareaRef.el, this.props.readonly]
        );
    }

    _buildTinyMCEConfig(el, syncToRecord) {
        const officialPreset = this.props.officialPreset;
        const enableTemplates = this.props.templateMenu !== false;
        const initialValue = this.props.record.data[this.props.name] || "";

        return {
            target: el,
            base_url: LOCAL_TINYMCE_BASE,
            suffix: ".min",
            menubar: officialPreset ? false : "edit view insert format table tools",
            plugins: officialPreset
                ? "lists advlist link paste"
                : "lists advlist table link code autoresize",
            toolbar: officialPreset
                ? "undo redo | officialtemplate | bold italic underline | " +
                  "alignleft aligncenter alignright | bullist numlist outdent indent | removeformat"
                : "undo redo | blocks fontfamily fontsize | " +
                  "bold italic underline | alignleft aligncenter alignright alignjustify | " +
                  "bullist numlist outdent indent | lineheight | table | removeformat | code",
            branding: false,
            promotion: false,
            statusbar: true,
            min_height: this.props.minHeight,
            resize: "vertical",
            browser_spellcheck: true,
            convert_urls: false,
            placeholder: this.props.placeholder || "",
            forced_root_block: "p",
            forced_root_block_attrs: {
                style: OFFICIAL_PARAGRAPH_STYLE,
            },
            font_family_formats: "TH Sarabun New=TH Sarabun New,Sarabun,sans-serif",
            fontsize_formats: "16pt",
            invalid_styles: officialPreset
                ? {
                      "*": "font-family font-size line-height",
                  }
                : undefined,
            paste_as_text: officialPreset,
            line_height_formats: "1 1.15 1.5 1.75 2 2.5 3",
            content_style: officialPreset
                ? `body, p, li, td, th {font-family:${OFFICIAL_FONT_STACK} !important; font-size:16pt !important; line-height:1.8 !important;} ` +
                  "p {margin:0 0 10px 0;} ul,ol {margin:0 0 10px 30px; padding:0;}"
                : "body {font-family: 'Sarabun','TH Sarabun New',sans-serif; font-size:16px; line-height:1.5;} " +
                  "p {margin:0 0 10px 0;}",
            setup: (editor) => {
                if (officialPreset && enableTemplates) {
                    editor.ui.registry.addButton("officialtemplate", {
                        text: "แม่แบบราชการ",
                        onAction: () => {
                            editor.setContent(getDefaultOfficialTemplate());
                            syncToRecord();
                        },
                    });
                }
                editor.on("init", () => {
                    const hasValue = (initialValue || "").trim();
                    if (!hasValue && this.props.defaultTemplate) {
                        editor.setContent(getDefaultOfficialTemplate());
                        syncToRecord();
                    } else {
                        editor.setContent(initialValue || "<p><br></p>");
                    }
                });
                editor.on(
                    "change keyup undo redo input ExecCommand SetContent blur",
                    syncToRecord
                );
            },
        };
    }
}

export const tinymceHtmlField = {
    component: TinymceHtmlField,
    displayName: "TinyMCE HTML",
    supportedTypes: ["text", "html"],
    extractProps: ({ options }) => ({
        placeholder: options?.placeholder,
        minHeight: options?.min_height || 320,
        officialPreset: Boolean(options?.official_preset),
        templateMenu: options?.template_menu !== false,
        defaultTemplate: Boolean(options?.default_template),
    }),
};

registry.category("fields").add("tinymce_html", tinymceHtmlField);
