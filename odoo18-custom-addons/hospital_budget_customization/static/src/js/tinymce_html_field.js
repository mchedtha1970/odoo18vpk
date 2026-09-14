odoo.define("hospital_budget_customization.tinymce_html_field", function (require) {
    "use strict";

    var basic_fields = require("web.basic_fields");
    var core = require("web.core");
    var field_registry = require("web.field_registry");

    var _lt = core._lt;
    var LOCAL_TINYMCE_BASE = "/hospital_budget_customization/static/lib/tinymce";
    var tinyMCELoadPromise = null;
    var OFFICIAL_FONT_STACK = "'TH Sarabun New','Sarabun',sans-serif";
    var OFFICIAL_PARAGRAPH_STYLE = "margin:0 0 10px 0; line-height:1.8;";

    function loadTinyMCE() {
        if (window.tinymce) {
            return Promise.resolve(window.tinymce);
        }
        if (tinyMCELoadPromise) {
            return tinyMCELoadPromise;
        }
        tinyMCELoadPromise = new Promise(function (resolve, reject) {
            var script = document.createElement("script");
            script.src = LOCAL_TINYMCE_BASE + "/tinymce.min.js";
            script.onload = function () {
                resolve(window.tinymce);
            };
            script.onerror = function () {
                reject(
                    new Error("Unable to load local TinyMCE library from module assets.")
                );
            };
            document.head.appendChild(script);
        });
        return tinyMCELoadPromise;
    }

    var FieldTinyMCEHtml = basic_fields.DebouncedField.extend({
        description: _lt("TinyMCE HTML"),
        className: "oe_form_field oe_form_field_html o_tinymce_html_field",
        supportedFieldTypes: ["html", "text"],
        isQuickEditable: true,

        init: function () {
            this._super.apply(this, arguments);
            this._editor = null;
            this._editorId = _.uniqueId("o_tinymce_field_");
            this._tinyLoadFailed = false;
            this._editorOptions = this.nodeOptions || {};
            this._renderToken = 0;
            this._destroyed = false;
        },

        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return loadTinyMCE().catch(function () {
                    self._tinyLoadFailed = true;
                    return null;
                });
            });
        },

        destroy: function () {
            this._destroyed = true;
            this._renderToken += 1;
            this._destroyEditor();
            this._super.apply(this, arguments);
        },

        commitChanges: function () {
            if (this.mode === "readonly") {
                return this._super.apply(this, arguments);
            }
            this._setValue(this._getValue());
            return this._super.apply(this, arguments);
        },

        reset: function (record, event) {
            this._reset(record, event);
            if (this.mode === "edit" && this._editor && (!event || event.target !== this)) {
                this._editor.setContent(this.value || "<p><br></p>");
            } else if (this.mode === "edit" && this.$textarea && (!event || event.target !== this)) {
                this.$textarea.val(this.value || "");
            } else if (this.mode === "readonly") {
                this._renderReadonly();
            }
            return Promise.resolve();
        },

        _getValue: function () {
            if (this.mode === "edit" && this._editor) {
                return this._editor.getContent({format: "html"});
            }
            if (this.mode === "edit" && this.$textarea && this.$textarea.length) {
                return this.$textarea.val() || "";
            }
            return this.value || "";
        },

        _renderReadonly: function () {
            this._destroyEditor();
            this.$el.html(this.value || "");
        },

        _renderEdit: function () {
            var self = this;
            var renderToken = ++this._renderToken;
            this.$el.empty();
            this._destroyEditor();
            this._editorId = _.uniqueId("o_tinymce_field_");

            this.$textarea = $('<textarea id="' + this._editorId + '"/>');
            this.$textarea.val(this.value || "");
            this.$el.append(this.$textarea);

            if (this._tinyLoadFailed) {
                this.$textarea.on("input", function () {
                    self._doDebouncedAction();
                });
                this.$textarea.on("blur", function () {
                    self._doAction();
                });
                return Promise.resolve();
            }

            return loadTinyMCE()
                .then(function (tinymce) {
                    if (!self.$textarea || !self.$textarea.length || !tinymce) {
                        return;
                    }
                    if (self._destroyed || renderToken !== self._renderToken) {
                        return;
                    }
                    if (!document.body.contains(self.$textarea[0])) {
                        return;
                    }
                    return tinymce.init(self._buildTinyMCEConfig());
                })
                .catch(function () {
                    self._tinyLoadFailed = true;
                    if (self.$textarea && self.$textarea.length) {
                        self.$textarea.on("input", function () {
                            self._doDebouncedAction();
                        });
                        self.$textarea.on("blur", function () {
                            self._doAction();
                        });
                    }
                });
        },

        _buildTinyMCEConfig: function () {
            var self = this;
            var officialPreset = !!self._editorOptions.official_preset;
            var enableTemplates = self._editorOptions.template_menu !== false;

            return {
                target: self.$textarea[0],
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
                min_height: self._editorOptions.min_height || 360,
                resize: true,
                browser_spellcheck: true,
                convert_urls: false,
                placeholder: self._editorOptions.placeholder || "",
                forced_root_block: "p",
                forced_root_block_attrs: {
                    style: OFFICIAL_PARAGRAPH_STYLE,
                },
                font_family_formats:
                    "TH Sarabun New=TH Sarabun New,Sarabun,sans-serif",
                fontsize_formats: "16pt",
                invalid_styles: officialPreset
                    ? {
                          "*": "font-family font-size line-height",
                      }
                    : undefined,
                paste_as_text: officialPreset,
                line_height_formats: "1 1.15 1.5 1.75 2 2.5 3",
                content_style: officialPreset
                    ? "body, p, li, td, th {font-family:" +
                      OFFICIAL_FONT_STACK +
                      " !important; font-size:16pt !important; line-height:1.8 !important;} " +
                      "p {margin:0 0 10px 0;} ul,ol {margin:0 0 10px 30px; padding:0;}"
                    : "body {font-family: 'Sarabun','TH Sarabun New',sans-serif; font-size:16px; line-height:1.5;} " +
                      "p {margin:0 0 10px 0;}",
                setup: function (editor) {
                    self._editor = editor;
                    if (officialPreset && enableTemplates) {
                        self._registerOfficialTemplateButtons(editor);
                    }
                    editor.on("init", function () {
                        if (self._destroyed) {
                            editor.remove();
                            return;
                        }
                        var hasValue = (self.value || "").trim();
                        if (!hasValue && self._editorOptions.default_template) {
                            editor.setContent(self._getDefaultOfficialTemplate());
                            self._doDebouncedAction();
                        } else {
                            editor.setContent(self.value || "<p><br></p>");
                        }
                    });
                    editor.on("change keyup undo redo input ExecCommand SetContent", function () {
                        self._doDebouncedAction();
                    });
                    editor.on("blur", function () {
                        self._doAction();
                    });
                },
            };
        },

        _registerOfficialTemplateButtons: function (editor) {
            var self = this;
            editor.ui.registry.addButton("officialtemplate", {
                text: "แม่แบบราชการ",
                onAction: function () {
                    editor.setContent(self._getDefaultOfficialTemplate());
                    self._doDebouncedAction();
                },
            });
        },

        _getDefaultOfficialTemplate: function () {
            return (
                "<p>ด้วยหน่วยงานมีความประสงค์ขออนุมัติจัดซื้อพัสดุเพื่อใช้ในการปฏิบัติงาน</p>" +
                "<p><strong>เหตุผลและความจำเป็น</strong> เนื่องจากมีความจำเป็นในการใช้งานตามภารกิจของหน่วยงาน</p>" +
                "<p><strong>รายละเอียดพัสดุที่ขอซื้อ</strong> โปรดระบุรายการ/คุณลักษณะ/จำนวน</p>" +
                "<p>จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติ</p>"
            );
        },

        _destroyEditor: function () {
            if (this._editor) {
                this._editor.remove();
                this._editor = null;
            }
            if (window.tinymce) {
                var staleEditor = window.tinymce.get(this._editorId);
                if (staleEditor) {
                    staleEditor.remove();
                }
            }
        },
    });

    field_registry.add("tinymce_html", FieldTinyMCEHtml);

    return FieldTinyMCEHtml;
});
