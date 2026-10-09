/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { append, createElement, setAttributes } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";

import { AutoPartsPanel } from "./auto_parts_panel";

/**
 * Compile the automotive panel marker added by this module in the sale order
 * form (``<div class="o_elcepillo_auto_panel"/>``) into an OWL component.
 *
 * The component is wrapped in a container div carrying the class used below to
 * move it next to the form sheet.
 *
 * @param {HTMLElement} node
 * @returns {HTMLElement}
 */
function compileAutoPartsPanel(node) {
    const panelXml = createElement("t");
    setAttributes(panelXml, {
        "t-component": "__comp__.elcepilloComponents.AutoPartsPanel",
        record: "__comp__.props.record",
    });
    const containerXml = createElement("div");
    containerXml.classList.add("o_elcepillo_auto_panel_container");
    setAttributes(containerXml, { "t-if": "!__comp__.env.inDialog" });
    append(containerXml, panelXml);
    return containerXml;
}

registry.category("form_compilers").add("elcepillo_auto_panel_compiler", {
    selector: "div.o_elcepillo_auto_panel",
    fn: compileAutoPartsPanel,
});

patch(FormCompiler.prototype, {
    compile(node, params) {
        const res = super.compile(node, params);
        const panelContainerXml = res.querySelector(".o_elcepillo_auto_panel_container");
        if (!panelContainerXml) {
            return res; // not the automotive form, keep it as is
        }
        const formSheetBgXml = res.querySelector(".o_form_sheet_bg");
        if (!formSheetBgXml) {
            return res;
        }
        // Move the panel inside the sheet background so it is displayed as a
        // right hand side column (see auto_sale.scss). The class is set on the
        // sheet background itself (a real rendered element) so that the layout
        // rules of this module can be scoped to the automotive form only.
        formSheetBgXml.classList.add("o_elcepillo_auto_form");
        append(formSheetBgXml, panelContainerXml);

        // Mail normally decides between side and bottom chatter according to
        // viewport width. This form has its own right column, so the chatter
        // must always be the full-width row below sheet + assistant.
        const chatterContainersXml = res.querySelectorAll(".o-mail-Form-chatter");
        for (const chatterContainerXml of chatterContainersXml) {
            chatterContainerXml.classList.remove("o-aside");
            chatterContainerXml.classList.add("o_ick_auto_sale_chatter_bottom");
            setAttributes(chatterContainerXml, {
                "t-attf-class": "mt-4 w-100 w-print-100",
            });
            const chatterXml = chatterContainerXml.querySelector(
                "t[t-component='__comp__.mailComponents.Chatter']"
            );
            if (chatterXml) {
                setAttributes(chatterXml, {
                    isChatterAside: "false",
                    isInFormSheetBg: "true",
                });
            }
            append(formSheetBgXml, chatterContainerXml);
        }
        return res;
    },
});

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.elcepilloComponents = { AutoPartsPanel };
    },
});
