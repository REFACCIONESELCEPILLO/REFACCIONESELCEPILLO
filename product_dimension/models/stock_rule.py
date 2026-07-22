from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_custom_move_fields(self):
        fields = super()._get_custom_move_fields()
        return fields + ["dimension_sale_line_id", "dimension_bom_id"]

    def _get_matching_bom(self, product_id, company_id, values):
        sale_line = self.env["sale.order.line"].browse(
            values.get("dimension_sale_line_id")
        ).exists()
        dimension_bom = self.env["mrp.bom"].browse(
            values.get("dimension_bom_id")
        ).exists()
        if not dimension_bom and sale_line:
            dimension_bom = sale_line.dimension_bom_id
        if dimension_bom:
            return dimension_bom
        return super()._get_matching_bom(product_id, company_id, values)

    def _prepare_mo_vals(
        self,
        product_id,
        product_qty,
        product_uom,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
        bom,
    ):
        mo_values = super()._prepare_mo_vals(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
            bom,
        )
        if values.get("dimension_sale_line_id"):
            mo_values.update({
                "dimension_sale_line_id": values["dimension_sale_line_id"],
                "dimension_width_cm": values.get("dimension_width_cm", 0.0),
                "dimension_height_cm": values.get("dimension_height_cm", 0.0),
                "dimension_m2": values.get("dimension_m2", 0.0),
                "dimension_ml": values.get("dimension_ml", 0.0),
                "dimension_value_ids": [(6, 0, values.get("dimension_value_ids", []))],
            })
        return mo_values

    def _make_mo_get_domain(self, procurement, bom):
        domain = super()._make_mo_get_domain(procurement, bom)
        sale_line_id = procurement.values.get("dimension_sale_line_id")
        if sale_line_id:
            domain += (("dimension_sale_line_id", "=", sale_line_id),)
        return domain
