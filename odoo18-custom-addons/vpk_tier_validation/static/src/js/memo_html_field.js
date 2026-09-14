/** @odoo-module **/

import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";

/**
 * Legacy alias — behaves like standard html field (floating toolbar hidden until selection).
 * Kept for backward compatibility if any view still references widget="memo_html".
 */
export class MemoHtmlField extends HtmlField {
    static template = "html_editor.HtmlField";
}

export const memoHtmlField = {
    ...htmlField,
    component: MemoHtmlField,
};

registry.category("fields").add("memo_html", memoHtmlField, { force: true });
