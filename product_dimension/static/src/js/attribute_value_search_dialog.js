/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { formatCurrency } from "@web/core/currency";

export class AttributeValueSearchDialog extends Component {
    static components = { Dialog };
    static template = "product_dimension.AttributeValueSearchDialog";
    static props = {
        close: Function,
        confirm: Function,
        currencyId: Number,
        selectedValueId: { type: Number, optional: true },
        title: String,
        values: Array,
    };

    setup() {
        this.state = useState({
            query: "",
            selectedValueId: this.props.selectedValueId || false,
        });
    }

    get filteredValues() {
        const query = this._normalize(this.state.query);
        if (!query) {
            return this.props.values;
        }
        return this.props.values.filter((value) => {
            const searchableText = `${value.component_sku || ""} ${value.name || ""}`;
            return this._normalize(searchableText).includes(query);
        });
    }

    updateSearch(event) {
        this.state.query = event.target.value;
    }

    selectValue(value) {
        if (!value.excluded) {
            this.state.selectedValueId = value.id;
        }
    }

    async confirmSelection() {
        if (!this.state.selectedValueId) {
            return;
        }
        await this.props.confirm(this.state.selectedValueId);
        this.props.close();
    }

    formatPrice(value) {
        return formatCurrency(value || 0, this.props.currencyId);
    }

    _normalize(value) {
        return (value || "")
            .toString()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .trim();
    }
}
