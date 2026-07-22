from odoo.addons.sale.controllers.product_configurator import (
    SaleProductConfiguratorController,
)
from odoo.http import request


class DimensionSaleProductConfiguratorController(SaleProductConfiguratorController):

    def _get_product_information(
        self,
        product_template,
        combination,
        currency,
        pricelist,
        so_date,
        quantity=1,
        product_uom_id=None,
        parent_combination=None,
        **kwargs,
    ):
        information = super()._get_product_information(
            product_template,
            combination,
            currency,
            pricelist,
            so_date,
            quantity=quantity,
            product_uom_id=product_uom_id,
            parent_combination=parent_combination,
            **kwargs,
        )
        component_data = {
            value.id: {
                "internal_reference": (
                    value.product_attribute_value_id.component_internal_reference
                    or False
                ),
                "skip_component": value._is_dimension_na_value(),
            }
            for value in product_template.attribute_line_ids.product_template_value_ids
        }
        for attribute_line in information["attribute_lines"]:
            for value in attribute_line["attribute_values"]:
                value.update(component_data.get(value["id"], {
                    "internal_reference": False,
                    "skip_component": False,
                }))
            attribute_line["attribute_values"].sort(
                key=lambda value: not value["skip_component"]
            )

        if product_template.dimension_enabled:
            area = float(kwargs.get("m2") or 0.0)
            perimeter = float(kwargs.get("ml") or 0.0)
            ptavs = product_template.attribute_line_ids.product_template_value_ids
            ptavs_by_id = {value.id: value for value in ptavs}
            for attribute_line in information["attribute_lines"]:
                for value_information in attribute_line["attribute_values"]:
                    value = ptavs_by_id[value_information["id"]]
                    amount = value._get_dimension_sale_amount(area, perimeter)
                    value_information["price_extra"] = value.currency_id._convert(
                        amount,
                        currency,
                        request.env.company,
                        so_date,
                        round=False,
                    )

        return information

    def _get_basic_product_information(
        self,
        product_or_template,
        pricelist,
        combination,
        **kwargs,
    ):
        information = super()._get_basic_product_information(
            product_or_template,
            pricelist,
            combination,
            **kwargs,
        )
        product_template = (
            product_or_template.product_tmpl_id
            if product_or_template.is_product_variant
            else product_or_template
        )
        if not product_template.dimension_enabled:
            return information

        area = float(kwargs.get("m2") or 0.0)
        perimeter = float(kwargs.get("ml") or 0.0)
        dimensional_base = product_template.list_price + sum(
            value._get_dimension_sale_amount(area, perimeter)
            for value in combination
            if not value._is_dimension_na_value()
        )
        information["price"] = product_template._apply_dimension_pricelist_price(
            dimensional_base,
            product_or_template,
            pricelist,
            kwargs.get("quantity", 1.0),
            kwargs.get("uom") or product_or_template.uom_id,
            kwargs.get("date"),
            request.env.company,
        )
        return information
