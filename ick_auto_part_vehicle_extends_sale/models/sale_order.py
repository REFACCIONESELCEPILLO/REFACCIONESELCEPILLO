# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_auto_context_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto activo del asistente",
        copy=False,
        help="Producto de la cotización que alimenta el asistente contextual.",
    )
    x_auto_panel = fields.Json(
        string="Panel automotriz",
        compute="_compute_x_auto_panel",
    )

    # ------------------------------------------------------------------
    # Panel computation
    # ------------------------------------------------------------------
    @api.depends(
        "x_auto_context_product_id",
        "company_id",
        "warehouse_id",
        "pricelist_id",
        "order_line.product_id",
        "order_line.product_uom_qty",
        "order_line.display_type",
        "x_auto_context_product_id.motorcycle_ids",
        "x_auto_context_product_id.product_tmpl_id.optional_product_ids",
        "x_auto_context_product_id.product_tmpl_id.accessory_product_ids",
        "x_auto_context_product_id.product_tmpl_id.alternative_product_ids",
        "x_auto_context_product_id.product_tmpl_id.vehicle_oem_lines.name",
    )
    def _compute_x_auto_panel(self):
        for order in self:
            order.x_auto_panel = order._x_auto_build_panel()

    def _x_auto_build_panel(self):
        """Build the JSON structure consumed by the automotive panel (OWL)."""
        self.ensure_one()
        company_domain = [
            "|",
            ("company_id", "in", self.env.companies.ids),
            ("company_id", "=", False),
        ]

        ordered_products = self.order_line.filtered(
            lambda line: not line.display_type and line.product_id
        ).product_id

        active_product = self.x_auto_context_product_id
        if active_product not in ordered_products:
            # Legacy quotations may not have an explicit context yet. The
            # latest valid line best represents what the seller just added.
            active_product = ordered_products[-1:]
        if not active_product:
            return {
                "active_product": False,
                "compatible": [],
                "equivalents": [],
                "optional": [],
                "accessories": [],
                "alternatives": [],
            }

        # The active quotation product drives both automotive and commercial
        # context; recommendations never merge every order line together.
        # Parts compatible with the reference vehicle(s).
        compatible = self.env["product.product"].search(
            company_domain + [
                ("motorcycle_ids.product_ids", "in", active_product.product_tmpl_id.ids),
                ("id", "not in", ordered_products.ids),
            ],
            limit=8,
        )
        # Parts sharing the same OEM code (equivalences).
        equivalents = self._x_auto_oem_equivalents(active_product)

        # Cross-sell declared on the product templates of the order. Optional
        # products come from ``sale``; accessories and alternatives come from
        # ``website_sale``, so they are read only when available.
        templates = active_product.product_tmpl_id
        template_fields = self.env["product.template"]._fields
        optional = templates.optional_product_ids.product_variant_id
        accessories = (
            templates.accessory_product_ids
            if "accessory_product_ids" in template_fields
            else self.env["product.product"].browse()
        )
        alternatives = (
            templates.alternative_product_ids.product_variant_id
            if "alternative_product_ids" in template_fields
            else self.env["product.product"].browse()
        )

        # Never suggest what is already in the order.
        ordered = ordered_products
        compatible -= ordered
        equivalents -= ordered
        optional = optional.filtered_domain(company_domain) - ordered
        accessories = accessories.filtered_domain(company_domain) - ordered
        alternatives = alternatives.filtered_domain(company_domain) - ordered

        # Remove duplicates across sections (priority to earlier ones).
        equivalents -= compatible
        optional -= compatible | equivalents
        accessories -= compatible | equivalents | optional
        alternatives -= compatible | equivalents | optional | accessories

        return {
            "active_product": self._x_auto_serialize_products(active_product, limit=1)[0],
            "compatible": self._x_auto_serialize_products(compatible),
            "equivalents": self._x_auto_serialize_products(equivalents),
            "optional": self._x_auto_serialize_products(optional),
            "accessories": self._x_auto_serialize_products(accessories),
            "alternatives": self._x_auto_serialize_products(alternatives),
        }

    def _x_auto_oem_equivalents(self, product):
        """Products sharing an OEM code with the active product."""
        self.ensure_one()
        codes = product.product_tmpl_id.vehicle_oem_lines.mapped("name")
        codes = [code for code in codes if code]
        if not codes:
            return self.env["product.product"]
        oem_lines = self.env["sh.vehicle.oem"].search([("name", "in", codes)])
        return oem_lines.product_id.product_variant_id

    def _x_auto_get_price(self, product):
        """Unit price for the given product using the order pricelist."""
        self.ensure_one()
        if self.pricelist_id:
            try:
                return self.pricelist_id._get_product_price(
                    product,
                    1.0,
                    uom=product.uom_id,
                    date=self.date_order,
                )
            except Exception:  # pragma: no cover - defensive
                pass
        return product.lst_price

    def _x_auto_serialize_products(self, products, limit=8):
        self.ensure_one()
        products = products.filtered(
            lambda product: not product.company_id
            or product.company_id in self.env.companies
        )[:limit]
        available_by_product = {product.id: 0.0 for product in products}
        availability_rows = self.env["product.warehouse.availability"].search([
            ("product_id", "in", products.ids),
            ("warehouse_id", "=", self.warehouse_id.id),
        ])
        for availability_row in availability_rows:
            available_by_product[availability_row.product_id.id] += (
                availability_row.free_quantity
            )
        result = []
        for product in products:
            result.append({
                "id": product.id,
                "name": product.display_name,
                "default_code": product.default_code or "",
                # Public brand interface supplied by sh_product_brand_sale.
                "brand": product.brand_name or "",
                "price": self._x_auto_get_price(product),
                "list_price": product.list_price,
                "uom": product.uom_id.name or "",
                # Quantity that can still be sold: physical minus reserved.
                # Never expose qty_available ("A mano") in the sales grid.
                "available_qty": available_by_product[product.id],
                "has_compatibility": bool(product.motorcycle_ids),
                "image_url": "/web/image/product.product/%s/image_128" % product.id,
            })
        return result

    def _x_auto_serialize_vehicles(self, vehicles):
        self.ensure_one()
        result = []
        for vehicle in vehicles:
            result.append({
                "id": vehicle.id,
                "name": vehicle.display_name,
                "image_url":
                    "/web/image/motorcycle.motorcycle/%s/vehicle_image" % vehicle.id,
            })
        return result

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_auto_add_product(self, product_id):
        """Add a product (or increase its quantity) on the current order."""
        self.ensure_one()
        product = self.env["product.product"].browse(product_id)
        if not product.exists():
            raise UserError(_("El producto seleccionado ya no está disponible."))
        product.check_access("read")
        if not product.sale_ok:
            raise UserError(_("El producto seleccionado no puede venderse."))
        if product.company_id and product.company_id not in self.env.companies:
            raise UserError(
                _("El producto seleccionado pertenece a otra compañía."))
        if self.state not in ("draft", "sent"):
            raise UserError(_(
                "Solo se pueden agregar productos a cotizaciones en borrador "
                "o enviadas."
            ))
        line = self.order_line.filtered(
            lambda line: not line.display_type and line.product_id == product
        )[:1]
        if line:
            line.product_uom_qty += 1
        else:
            self.write({
                "order_line": [(0, 0, {
                    "product_id": product.id,
                    "product_uom_qty": 1.0,
                })],
            })
        # Every product added from the assistant becomes the new commercial
        # context, so its own compatible/optional/accessory products replace
        # the previous recommendations immediately.
        self.x_auto_context_product_id = product
        return True

    def action_auto_product_compatibility(self, product_id):
        """Open the compatibility rules (vehicles) of a given product."""
        product = self.env["product.product"].browse(product_id)
        if not product.exists():
            raise UserError(_("El producto seleccionado ya no está disponible."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Compatibilidad: %s") % (product.display_name or ""),
            "res_model": "motorcycle.motorcycle",
            "view_mode": "list,form",
            "domain": [("product_ids", "in", product.product_tmpl_id.ids)],
            "context": {"create": False},
            "target": "new",
        }

    @api.model
    def get_auto_product_compatibility(self, product_id, limit=100):
        """Return compact compatibility data for the sales assistant dialog."""
        product = self.env["product.product"].browse(product_id).exists()
        if not product:
            raise UserError(_("El producto seleccionado ya no está disponible."))
        product.check_access("read")

        vehicle_model = self.env["motorcycle.motorcycle"]
        vehicle_domain = [
            ("product_ids", "in", product.product_tmpl_id.id),
            "|",
            ("company_id", "in", self.env.companies.ids),
            ("company_id", "=", False),
        ]
        application_count = vehicle_model.search_count(vehicle_domain)
        vehicles = vehicle_model.search(
            vehicle_domain,
            limit=max(1, min(limit, 200)),
        )
        applications = []
        for vehicle in vehicles:
            applications.append({
                "id": vehicle.id,
                "make": vehicle.make_id.name or "",
                "model": vehicle.mmodel_id.name or "",
                "type": vehicle.type_id.name or "",
                "year_from": vehicle.year_id.name or "",
                "year_to": vehicle.end_year_id.name or "",
                "engines": ", ".join(vehicle.engine.mapped("name")),
                "transmissions": ", ".join(
                    vehicle.transmission_ids.mapped("name")
                ),
                "grades": ", ".join(vehicle.garde.mapped("name")),
            })

        oem_lines = product.product_tmpl_id.vehicle_oem_lines
        return {
            "product": {
                "id": product.id,
                "name": product.display_name,
                "default_code": product.default_code or "",
                # Public brand interface supplied by sh_product_brand_sale.
                "brand": product.brand_name or "",
                "image_url": "/web/image/product.product/%s/image_128" % product.id,
            },
            "applications": applications,
            "application_count": application_count,
            "truncated": application_count > len(applications),
            "oem": [
                {
                    "id": line.id,
                    "code": line.name or "",
                    "brand": line.brand_id.name if line.brand_id else "",
                }
                for line in oem_lines
                if line.name
            ],
        }

    @api.model
    def get_auto_product_stock(self, product_id, company_id=None):
        """Return warehouse availability for one recommendation product."""
        product = self.env["product.product"].browse(product_id).exists()
        if not product:
            raise UserError(_("El producto seleccionado ya no está disponible."))
        product.check_access("read")

        company = self.env["res.company"].browse(company_id).exists()
        if not company:
            company = self.env.company
        rows = self.env["product.warehouse.availability"].search_read(
            [
                ("product_id", "=", product.id),
                ("company_id", "=", company.id),
            ],
            [
                "warehouse_id",
                "free_quantity",
                "product_uom_id",
            ],
            order="warehouse_id",
        )
        return {
            "product": {
                "id": product.id,
                "name": product.display_name,
                "default_code": product.default_code or "",
                "image_url": "/web/image/product.product/%s/image_128" % product.id,
            },
            "warehouses": [
                {
                    "id": row["warehouse_id"][0],
                    "name": row["warehouse_id"][1],
                    "available": row["free_quantity"],
                    "uom": row["product_uom_id"][1],
                }
                for row in rows
            ],
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    x_auto_available_qty = fields.Float(
        string="Disponibilidad",
        compute="_compute_x_auto_available_qty",
        compute_sudo=True,
        digits="Product Unit of Measure",
        help="Cantidad disponible para venta: existencia física menos reservada.",
    )

    @api.depends("product_id", "order_id.warehouse_id")
    def _compute_x_auto_available_qty(self):
        for line in self:
            line.x_auto_available_qty = 0.0

        product_lines = self.filtered(
            lambda line: line.product_id and not line.display_type
        )
        if not product_lines:
            return

        rows = self.env["product.warehouse.availability"].sudo().search([
            ("product_id", "in", product_lines.product_id.ids),
            ("warehouse_id", "in", product_lines.order_id.warehouse_id.ids),
        ])
        available_by_product_warehouse = {}
        for row in rows:
            key = (row.product_id.id, row.warehouse_id.id)
            available_by_product_warehouse[key] = (
                available_by_product_warehouse.get(key, 0.0)
                + row.free_quantity
            )
        for line in product_lines:
            line.x_auto_available_qty = available_by_product_warehouse.get(
                (line.product_id.id, line.order_id.warehouse_id.id),
                0.0,
            )

    @api.onchange("product_id")
    def _onchange_x_auto_context_product(self):
        for line in self:
            if line.product_id and line.order_id:
                line.order_id.x_auto_context_product_id = line.product_id

    def action_auto_set_context_product(self):
        """Make this quotation line the explicit context of the assistant."""
        self.ensure_one()
        if self.display_type or not self.product_id:
            return False
        if self.order_id.state not in ("draft", "sent"):
            raise UserError(_(
                "El asistente sólo puede cambiar de producto en cotizaciones."
            ))
        self.order_id.x_auto_context_product_id = self.product_id
        return True

    def action_auto_open_warehouse_availability(self):
        """Show only sellable availability for this product by warehouse."""
        self.ensure_one()
        if self.display_type or not self.product_id:
            return False
        availability_view = self.env.ref(
            "ick_auto_part_vehicle_extends_sale."
            "product_warehouse_availability_sale_list"
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Disponibilidad: %s") % self.product_id.display_name,
            "res_model": "product.warehouse.availability",
            "view_mode": "list",
            "views": [(availability_view.id, "list")],
            "domain": [
                ("product_id", "=", self.product_id.id),
                ("company_id", "=", self.order_id.company_id.id),
            ],
            "context": {"create": False, "edit": False, "delete": False},
            "target": "new",
        }
