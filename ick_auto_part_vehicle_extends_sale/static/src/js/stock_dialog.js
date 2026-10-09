/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class StockDialog extends Component {
    static template = "ick_auto_part_vehicle_extends_sale.StockDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productId: Number,
        productName: { type: String, optional: true },
        companyId: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: true, error: false, data: null });
        onWillStart(async () => {
            try {
                this.state.data = await this.orm.call(
                    "sale.order",
                    "get_auto_product_stock",
                    [],
                    {
                        product_id: this.props.productId,
                        company_id: this.props.companyId,
                    }
                );
            } catch (error) {
                this.state.error = error?.message || "No fue posible consultar las existencias.";
            } finally {
                this.state.loading = false;
            }
        });
    }
}
