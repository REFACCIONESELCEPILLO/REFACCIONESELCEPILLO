/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
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
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    async _loadData(onlyMainProduct) {
        const data = await super._loadData(...arguments);
        this.currency.id ??= data.currency_id;
        await this._loadDimensionAttributeValueMetadata(data);
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

    async _loadDimensionAttributeValueMetadata(data) {
        const products = [
            ...(data.products || []),
            ...(data.optional_products || []),
        ];
        const valuesById = new Map();
        for (const product of products) {
            for (const attributeLine of product.attribute_lines || []) {
                for (const value of attributeLine.attribute_values || []) {
                    valuesById.set(value.id, value);
                }
            }
        }
        if (!valuesById.size) {
            return;
        }

        const ptavMetadata = await this.orm.read(
            "product.template.attribute.value",
            [...valuesById.keys()],
            ["component_sku", "skip_component", "product_attribute_value_id"]
        );
        const valuesNeedingFallback = ptavMetadata.filter(
            (value) => (
                !value.component_sku
                && !value.skip_component
                && value.product_attribute_value_id
            )
        );
        let referencesByAttributeValue = {};
        if (valuesNeedingFallback.length) {
            const attributeValues = await this.orm.read(
                "product.attribute.value",
                [...new Set(valuesNeedingFallback.map(
                    (value) => value.product_attribute_value_id[0]
                ))],
                ["component_internal_reference"]
            );
            referencesByAttributeValue = Object.fromEntries(
                attributeValues.map((value) => [
                    value.id,
                    value.component_internal_reference || "",
                ])
            );
        }
        for (const metadata of ptavMetadata) {
            const value = valuesById.get(metadata.id);
            const attributeValueId = metadata.product_attribute_value_id?.[0];
            value.internal_reference = (
                metadata.component_sku
                || referencesByAttributeValue[attributeValueId]
                || ""
            );
            value.skip_component = metadata.skip_component;
        }
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
