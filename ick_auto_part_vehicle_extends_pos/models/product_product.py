# -*- coding: utf-8 -*-
from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        return list(dict.fromkeys([*fields, "free_qty"]))

    def _load_pos_data(self, data):
        config = self.env["pos.config"].browse(
            data["pos.config"]["data"][0]["id"]
        )
        warehouse = config.picking_type_id.warehouse_id
        product = self.with_context(warehouse_id=warehouse.id) if warehouse else self
        return super(ProductProduct, product)._load_pos_data(data)

    def get_product_info_pos(self, price, quantity, pos_config_id):
        result = super().get_product_info_pos(price, quantity, pos_config_id)
        config = self.env["pos.config"].browse(pos_config_id)
        availability = self.env["product.warehouse.availability"].search([
            ("product_id", "=", self.id),
            ("company_id", "=", config.company_id.id),
        ])
        free_by_warehouse = {}
        for row in availability:
            free_by_warehouse[row.warehouse_id.id] = (
                free_by_warehouse.get(row.warehouse_id.id, 0.0)
                + row.free_quantity
            )
        for warehouse in result.get("warehouses", []):
            warehouse["available_quantity"] = free_by_warehouse.get(
                warehouse["id"], 0.0
            )
            warehouse.pop("forecasted_quantity", None)
        result["auto_oem"] = [{
            "id": line.id,
            "code": line.name or "",
            "brand": line.brand_id.name if line.brand_id else "",
        } for line in self.product_tmpl_id.vehicle_oem_lines if line.name]
        vehicle_model = self.env["motorcycle.motorcycle"]
        domain = [
            ("product_ids", "in", self.product_tmpl_id.id),
            "|", ("company_id", "=", config.company_id.id),
            ("company_id", "=", False),
        ]
        vehicles = vehicle_model.search(domain, limit=100)
        result["auto_application_count"] = vehicle_model.search_count(domain)
        result["auto_applications"] = self._auto_pos_application_rows(vehicles)
        result["auto_product"] = {
            "name": self.display_name,
            "default_code": self.default_code or "",
            "brand": self.brand_name or "",
            "image_url": "/web/image/product.product/%s/image_128" % self.id,
        }
        result["auto_part_details"] = self._auto_pos_part_details()
        return result

    def _auto_pos_application_rows(self, vehicles):
        """Use the same template attributes in both POS compatibility dialogs."""
        self.ensure_one()
        template = self.product_tmpl_id
        return [{
            "id": vehicle.id,
            "make": vehicle.make_id.name or "",
            "model": vehicle.mmodel_id.name or "",
            "type": vehicle.type_id.name or "",
            "year_from": vehicle.year_id.name or "",
            "year_to": vehicle.end_year_id.name or "",
            "engines": ", ".join(template.engine.mapped("name")),
            "transmissions": ", ".join(template.transmission_ids.mapped("name")),
            "grades": ", ".join(template.garde.mapped("name")),
        } for vehicle in vehicles]

    def _auto_pos_part_details(self):
        self.ensure_one()
        template = self.product_tmpl_id
        return [
            {"label": label, "value": value}
            for label, value in [
                ("Tipo de producto de vehículo", ", ".join(template.product_type.mapped("name"))),
                ("Marca", self.brand_name or ""),
                ("Hecho en", self.made_in.name or ""),
            ] if value
        ]
