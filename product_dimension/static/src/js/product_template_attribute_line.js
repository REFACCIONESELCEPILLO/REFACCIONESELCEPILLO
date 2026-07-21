/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import {
    ProductTemplateAttributeLine,
} from "@sale/js/product_template_attribute_line/product_template_attribute_line";

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
                    component_sku: {
                        type: [Boolean, String],
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
        this.dimensionSearch = useState({ query: "" });
    },

    getPTAVTemplate() {
        if (this.showDimensionSearch) {
            return "product_dimension.ptav_select_search";
        }
        return super.getPTAVTemplate(...arguments);
    },

    updateDimensionSearch(event) {
        this.dimensionSearch.query = event.target.value;
    },

    get showDimensionSearch() {
        return (
            this.props.attribute.display_type === "select" &&
            this.props.attribute_values.length >= 20
        );
    },

    get filteredDimensionValues() {
        const query = this._normalizeDimensionSearch(this.dimensionSearch.query);
        if (!query) {
            return this.props.attribute_values;
        }
        return this.props.attribute_values.filter((value) => {
            const searchableText = `${value.component_sku || ""} ${value.name}`;
            return this._normalizeDimensionSearch(searchableText).includes(query);
        });
    },

    get dimensionSearchPlaceholder() {
        return _t("Buscar por referencia interna o descripción...");
    },

    get dimensionNoResultsText() {
        return _t("No hay valores que coincidan con la búsqueda");
    },

    getDimensionPTAVSelectName(value) {
        const name = this.getPTAVSelectName(value);
        if (value.component_sku && !name.includes(value.component_sku)) {
            return `[${value.component_sku}] ${name}`;
        }
        return name;
    },

    _normalizeDimensionSearch(value) {
        return (value || "")
            .toString()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .trim();
    },
});
