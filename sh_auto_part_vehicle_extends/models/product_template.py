# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ick_default_code = fields.Char(
        string="SKU",
        compute="_compute_ick_default_code",
        compute_sudo=True,
    )
    ick_website_free_qty = fields.Float(
        string="Disponible libre en almacenes",
        compute="_compute_ick_website_availability",
        compute_sudo=True,
    )
    ick_website_has_free_stock = fields.Boolean(
        string="Tiene disponibilidad libre",
        compute="_compute_ick_website_availability",
        compute_sudo=True,
    )

    @api.depends("product_variant_ids.default_code")
    def _compute_ick_default_code(self):
        for product in self:
            variant = product.product_variant_id or product.product_variant_ids[:1]
            product.ick_default_code = variant.default_code or False

    @api.depends(
        "product_variant_ids.stock_quant_ids.quantity",
        "product_variant_ids.stock_quant_ids.reserved_quantity",
        "product_variant_ids.stock_quant_ids.location_id",
    )
    def _compute_ick_website_availability(self):
        _warehouse_data, quantities = self._get_warehouse_quantities()

        for product in self:
            free_qty = sum(
                values["free_quantity"]
                for values in quantities.get(product.id, {}).values()
            )
            product.ick_website_free_qty = free_qty
            product.ick_website_has_free_stock = free_qty > 0

    @api.model
    def _search_get_detail(self, website, order, options):
        result = super()._search_get_detail(website, order, options)
        search_fields = list(result.get("search_fields", []))
        if "vehicle_oem_lines.name" not in search_fields:
            search_fields.append("vehicle_oem_lines.name")
        result["search_fields"] = search_fields
        return result

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if not value or operator in expression.NEGATIVE_TERM_OPERATORS:
            return domain

        oem_domain = [("vehicle_oem_lines.name", operator, value)]
        return expression.OR([domain, oem_domain])
