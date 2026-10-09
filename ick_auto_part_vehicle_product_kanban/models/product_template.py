# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ick_kanban_has_related = fields.Boolean(
        string="Tiene productos relacionados",
        compute="_compute_ick_kanban_has_related",
        compute_sudo=True,
    )

    @api.depends(
        "optional_product_ids",
        "accessory_product_ids",
        "alternative_product_ids",
    )
    def _compute_ick_kanban_has_related(self):
        for template in self:
            template.ick_kanban_has_related = bool(
                template.optional_product_ids
                or template.accessory_product_ids
                or template.alternative_product_ids
            )

    def _ick_kanban_product_values(self, products):
        products = products.exists().filtered(
            lambda product: not product.company_id
            or product.company_id in self.env.companies
        )
        return [{
            "id": product.id,
            "name": product.display_name,
            "sku": product.default_code or "",
            "brand": product.brand_name or "",
            "price": product.lst_price,
            "currency": product.currency_id.name or "",
            "image_url": "/web/image/product.product/%s/image_128" % product.id,
        } for product in products]

    def get_ick_kanban_related_products(self):
        self.ensure_one()
        self.check_access("read")
        optional = self.optional_product_ids.product_variant_id
        accessories = self.accessory_product_ids
        suggested = self.alternative_product_ids.product_variant_id
        return {
            "product_name": self.display_name,
            "sections": [
                {"key": "suggested", "label": "Productos sugeridos", "items": self._ick_kanban_product_values(suggested)},
                {"key": "accessories", "label": "Accesorios", "items": self._ick_kanban_product_values(accessories)},
                {"key": "optional", "label": "Opcionales", "items": self._ick_kanban_product_values(optional)},
            ],
        }
