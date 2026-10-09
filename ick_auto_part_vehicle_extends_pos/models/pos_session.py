# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.osv import expression


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def get_auto_parts_panel(self, session_id, product_id):
        """Return contextual suggestions for a product in an open POS session."""
        session = self.browse(session_id).exists()
        if not session or session.state == "closed":
            raise UserError(_("La sesión del punto de venta ya no está disponible."))
        if session.user_id != self.env.user and not self.env.user.has_group(
            "point_of_sale.group_pos_manager"
        ):
            raise UserError(_("No tiene acceso a esta sesión del punto de venta."))

        product = self.env["product.product"].browse(product_id).exists()
        if not product:
            raise UserError(_("El producto seleccionado ya no está disponible."))
        product.check_access("read")

        product_model = self.env["product.product"]
        available_domain = session.config_id._get_available_product_domain()
        company_domain = [
            "|",
            ("company_id", "in", self.env.companies.ids),
            ("company_id", "=", False),
        ]

        compatible = product_model.search(
            expression.AND([
                available_domain,
                company_domain,
                [("motorcycle_ids.product_ids", "in", product.product_tmpl_id.ids),
                 ("id", "!=", product.id)],
            ]),
            limit=8,
        )

        codes = [
            code for code in product.product_tmpl_id.vehicle_oem_lines.mapped("name")
            if code
        ]
        equivalents = product_model.browse()
        if codes:
            equivalent_ids = self.env["sh.vehicle.oem"].search([
                ("name", "in", codes),
            ]).product_id.product_variant_ids.ids
            equivalents = product_model.search(
                expression.AND([
                    available_domain,
                    company_domain,
                    [("id", "in", equivalent_ids), ("id", "!=", product.id)],
                ]),
                limit=8,
            )

        template = product.product_tmpl_id
        template_fields = self.env["product.template"]._fields
        optional = template.optional_product_ids.product_variant_ids
        accessories = (
            template.accessory_product_ids
            if "accessory_product_ids" in template_fields
            else product_model.browse()
        )
        alternatives = (
            template.alternative_product_ids.product_variant_ids
            if "alternative_product_ids" in template_fields
            else product_model.browse()
        )

        def available(records):
            if not records:
                return records
            return product_model.search(
                expression.AND([
                    available_domain,
                    company_domain,
                    [("id", "in", records.ids), ("id", "!=", product.id)],
                ]),
                limit=8,
            )

        optional = available(optional)
        accessories = available(accessories)
        alternatives = available(alternatives)

        # Keep every card in a single section, using the same priority as Sale.
        equivalents -= compatible
        optional -= compatible | equivalents
        accessories -= compatible | equivalents | optional
        alternatives -= compatible | equivalents | optional | accessories

        return {
            "active_product": self._auto_pos_serialize(session, product)[0],
            "compatible": self._auto_pos_serialize(session, compatible),
            "equivalents": self._auto_pos_serialize(session, equivalents),
            "optional": self._auto_pos_serialize(session, optional),
            "accessories": self._auto_pos_serialize(session, accessories),
            "alternatives": self._auto_pos_serialize(session, alternatives),
        }

    def _auto_pos_serialize(self, session, products):
        products = products[:8]
        warehouse = session.config_id.picking_type_id.warehouse_id
        quantities = {product.id: 0.0 for product in products}
        if products and warehouse:
            rows = self.env["product.warehouse.availability"].search([
                ("product_id", "in", products.ids),
                ("warehouse_id", "=", warehouse.id),
            ])
            for row in rows:
                quantities[row.product_id.id] += row.free_quantity
        return [{
            "id": product.id,
            "name": product.display_name,
            "default_code": product.default_code or "",
            "brand": product.brand_name or "",
            "available_qty": quantities[product.id],
            "uom": product.uom_id.name or "",
            "has_compatibility": bool(product.motorcycle_ids),
            "image_url": "/web/image/product.product/%s/image_128" % product.id,
        } for product in products]

    @api.model
    def get_auto_product_compatibility(self, session_id, product_id, limit=100):
        self._auto_pos_validate_session_product(session_id, product_id)
        product = self.env["product.product"].browse(product_id)
        domain = [
            ("product_ids", "in", product.product_tmpl_id.id),
            "|",
            ("company_id", "in", self.env.companies.ids),
            ("company_id", "=", False),
        ]
        vehicle_model = self.env["motorcycle.motorcycle"]
        count = vehicle_model.search_count(domain)
        vehicles = vehicle_model.search(domain, limit=max(1, min(limit, 200)))
        return {
            "product": product.display_name,
            "applications": product._auto_pos_application_rows(vehicles),
            "part_details": product._auto_pos_part_details(),
            "application_count": count,
            "truncated": count > len(vehicles),
            "oem": [{
                "id": line.id,
                "code": line.name or "",
                "brand": line.brand_id.name if line.brand_id else "",
            } for line in product.product_tmpl_id.vehicle_oem_lines if line.name],
        }

    @api.model
    def get_auto_product_specifications(self, session_id, product_id):
        session, product = self._auto_pos_validate_session_product(session_id, product_id)
        lines = product.product_tmpl_id.specification_lines.filtered(
            lambda line: not line.company_id or line.company_id == session.company_id
        )
        return {
            "specifications": [{
                "id": line.id,
                "label": line.name or "",
                "value": line.value or "",
            } for line in lines],
        }

    @api.model
    def get_auto_product_stock(self, session_id, product_id):
        session, product = self._auto_pos_validate_session_product(
            session_id, product_id
        )
        rows = self.env["product.warehouse.availability"].search([
            ("product_id", "=", product.id),
            ("company_id", "=", session.company_id.id),
        ], order="warehouse_id")
        return {
            "product": product.display_name,
            "warehouses": [{
                "id": row.warehouse_id.id,
                "name": row.warehouse_id.name,
                "available": row.free_quantity,
                "uom": row.product_uom_id.name,
            } for row in rows],
        }

    def _auto_pos_validate_session_product(self, session_id, product_id):
        session = self.browse(session_id).exists()
        product = self.env["product.product"].browse(product_id).exists()
        if not session or session.state == "closed":
            raise UserError(_("La sesión del punto de venta ya no está disponible."))
        if session.user_id != self.env.user and not self.env.user.has_group(
            "point_of_sale.group_pos_manager"
        ):
            raise UserError(_("No tiene acceso a esta sesión del punto de venta."))
        if not product:
            raise UserError(_("El producto seleccionado ya no está disponible."))
        product.check_access("read")
        return session, product
