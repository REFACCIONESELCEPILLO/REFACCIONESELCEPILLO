/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { formatCurrency } from "@web/core/currency";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import {
    ProductTemplateAttributeLine,
} from "@sale/js/product_template_attribute_line/product_template_attribute_line";
import { AttributeValueSearchDialog } from "./attribute_value_search_dialog";

const attributeValuesProp = ProductTemplateAttributeLine.props.attribute_values;

patch(ProductTemplateAttributeLine, {
    props: {
        ...ProductTemplateAttributeLine.props,
        attribute_values: {
            ...attributeValuesProp,
            element: {
                ...attributeValuesProp.element,
                shape: {
                    ...attributeValuesProp.element.shape,
                    internal_reference: {
                        type: [Boolean, String],
                        optional: true,
                    },
                    skip_component: {
                        type: Boolean,
                        optional: true,
                    },
                },
            },
        },
    },
});

patch(ProductTemplateAttributeLine.prototype, {
    setup() {
        if (super.setup) {
            super.setup(...arguments);
        }
        this.dialog = useService("dialog");
    },

    getPTAVTemplate() {
        if (this.showDimensionSelector) {
            return "product_dimension.ptav_select_lookup";
        }
        return super.getPTAVTemplate(...arguments);
    },

    get showDimensionSelector() {
        return this.props.attribute.display_type === "select";
    },

    get sortedDimensionValues() {
        return [...this.props.attribute_values].sort(
            (left, right) => Number(Boolean(right.skip_component)) - Number(Boolean(left.skip_component))
        );
    },

    get dimensionValuesWithReferences() {
        return this.sortedDimensionValues.map((value) => ({
            ...value,
            internal_reference: this.getDimensionInternalReference(value),
        }));
    },

    openDimensionValueSearch() {
        this.dialog.add(AttributeValueSearchDialog, {
            title: `${_t("Seleccionar valor")}: ${this.props.attribute.name}`,
            values: this.dimensionValuesWithReferences,
            selectedValueId: this.props.selected_attribute_value_ids[0],
            currencyId: this.env.currency.id,
            confirm: (ptavId) => this.env.updateProductTemplateSelectedPTAV(
                this.props.productTmplId,
                this.props.id,
                ptavId,
                false
            ),
        });
    },

    getDimensionPTAVSelectName(value) {
        const parts = [this.getDimensionInternalReference(value)];
        parts.push(value.name);
        parts.push(formatCurrency(value.price_extra || 0, this.env.currency.id));
        return parts.filter(Boolean).join(" - ");
    },

    getDimensionInternalReference(value) {
        return value.internal_reference || "";
    },
});
