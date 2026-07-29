from odoo.addons.sale.controllers.product_configurator import (
    SaleProductConfiguratorController,
)


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

        # Preserve Odoo's unit ``price_extra`` in the configurator. The
        # dimensional extension belongs to the sale order line, once width and
        # height are known, and must not replace the catalog rate shown here.
        return information
