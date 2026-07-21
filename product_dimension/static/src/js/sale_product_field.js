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
    async _loadData(onlyMainProduct) {
        const data = await super._loadData(...arguments);
        this.currency.id ??= data.currency_id;
        if (this.props.edit) {
            return data;
        }

        const products = [
            ...(data.products || []),
            ...(data.optional_products || []),
        ];
        for (const product of products) {
            let selectionChanged = false;
            for (const attributeLine of product.attribute_lines || []) {
                const naValue = attributeLine.attribute_values.find(
                    (value) => value.skip_component
                );
                if (
                    naValue &&
                    !attributeLine.selected_attribute_value_ids.includes(naValue.id)
                ) {
                    attributeLine.selected_attribute_value_ids = [naValue.id];
                    selectionChanged = true;
                }
            }
            if (selectionChanged) {
                const updatedValues = await this._updateCombination(
                    product,
                    product.quantity
                );
                Object.assign(product, updatedValues);
            }
        }
        return data;
    },

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
