/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import {
    ProductConfiguratorDialog,
} from "@sale/js/product_configurator_dialog/product_configurator_dialog";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field";

patch(ProductConfiguratorDialog, {
    props: {
        ...ProductConfiguratorDialog.props,
        dimensionM2: { type: Number, optional: true },
        dimensionMl: { type: Number, optional: true },
    },
});

patch(ProductConfiguratorDialog.prototype, {
    _getAdditionalRpcParams() {
        return {
            ...super._getAdditionalRpcParams(...arguments),
            m2: this.props.dimensionM2 || 0.0,
            ml: this.props.dimensionMl || 0.0,
        };
    },
});

patch(SaleOrderLineProductField.prototype, {
    _getAdditionalDialogProps() {
        return {
            ...super._getAdditionalDialogProps(...arguments),
            dimensionM2: this.props.record.data.m2 || 0.0,
            dimensionMl: this.props.record.data.ml || 0.0,
        };
    },
});
