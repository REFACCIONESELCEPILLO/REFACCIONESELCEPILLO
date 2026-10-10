# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
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
    ick_website_availability_text = fields.Text(
        string="Disponibilidad web",
        compute="_compute_ick_website_availability",
        compute_sudo=True,
    )
    ick_oem_codes_kanban = fields.Text(
        string="Compatibilidad OEM",
        compute="_compute_ick_oem_codes_kanban",
        compute_sudo=True,
    )
    ick_kanban_compatibility_codes = fields.Json(
        string="Códigos de compatibilidad kanban",
        compute="_compute_ick_kanban_compatibility_codes",
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
        warehouse_data, quantities = self._get_warehouse_quantities()

        for product in self:
            lines = []
            free_qty = sum(
                values["free_quantity"]
                for values in quantities.get(product.id, {}).values()
            )
            for warehouse, __parent_path in warehouse_data:
                warehouse_qty = quantities[product.id][warehouse.id]["free_quantity"]
                if warehouse_qty > 0:
                    lines.append(
                        "%s: %.3f %s"
                        % (warehouse.display_name, warehouse_qty, product.uom_id.name)
                    )
            product.ick_website_free_qty = free_qty
            product.ick_website_has_free_stock = free_qty > 0
            if lines:
                product.ick_website_availability_text = "\n".join([
                    "Disponible total: %.3f %s"
                    % (free_qty, product.uom_id.name),
                    *lines,
                ])
            else:
                product.ick_website_availability_text = "No disponible"

    @api.depends("vehicle_oem_lines.name", "vehicle_oem_lines.brand_id")
    def _compute_ick_oem_codes_kanban(self):
        for product in self:
            lines = []
            for oem_line in product.vehicle_oem_lines:
                if not oem_line.name:
                    continue
                if oem_line.brand_id:
                    lines.append("%s: %s" % (oem_line.brand_id.name, oem_line.name))
                else:
                    lines.append(oem_line.name)
            product.ick_oem_codes_kanban = "\n".join(lines)

    @api.depends("vehicle_oem_lines.name", "vehicle_oem_lines.brand_id")
    def _compute_ick_kanban_compatibility_codes(self):
        for template in self:
            template.ick_kanban_compatibility_codes = [
                {
                    "id": line.id,
                    "code": line.name,
                    "brand": line.brand_id.name or "",
                    "label": "%s: %s" % (line.brand_id.name, line.name)
                    if line.brand_id else line.name,
                }
                for line in template.vehicle_oem_lines
                if line.name
            ]

    @api.model
    def _ick_kanban_selected_warehouse(self):
        """Resolve the selected or user-default warehouse for product tools."""
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

    @api.model
    def _ick_kanban_available_by_product(self, products, warehouse):
        available = {product.id: 0.0 for product in products}
        if not products or not warehouse:
            return available
        rows = self.env["product.warehouse.availability"].sudo().search([
            ("product_id", "in", products.ids),
            ("warehouse_id", "=", warehouse.id),
            ("company_id", "=", warehouse.company_id.id),
        ])
        for row in rows:
            available[row.product_id.id] += row.free_quantity
        return available

    @api.model
    def get_ick_kanban_product_stock(self, product_id):
        """Return sellable availability for one product in every warehouse."""
        product = self.env["product.product"].browse(product_id).exists()
        if not product:
            raise UserError("El producto seleccionado ya no está disponible.")
        product.check_access("read")
        selected_warehouse = self._ick_kanban_selected_warehouse()
        company = selected_warehouse.company_id or self.env.company
        warehouses = self.env["stock.warehouse"].search([
            ("company_id", "=", company.id),
        ], order="name")
        rows = self.env["product.warehouse.availability"].sudo().search([
            ("product_id", "=", product.id),
            ("company_id", "=", company.id),
            ("warehouse_id", "in", warehouses.ids),
        ])
        available_by_warehouse = {warehouse.id: 0.0 for warehouse in warehouses}
        uom_by_warehouse = {}
        for row in rows:
            available_by_warehouse[row.warehouse_id.id] += row.free_quantity
            uom_by_warehouse[row.warehouse_id.id] = row.product_uom_id.name
        return {
            "product": {
                "id": product.id,
                "name": product.display_name,
                "sku": product.default_code or "",
                "image_url": "/web/image/product.product/%s/image_128" % product.id,
            },
            "selected_warehouse_id": selected_warehouse.id,
            "warehouses": [{
                "id": warehouse.id,
                "name": warehouse.display_name,
                "available": available_by_warehouse[warehouse.id],
                "uom": uom_by_warehouse.get(warehouse.id)
                or product.uom_id.name or "",
                "selected": warehouse == selected_warehouse,
            } for warehouse in warehouses],
        }

    def get_ick_kanban_compatibility(self, oem_line_id=False):
        self.ensure_one()
        self.check_access("read")
        line = self.vehicle_oem_lines.filtered(
            lambda item: item.id == oem_line_id
        )[:1]
        products = self.env["product.product"]
        if line and line.name:
            products = products.search([
                ("default_code", "=", line.name.strip()),
                "|",
                ("company_id", "in", self.env.companies.ids),
                ("company_id", "=", False),
            ])
        warehouse = self._ick_kanban_selected_warehouse()
        available_by_product = self._ick_kanban_available_by_product(
            products, warehouse
        )
        rows = []
        for product in products:
            vehicles = product.motorcycle_ids.filtered(
                lambda vehicle: not vehicle.company_id
                or vehicle.company_id in self.env.companies
            )
            product_values = {
                "id": product.id,
                "name": product.display_name,
                "sku": product.default_code or "",
                "brand": product.brand.name or "",
                "available_qty": available_by_product[product.id],
                "uom": product.uom_id.name or "",
                "image_url": "/web/image/product.product/%s/image_128" % product.id,
            }
            if vehicles:
                for vehicle in vehicles:
                    rows.append({
                        "key": "%s-%s" % (product.id, vehicle.id),
                        "product": product_values,
                        "vehicle": {
                            "id": vehicle.id,
                            "make": vehicle.make_id.name or "",
                            "model": vehicle.mmodel_id.name or "",
                            "type": vehicle.type_id.name or "",
                            "year_from": vehicle.year_id.name or "",
                            "year_to": vehicle.end_year_id.name or "",
                        },
                    })
            else:
                rows.append({
                    "key": "%s-none" % product.id,
                    "product": product_values,
                    "vehicle": False,
                })
        return {
            "title": line.name if line else self.name,
            "code": line.name if line else "",
            "code_brand": line.brand_id.name if line and line.brand_id else "",
            "selected_warehouse": {
                "id": warehouse.id,
                "name": warehouse.display_name or "",
            } if warehouse else False,
            "rows": rows,
            "product_count": len(products),
        }

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
