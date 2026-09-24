/** @odoo-module **/

import { registry } from "@web/core/registry";

// Odoo's Print menu executes report actions in the browser, bypassing the
// Python report_action() override used by server-side callers.
registry.category("ir.actions.report handlers").add("ickab_direct_print", async (action, options, env) => {
    if (!["qweb-pdf", "qweb-text"].includes(action.report_type) || !action.report_name) {
        return false;
    }
    const context = action.context || {};
    const result = await env.services.orm.call(
        "ir.actions.report",
        "ickab_handle_web_report",
        [action.report_name, action.report_type, context.active_ids || [], action.data || {}],
        { context }
    );
    if (!result) {
        return false;
    }
    await env.services.action.doAction(result);
    return true;
});
