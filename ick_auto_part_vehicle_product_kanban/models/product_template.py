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

    def _ick_kanban_product_values(self, products, warehouse):
        products = products.exists().filtered(
            lambda product: not product.company_id
            or product.company_id in self.env.companies
        )
        available_by_product = self._ick_kanban_available_by_product(
            products, warehouse
        )
        return [{
            "id": product.id,
            "name": product.display_name,
            "sku": product.default_code or "",
            "brand": product.brand_name or "",
            "price": product.lst_price,
            "currency": product.currency_id.name or "",
            # Sellable stock: physical quantity minus reservations.
            "available_qty": available_by_product[product.id],
            "uom": product.uom_id.name or "",
            "image_url": "/web/image/product.product/%s/image_128" % product.id,
        } for product in products]

    def get_ick_kanban_related_products(self):
        self.ensure_one()
        self.check_access("read")
        optional = self.optional_product_ids.product_variant_id
        accessories = self.accessory_product_ids
        suggested = self.alternative_product_ids.product_variant_id
        warehouse = self._ick_kanban_selected_warehouse()
        return {
            "product_name": self.display_name,
            "selected_warehouse": {
                "id": warehouse.id,
                "name": warehouse.display_name or "",
            } if warehouse else False,
            "sections": [
                {"key": "suggested", "label": "Productos sugeridos", "items": self._ick_kanban_product_values(suggested, warehouse)},
                {"key": "accessories", "label": "Accesorios", "items": self._ick_kanban_product_values(accessories, warehouse)},
                {"key": "optional", "label": "Opcionales", "items": self._ick_kanban_product_values(optional, warehouse)},
            ],
        }
