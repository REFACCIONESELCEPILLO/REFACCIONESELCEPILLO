# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if not value or operator in expression.NEGATIVE_TERM_OPERATORS:
            return domain

        oem_domain = [("product_tmpl_id.vehicle_oem_lines.name", operator, value)]
        return expression.OR([domain, oem_domain])

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        results = super().name_search(name, args, operator, limit)
        if not name or operator in expression.NEGATIVE_TERM_OPERATORS:
            return results

        remaining_limit = None
        if limit:
            remaining_limit = max(limit - len(results), 0)
            if not remaining_limit:
                return results

        found_ids = [product_id for product_id, __display_name in results]
        domain = args or []
        oem_domain = expression.AND([
            domain,
            [("product_tmpl_id.vehicle_oem_lines.name", operator, name)],
        ])
        if found_ids:
            oem_domain = expression.AND([oem_domain, [("id", "not in", found_ids)]])

        products = self.search(
            oem_domain,
            limit=remaining_limit,
        )
        return results + [
            (product.id, product.display_name)
            for product in products.sudo()
        ]
