/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class CompatibilityDialog extends Component {
    static template = "ick_auto_part_vehicle_extends_sale.CompatibilityDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productId: Number,
        productName: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: true, error: false, data: null });
        onWillStart(async () => {
            try {
                this.state.data = await this.orm.call(
                    "sale.order",
                    "get_auto_product_compatibility",
                    [],
                    { product_id: this.props.productId }
                );
            } catch (error) {
                this.state.error = error?.message || "No fue posible consultar la compatibilidad.";
            } finally {
                this.state.loading = false;
            }
        });
    }
}
