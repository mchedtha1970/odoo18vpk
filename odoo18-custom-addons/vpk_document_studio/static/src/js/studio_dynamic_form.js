/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class StudioDynamicFormField extends Component {
    static template = "vpk_document_studio.StudioDynamicForm";
    static components = { DateTimeInput };
    static props = { ...standardFieldProps };

    get schema() {
        const schema = this.props.record.data.field_schema_json;
        return Array.isArray(schema) ? schema : [];
    }

    get values() {
        return this.props.record.data[this.props.name] || {};
    }

    isType(field, type) {
        return field.field_type === type;
    }

    isNumber(field) {
        return field.field_type === "integer" || field.field_type === "float";
    }

    numberStep(field) {
        return field.field_type === "integer" ? "1" : "any";
    }

    options(field) {
        return field.options || [];
    }

    isChecked(field) {
        return Boolean(this.values[field.code]);
    }

    isSelected(field, option) {
        return this.values[field.code] === option;
    }

    charValue(field) {
        const value = this.values[field.code];
        if (value === false || value === null || value === undefined) {
            return "";
        }
        return String(value);
    }

    showRefHint(field) {
        return field.field_type === "char" || field.field_type === "text";
    }

    refHintText() {
        return "อ้างอิงฟิลด์อื่นได้ด้วย {{รหัส}} เช่น ด้วย {{agency}} มีความประสงค์...";
    }

    fieldPlaceholder(field) {
        if (field.display_template) {
            return "ค่านี้ใช้ใน {{self}} ของรูปแบบแสดงผล";
        }
        return "อ้างอิงฟิลด์อื่นได้ เช่น ด้วย {{agency}} มีความประสงค์...";
    }

    _plainValue(field) {
        return this.displayValue(field) || "";
    }

    _thaiDigits(value) {
        return String(value).replace(/\d/g, (digit) => "๐๑๒๓๔๕๖๗๘๙"[Number(digit)]);
    }

    _interpolationMap() {
        const mapping = {};
        for (const field of this.schema) {
            const text = this._plainValue(field);
            mapping[field.code] = text;
            const lines = String(text)
                .split(/\n/)
                .filter((line) => line.trim());
            if (lines.length) {
                mapping[`${field.code}_count`] = String(lines.length);
                mapping[`${field.code}_count_th`] = this._thaiDigits(lines.length);
            }
        }
        return mapping;
    }

    interpolateText(source, field) {
        if (!source || !String(source).includes("{{")) {
            return source || "";
        }
        const mapping = this._interpolationMap();
        const selfValue = this._plainValue(field);
        return String(source).replace(/\{\{\s*([a-z][a-z0-9_]*)\s*\}\}/g, (match, code) => {
            if (code === "self") {
                return selfValue;
            }
            if (Object.prototype.hasOwnProperty.call(mapping, code)) {
                const value = mapping[code];
                return value === false || value === null || value === undefined ? "" : String(value);
            }
            return match;
        });
    }

    previewDisplay(field) {
        const template = (field.display_template || "").trim();
        const source = template || this._plainValue(field);
        if (!source || !source.includes("{{")) {
            return "";
        }
        return this.interpolateText(source, field);
    }

    numberValue(field) {
        const value = this.values[field.code];
        if (value === false || value === null || value === undefined || value === "") {
            return "";
        }
        return value;
    }

    displayValue(field) {
        const value = this.values[field.code];
        if (field.field_type === "boolean") {
            return value ? _t("ใช่") : _t("ไม่ใช่");
        }
        if (field.field_type === "many2one") {
            if (value && typeof value === "object") {
                return value.text || value.label || "";
            }
            return value ? String(value) : "";
        }
        if (value === false || value === null || value === undefined || value === "") {
            return "";
        }
        return String(value);
    }

    dateValue(field) {
        const raw = this.values[field.code];
        if (!raw) {
            return false;
        }
        try {
            return deserializeDate(String(raw).slice(0, 10));
        } catch {
            return false;
        }
    }

    updateValue(code, value) {
        const next = { ...this.values, [code]: value };
        this.props.record.update({ [this.props.name]: next });
    }

    onChar(field, ev) {
        this.updateValue(field.code, ev.target.value || "");
    }

    onNumber(field, ev) {
        const raw = ev.target.value;
        if (raw === "") {
            this.updateValue(field.code, false);
            return;
        }
        const number =
            field.field_type === "integer" ? parseInt(raw, 10) : parseFloat(raw);
        this.updateValue(field.code, Number.isNaN(number) ? false : number);
    }

    onBoolean(field, ev) {
        this.updateValue(field.code, Boolean(ev.target.checked));
    }

    onDate(field, value) {
        this.updateValue(field.code, value ? serializeDate(value) : false);
    }

    m2oChoices(field) {
        return Array.isArray(field.m2o_choices) ? field.m2o_choices : [];
    }

    isM2oSelected(field, choiceId) {
        return this.m2oSelectedId(field) === String(choiceId);
    }

    m2oSelectedId(field) {
        const val = this.values[field.code];
        if (val && typeof val === "object" && val.res_id) {
            return String(val.res_id);
        }
        if (typeof val === "number") {
            return String(val);
        }
        return "";
    }

    m2oTextValue(field) {
        const val = this.values[field.code];
        if (val && typeof val === "object") {
            return val.text || "";
        }
        if (typeof val === "string") {
            return val;
        }
        return "";
    }

    onMany2oneSelect(field, ev) {
        const rawId = ev.target.value;
        if (!rawId) {
            this.updateValue(field.code, "");
            return;
        }
        const prId = parseInt(rawId, 10);
        const choice = this.m2oChoices(field).find((c) => c.id === prId);
        this.updateValue(field.code, {
            res_id: prId,
            label: choice ? choice.label : `PR#${prId}`,
            text: choice ? choice.preview || "" : "",
        });
    }

    onMany2oneText(field, ev) {
        const val = this.values[field.code];
        const text = ev.target.value || "";
        if (val && typeof val === "object") {
            this.updateValue(field.code, { ...val, text });
        } else {
            this.updateValue(field.code, text);
        }
    }
}

registry.category("fields").add("studio_dynamic_form", {
    component: StudioDynamicFormField,
    supportedTypes: ["json"],
});
