# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


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

    @api.model
    def _ick_kanban_selected_warehouse(self):
        """Resolve the warehouse used by the product workspace."""
        warehouse_id = (
            self.env.context.get("warehouse_id")
            or self.env.context.get("warehouse")
        )
        warehouse = self.env["stock.warehouse"].browse(warehouse_id).exists()
        if not warehouse or warehouse.company_id not in self.env.companies:
            warehouse = self.env.user.with_company(
                self.env.company
            )._get_default_warehouse_id()
        if warehouse.company_id not in self.env.companies:
            return self.env["stock.warehouse"]
        return warehouse

    def _ick_kanban_product_values(self, products, warehouse):
        products = products.exists().filtered(
            lambda product: not product.company_id
            or product.company_id in self.env.companies
        )
        available_by_product = {product.id: 0.0 for product in products}
        if products and warehouse:
            rows = self.env["product.warehouse.availability"].sudo().search([
                ("product_id", "in", products.ids),
                ("warehouse_id", "=", warehouse.id),
                ("company_id", "=", warehouse.company_id.id),
            ])
            for row in rows:
                available_by_product[row.product_id.id] += row.free_quantity
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

    @api.model
    def get_ick_kanban_product_stock(self, product_id):
        """Return sellable availability for a related product by warehouse."""
        product = self.env["product.product"].browse(product_id).exists()
        if not product:
            raise UserError("El producto seleccionado ya no está disponible.")
        product.check_access("read")
        company = self.env.company
        selected_warehouse = self._ick_kanban_selected_warehouse()
        rows = self.env["product.warehouse.availability"].sudo().search([
            ("product_id", "=", product.id),
            ("company_id", "=", company.id),
        ], order="warehouse_id")
        return {
            "product": {
                "id": product.id,
                "name": product.display_name,
                "sku": product.default_code or "",
                "image_url": "/web/image/product.product/%s/image_128" % product.id,
            },
            "selected_warehouse_id": selected_warehouse.id,
            "warehouses": [{
                "id": row.warehouse_id.id,
                "name": row.warehouse_id.display_name,
                "available": row.free_quantity,
                "uom": row.product_uom_id.name or product.uom_id.name or "",
                "selected": row.warehouse_id == selected_warehouse,
            } for row in rows],
        }
