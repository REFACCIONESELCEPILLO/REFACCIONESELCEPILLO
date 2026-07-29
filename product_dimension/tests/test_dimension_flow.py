from unittest.mock import patch

from odoo import Command
from odoo.addons.sale.controllers.product_configurator import (
    SaleProductConfiguratorController,
)
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..controllers.product_configurator import (
    DimensionSaleProductConfiguratorController,
)


@tagged("post_install", "-at_install")
class TestDimensionFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attribute = cls.env["product.attribute"].create({
            "name": "Moldura",
            "create_variant": "no_variant",
            "dimension_type": "perimeter",
            "component_required": True,
        })
        cls.attribute_value = cls.env["product.attribute.value"].create({
            "name": "Moldura nogal",
            "attribute_id": cls.attribute.id,
        })
        cls.finished_template = cls.env["product.template"].create({
            "name": "Cuadro personalizado",
            "list_price": 500.0,
            "dimension_enabled": True,
        })
        cls.attribute_line = cls.env["product.template.attribute.line"].create({
            "product_tmpl_id": cls.finished_template.id,
            "attribute_id": cls.attribute.id,
            "value_ids": [Command.set(cls.attribute_value.ids)],
        })
        cls.ptav = cls.attribute_line.product_template_value_ids
        cls.component = cls.env["product.product"].create({
            "name": "Moldura nogal ML",
            "default_code": "MOL-NOG-001",
            "standard_price": 125.0,
            "type": "consu",
            "is_storable": True,
        })
        cls.vendor = cls.env["res.partner"].create({
            "name": "Proveedor de molduras",
            "supplier_rank": 1,
        })
        cls.env["product.supplierinfo"].create({
            "partner_id": cls.vendor.id,
            "product_tmpl_id": cls.component.product_tmpl_id.id,
            "min_qty": 0.0,
            "price": 125.0,
        })
        cls.placeholder = cls.env["product.product"].create({
            "name": "Molduras (Base)",
            "type": "consu",
            "is_storable": True,
        })
        cls.attribute_value.write({
            "component_product_id": cls.component.id,
            "component_calculation": "attribute",
            "component_qty_factor": 1.0,
        })
        cls.ptav.write({
            "pricing_mode": "perimeter",
            "dimension_price": 100.0,
        })

    def test_component_is_configured_on_attribute_value(self):
        self.assertEqual(self.attribute_value.component_product_id, self.component)
        self.assertEqual(
            self.attribute_value.component_internal_reference,
            "MOL-NOG-001",
        )
        self.assertAlmostEqual(self.attribute_value.component_cost, 125.0)
        self.assertEqual(self.ptav.component_product_id, self.component)
        self.assertEqual(self.ptav.component_sku, "MOL-NOG-001")
        self.assertAlmostEqual(self.ptav.component_cost, 125.0)
        matches = self.env["product.attribute.value"].name_search(
            name="MOL-NOG-001",
            args=[("attribute_id", "=", self.attribute.id)],
        )
        match_ids = [value_id for value_id, _name in matches]
        self.assertIn(self.attribute_value.id, match_ids)

    def test_purchase_attribute_selector_uses_reference_list_view(self):
        expected_view = self.env.ref(
            "product_dimension.product_attribute_value_purchase_select_list"
        )
        arch, selected_view = self.env["product.attribute.value"].with_context(
            list_view_ref=(
                "product_dimension.product_attribute_value_purchase_select_list"
            ),
        )._get_view(view_type="list")

        self.assertEqual(selected_view, expected_view)
        self.assertEqual(
            arch.xpath("//list/field/@name"),
            ["component_internal_reference", "name", "default_extra_price"],
        )

    def test_dimension_quotation_remains_editable_after_save(self):
        partner = self.env["res.partner"].create({
            "name": "Cliente de cotización editable",
        })
        dimension_order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "order_line": [Command.create({
                "product_id": self.finished_template.product_variant_id.id,
                "product_uom_qty": 1.0,
            })],
        })
        regular_product = self.env["product.product"].create({
            "name": "Producto sin configuración dimensional",
        })
        regular_order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "order_line": [Command.create({
                "product_id": regular_product.id,
                "product_uom_qty": 1.0,
            })],
        })

        self.assertIn(
            dimension_order,
            (dimension_order | regular_order)._get_editable_dimension_quotations(),
        )
        self.assertNotIn(
            regular_order,
            (dimension_order | regular_order)._get_editable_dimension_quotations(),
        )

    def test_reference_and_cost_are_editable_from_both_interfaces(self):
        self.attribute_value.write({
            "component_internal_reference": "MOL-NOG-EDIT",
            "component_cost": 130.0,
        })
        self.assertEqual(self.ptav.component_sku, "MOL-NOG-EDIT")
        self.assertAlmostEqual(self.ptav.component_cost, 130.0)
        self.assertEqual(self.component.default_code, "MOL-NOG-EDIT")
        self.assertAlmostEqual(self.component.standard_price, 130.0)

        self.ptav.write({
            "component_sku": "MOL-NOG-PTAV",
            "component_cost": 135.0,
        })
        self.assertEqual(
            self.attribute_value.component_internal_reference,
            "MOL-NOG-PTAV",
        )
        self.assertAlmostEqual(self.attribute_value.component_cost, 135.0)
        self.assertEqual(self.component.default_code, "MOL-NOG-PTAV")
        self.assertAlmostEqual(self.component.standard_price, 135.0)

    def test_attribute_value_configuration_action(self):
        action = self.attribute_value.action_open_dimension_configuration()
        self.assertEqual(action["res_model"], "product.attribute.value")
        self.assertEqual(action["res_id"], self.attribute_value.id)
        self.assertEqual(action["view_mode"], "form")

    def test_component_is_linked_from_unique_internal_reference(self):
        value = self.env["product.attribute.value"].create({
            "name": "Moldura vinculada por referencia",
            "attribute_id": self.attribute.id,
            "component_internal_reference": self.component.default_code,
        })
        unresolved = value._link_component_products_by_reference()
        self.assertFalse(unresolved)
        self.assertEqual(value.component_product_id, self.component)

    def test_component_reference_must_be_unique_to_link(self):
        duplicate_reference = "MOL-DUPLICADA"
        self.env["product.product"].create({
            "name": "Componente duplicado 1",
            "default_code": duplicate_reference,
            "type": "consu",
        })
        self.env["product.product"].create({
            "name": "Componente duplicado 2",
            "default_code": duplicate_reference,
            "type": "consu",
        })
        value = self.env["product.attribute.value"].create({
            "name": "Moldura con referencia duplicada",
            "attribute_id": self.attribute.id,
            "component_internal_reference": duplicate_reference,
        })
        unresolved = value._link_component_products_by_reference()
        self.assertEqual(unresolved, value)
        self.assertFalse(value.component_product_id)

    def test_na_values_are_not_described_manufactured_or_purchased(self):
        optional_attribute = self.env["product.attribute"].create({
            "name": "Vidrio opcional",
            "create_variant": "no_variant",
            "dimension_type": "area",
            "component_required": True,
        })
        na_value = self.env["product.attribute.value"].create({
            "name": "N/A Vidrio",
            "attribute_id": optional_attribute.id,
        })
        # Simulate legacy data where the checkbox was not marked.
        na_value.skip_component = False
        optional_line = self.env["product.template.attribute.line"].create({
            "product_tmpl_id": self.finished_template.id,
            "attribute_id": optional_attribute.id,
            "value_ids": [Command.set(na_value.ids)],
        })
        na_ptav = optional_line.product_template_value_ids
        optional_placeholder = self.env["product.product"].create({
            "name": "Vidrio (Base)",
            "type": "consu",
            "is_storable": True,
        })
        partner = self.env["res.partner"].create({"name": "Cliente solo moldura"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.finished_template.product_variant_id.id,
            "product_uom_qty": 1.0,
            "product_uom": self.finished_template.uom_id.id,
            "width_cm": 120.0,
            "height_cm": 180.0,
            "product_no_variant_attribute_value_ids": [
                Command.set((self.ptav | na_ptav).ids),
            ],
        })

        self.assertTrue(na_ptav.dimension_is_na)
        self.assertIn("Moldura: Moldura nogal", sale_line.name)
        self.assertNotIn("N/A", sale_line.name)
        procurement_values = sale_line._prepare_procurement_values()
        self.assertEqual(
            procurement_values["dimension_value_ids"],
            self.ptav.ids,
        )

        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": self.finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": self.finished_template.uom_id.id,
            "bom_line_ids": [
                Command.create({
                    "product_id": self.placeholder.id,
                    "product_qty": 1.0,
                    "product_uom_id": self.placeholder.uom_id.id,
                    "dimension_attribute_id": self.attribute.id,
                }),
                Command.create({
                    "product_id": optional_placeholder.id,
                    "product_qty": 1.0,
                    "product_uom_id": optional_placeholder.uom_id.id,
                    "dimension_attribute_id": optional_attribute.id,
                }),
            ],
        })
        dynamic_bom = sale_line._create_dimension_bom(
            sale_line._get_selected_dimension_values()
        )
        self.assertTrue(dynamic_bom.is_dimension_dynamic)
        self.assertFalse(dynamic_bom.active)
        self.assertEqual(dynamic_bom.dimension_source_bom_id, bom)
        self.assertEqual(dynamic_bom.bom_line_ids.product_id, self.component)
        self.assertEqual(dynamic_bom.bom_line_ids.dimension_value_id, self.ptav)
        self.assertNotIn(optional_placeholder, dynamic_bom.bom_line_ids.product_id)
        procurement_values = sale_line._prepare_procurement_values()
        self.assertEqual(procurement_values["bom_id"], dynamic_bom)
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        manufacture_rule = warehouse.manufacture_pull_id
        matching_bom = manufacture_rule._get_matching_bom(
            self.finished_template.product_variant_id,
            self.env.company,
            {"dimension_sale_line_id": sale_line.id},
        )
        self.assertEqual(matching_bom, dynamic_bom)
        self.assertIn(
            "dimension_bom_id",
            manufacture_rule._get_custom_move_fields(),
        )
        production = self.env["mrp.production"].create({
            "product_id": self.finished_template.product_variant_id.id,
            "product_qty": 1.0,
            "product_uom_id": self.finished_template.uom_id.id,
            "bom_id": bom.id,
            "picking_type_id": warehouse.manu_type_id.id,
            "location_src_id": warehouse.manu_type_id.default_location_src_id.id,
            "location_dest_id": warehouse.manu_type_id.default_location_dest_id.id,
            "dimension_sale_line_id": sale_line.id,
            "dimension_width_cm": 120.0,
            "dimension_height_cm": 180.0,
            "dimension_m2": 2.16,
            "dimension_ml": 6.0,
            "dimension_value_ids": [Command.set((self.ptav | na_ptav).ids)],
        })

        active_moves = production.move_raw_ids.filtered(
            lambda move: move.state != "cancel"
        )
        self.assertEqual(active_moves.product_id, self.component)
        self.assertNotIn(optional_placeholder, active_moves.product_id)

    def test_dynamic_base_variant_inherits_vendor(self):
        dynamic_attribute = self.env["product.attribute"].create({
            "name": "Impresión dinámica",
            "create_variant": "dynamic",
            "dimension_type": "area",
            "component_required": True,
        })
        dynamic_value = self.env["product.attribute.value"].create({
            "name": "Acrílico",
            "attribute_id": dynamic_attribute.id,
            "component_internal_reference": "IMP-ACR-001",
        })
        base_template = self.env["product.template"].create({
            "name": "Impresión (Base)",
            "type": "consu",
            "is_storable": True,
            "purchase_ok": True,
        })
        general_seller = self.env["product.supplierinfo"].create({
            "partner_id": self.vendor.id,
            "product_tmpl_id": base_template.id,
            "min_qty": 0.0,
            "price": 10.0,
        })
        finished_template = self.env["product.template"].create({
            "name": "Cuadro con impresión dinámica",
            "dimension_enabled": True,
        })
        finished_line = self.env["product.template.attribute.line"].create({
            "product_tmpl_id": finished_template.id,
            "attribute_id": dynamic_attribute.id,
            "value_ids": [Command.set(dynamic_value.ids)],
        })
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": finished_template.uom_id.id,
            "bom_line_ids": [Command.create({
                "product_id": base_template.product_variant_id.id,
                "product_qty": 1.0,
                "product_uom_id": base_template.uom_id.id,
                "dimension_attribute_id": dynamic_attribute.id,
            })],
        })
        variant_vendor = self.env["res.partner"].create({
            "name": "Proveedor exclusivo de acrílico",
            "supplier_rank": 1,
        })
        variant_seller = self.env["product.supplierinfo"].create({
            "partner_id": variant_vendor.id,
            "product_tmpl_id": base_template.id,
            "dimension_attribute_value_id": dynamic_value.id,
            "min_qty": 1.0,
            "price": 300.0,
        })

        component = finished_line.product_template_value_ids._get_or_create_bom_component(
            bom.bom_line_ids
        )
        self.assertTrue(component)
        self.assertEqual(component.product_tmpl_id, base_template)
        self.assertEqual(
            base_template.attribute_line_ids.attribute_id,
            dynamic_attribute,
        )
        self.assertEqual(
            base_template.attribute_line_ids.value_ids,
            dynamic_value,
        )
        self.assertIn(self.vendor, component._prepare_sellers(False).partner_id)
        self.assertFalse(general_seller.product_id)
        self.assertEqual(variant_seller.product_id, component)
        self.assertEqual(variant_seller.dimension_attribute_id, dynamic_attribute)

        generic_component = self.env["product.product"].create({
            "name": "Impresión (Base) genérica",
            "type": "consu",
            "is_storable": True,
        })
        dynamic_value.component_product_id = generic_component

        partner = self.env["res.partner"].create({
            "name": "Cliente con componente dinámico",
        })
        order = self.env["sale.order"].create({"partner_id": partner.id})
        selected_value = finished_line.product_template_value_ids
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": finished_template.product_variant_id.id,
            "product_uom_qty": 1.0,
            "product_uom": finished_template.uom_id.id,
            "width_cm": 100.0,
            "height_cm": 50.0,
            "product_template_attribute_value_ids": [
                Command.set(selected_value.ids),
            ],
        })
        resolved_components = sale_line._link_dimension_components_from_bom(
            selected_value
        )
        self.assertEqual(resolved_components[selected_value.id], component)
        self.assertNotEqual(
            resolved_components[selected_value.id],
            generic_component,
        )
        dynamic_bom = sale_line._create_dimension_bom(
            selected_value,
            resolved_components,
        )
        self.assertEqual(dynamic_bom.bom_line_ids.product_id, component)
        self.assertIn(
            dynamic_value,
            component.product_template_attribute_value_ids.product_attribute_value_id,
        )

        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        move = self.env["stock.move"].create({
            "name": "Compra exacta de acrílico",
            "product_id": component.id,
            "product_uom_qty": 0.8,
            "product_uom": component.uom_id.id,
            "location_id": warehouse.lot_stock_id.id,
            "location_dest_id": component.property_stock_production.id,
            "picking_type_id": warehouse.manu_type_id.id,
            "dimension_value_id": finished_line.product_template_value_ids.id,
            "company_id": self.env.company.id,
        })
        procurement_values = move._prepare_procurement_values()
        self.assertEqual(procurement_values["supplierinfo_id"], variant_seller)
        self.assertLess(move.product_uom_qty, variant_seller.min_qty)

        purchase_order = self.env["purchase.order"].create({
            "partner_id": variant_vendor.id,
            "company_id": self.env.company.id,
            "currency_id": variant_seller.currency_id.id,
        })
        procurement_values.update({
            "supplier": variant_seller,
            "propagate_cancel": True,
        })
        purchase_line_values = self.env[
            "purchase.order.line"
        ]._prepare_purchase_order_line_from_procurement(
            component,
            move.product_uom_qty,
            move.product_uom,
            warehouse.lot_stock_id,
            move.name,
            "Prueba de atributo dinamico adicional",
            self.env.company,
            procurement_values,
            purchase_order,
        )
        self.assertAlmostEqual(purchase_line_values["price_unit"], 300.0)

        variant_seller.dimension_attribute_value_id = False
        self.assertFalse(variant_seller.product_id)

    def test_component_resolution_uses_complete_template_variant_mode(self):
        selected_attribute = self.env["product.attribute"].create({
            "name": "Característica instantánea",
            "create_variant": "always",
            "dimension_type": "area",
            "component_required": True,
        })
        selected_value = self.env["product.attribute.value"].create({
            "name": "Valor solicitado",
            "attribute_id": selected_attribute.id,
        })
        auxiliary_attribute = self.env["product.attribute"].create({
            "name": "Característica dinámica auxiliar",
            "create_variant": "dynamic",
        })
        auxiliary_value = self.env["product.attribute.value"].create({
            "name": "Presentación estándar",
            "attribute_id": auxiliary_attribute.id,
        })
        auxiliary_alternative = self.env["product.attribute.value"].create({
            "name": "Presentación alternativa",
            "attribute_id": auxiliary_attribute.id,
        })
        base_template = self.env["product.template"].create({
            "name": "Componente Base extensible",
            "type": "consu",
            "is_storable": True,
            "purchase_ok": True,
        })
        placeholder = base_template.product_variant_id
        self.env["product.template.attribute.line"].create({
            "product_tmpl_id": base_template.id,
            "attribute_id": selected_attribute.id,
            "value_ids": [Command.set(selected_value.ids)],
        })
        self.env["product.template.attribute.line"].create({
            "product_tmpl_id": base_template.id,
            "attribute_id": auxiliary_attribute.id,
            "value_ids": [
                Command.set((auxiliary_value | auxiliary_alternative).ids),
            ],
        })
        finished_template = self.env["product.template"].create({
            "name": "Producto con características futuras",
            "dimension_enabled": True,
        })
        finished_line = self.env["product.template.attribute.line"].create({
            "product_tmpl_id": finished_template.id,
            "attribute_id": selected_attribute.id,
            "value_ids": [Command.set(selected_value.ids)],
        })
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": finished_template.uom_id.id,
            "bom_line_ids": [Command.create({
                "product_id": placeholder.id,
                "product_qty": 1.0,
                "product_uom_id": base_template.uom_id.id,
                "dimension_attribute_id": selected_attribute.id,
            })],
        })

        component = (
            finished_line.product_template_value_ids
            ._get_or_create_bom_component(bom.bom_line_ids)
        )

        self.assertTrue(component)
        self.assertEqual(component.product_tmpl_id, base_template)
        component_values = component.product_template_attribute_value_ids.mapped(
            "product_attribute_value_id"
        )
        self.assertIn(
            selected_value,
            component_values,
        )
        self.assertIn(
            auxiliary_value,
            component_values,
        )
        self.assertNotEqual(component, placeholder)

    def test_unmapped_base_line_is_repaired_and_resolved_exactly(self):
        attribute = self.env["product.attribute"].create({
            "name": "Atributo adicional genérico",
            "create_variant": "dynamic",
            "dimension_type": "area",
            "component_required": True,
        })
        attribute_value = self.env["product.attribute.value"].create({
            "name": "Opción exacta",
            "attribute_id": attribute.id,
            "component_internal_reference": "GEN-EXACT-001",
        })
        base_template = self.env["product.template"].create({
            "name": "Componente genérico (Base)",
            "type": "consu",
            "is_storable": True,
            "purchase_ok": True,
        })
        base_product = base_template.product_variant_id
        attribute_value.component_product_id = base_product
        finished_template = self.env["product.template"].create({
            "name": "Producto configurable genérico",
            "dimension_enabled": True,
        })
        finished_line = self.env["product.template.attribute.line"].create({
            "product_tmpl_id": finished_template.id,
            "attribute_id": attribute.id,
            "value_ids": [Command.set(attribute_value.ids)],
        })
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": finished_template.uom_id.id,
            "bom_line_ids": [Command.create({
                "product_id": base_product.id,
                "product_qty": 1.0,
                "product_uom_id": base_template.uom_id.id,
            })],
        })
        partner = self.env["res.partner"].create({
            "name": "Cliente de atributo genérico",
        })
        order = self.env["sale.order"].create({"partner_id": partner.id})
        selected_value = finished_line.product_template_value_ids
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": finished_template.product_variant_id.id,
            "product_uom_qty": 1.0,
            "product_uom": finished_template.uom_id.id,
            "width_cm": 100.0,
            "height_cm": 50.0,
            "product_template_attribute_value_ids": [
                Command.set(selected_value.ids),
            ],
        })

        resolved_components = sale_line._link_dimension_components_from_bom(
            selected_value
        )
        component = resolved_components[selected_value.id]

        self.assertEqual(bom.bom_line_ids.dimension_attribute_id, attribute)
        self.assertTrue(component)
        self.assertIn(
            attribute_value,
            component.product_template_attribute_value_ids.mapped(
                "product_attribute_value_id"
            ),
        )
        self.assertEqual(component.default_code, "GEN-EXACT-001")
        self.assertIn("[GEN-EXACT-001]", component.display_name)

    def test_component_reference_is_required_before_confirmation(self):
        self.attribute_value.component_internal_reference = False
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": self.finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": self.finished_template.uom_id.id,
            "bom_line_ids": [Command.create({
                "product_id": self.placeholder.id,
                "product_qty": 1.0,
                "product_uom_id": self.placeholder.uom_id.id,
                "dimension_attribute_id": self.attribute.id,
            })],
        })
        partner = self.env["res.partner"].create({
            "name": "Cliente sin referencia de componente",
        })
        order = self.env["sale.order"].create({"partner_id": partner.id})
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.finished_template.product_variant_id.id,
            "product_uom_qty": 1.0,
            "product_uom": self.finished_template.uom_id.id,
            "width_cm": 100.0,
            "height_cm": 50.0,
            "product_no_variant_attribute_value_ids": [
                Command.set(self.ptav.ids),
            ],
        })

        with self.assertRaisesRegex(ValidationError, "referencia interna"):
            sale_line._validate_dimension_configuration()
        self.assertTrue(bom)

    def test_dynamic_bom_adds_new_selected_attribute_without_template_line(self):
        future_attribute = self.env["product.attribute"].create({
            "name": "Característica futura",
            "create_variant": "no_variant",
            "dimension_type": "area",
            "component_required": True,
        })
        future_component = self.env["product.product"].create({
            "name": "Componente futuro exacto",
            "default_code": "FUT-EXACT-001",
            "type": "consu",
            "is_storable": True,
        })
        future_value = self.env["product.attribute.value"].create({
            "name": "Nueva opción",
            "attribute_id": future_attribute.id,
            "component_product_id": future_component.id,
        })
        future_line = self.env["product.template.attribute.line"].create({
            "product_tmpl_id": self.finished_template.id,
            "attribute_id": future_attribute.id,
            "value_ids": [Command.set(future_value.ids)],
        })
        future_ptav = future_line.product_template_value_ids
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": self.finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": self.finished_template.uom_id.id,
            "bom_line_ids": [Command.create({
                "product_id": self.placeholder.id,
                "product_qty": 1.0,
                "product_uom_id": self.placeholder.uom_id.id,
                "dimension_attribute_id": self.attribute.id,
            })],
        })
        partner = self.env["res.partner"].create({
            "name": "Cliente con característica futura",
        })
        order = self.env["sale.order"].create({"partner_id": partner.id})
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.finished_template.product_variant_id.id,
            "product_uom_qty": 1.0,
            "product_uom": self.finished_template.uom_id.id,
            "width_cm": 100.0,
            "height_cm": 50.0,
            "product_no_variant_attribute_value_ids": [
                Command.set((self.ptav | future_ptav).ids),
            ],
        })
        selected_values = sale_line._get_selected_dimension_values()
        resolved_components = sale_line._link_dimension_components_from_bom(
            selected_values
        )

        dynamic_bom = sale_line._create_dimension_bom(
            selected_values,
            resolved_components,
        )

        self.assertEqual(
            set(dynamic_bom.bom_line_ids.product_id.ids),
            {self.component.id, future_component.id},
        )
        self.assertEqual(
            set(dynamic_bom.bom_line_ids.dimension_value_id.ids),
            set(selected_values.ids),
        )

    def test_placeholder_base_is_not_accepted_as_selected_component(self):
        self.attribute_value.write({
            "component_product_id": False,
            "component_internal_reference": "BASE-NO-EXACTA",
        })
        self.placeholder.default_code = "BASE-NO-EXACTA"
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": self.finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": self.finished_template.uom_id.id,
            "bom_line_ids": [Command.create({
                "product_id": self.placeholder.id,
                "product_qty": 1.0,
                "product_uom_id": self.placeholder.uom_id.id,
                "dimension_attribute_id": self.attribute.id,
            })],
        })
        partner = self.env["res.partner"].create({
            "name": "Cliente sin componente exacto",
        })
        order = self.env["sale.order"].create({"partner_id": partner.id})
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.finished_template.product_variant_id.id,
            "product_uom_qty": 1.0,
            "product_uom": self.finished_template.uom_id.id,
            "width_cm": 100.0,
            "height_cm": 50.0,
            "product_no_variant_attribute_value_ids": [
                Command.set(self.ptav.ids),
            ],
        })

        resolved_components = sale_line._link_dimension_components_from_bom(
            sale_line._get_selected_dimension_values()
        )

        self.assertFalse(resolved_components[self.ptav.id])
        self.assertEqual(bom.bom_line_ids.product_id, self.placeholder)
        with self.assertRaises(ValidationError):
            sale_line._validate_dimension_configuration()
        self.assertEqual(
            self.attribute_value.component_product_id,
            self.placeholder,
            "La búsqueda por referencia puede encontrar el Base, pero no debe usarlo.",
        )

    def test_dimension_quantities_and_explicit_zero_price(self):
        self.assertAlmostEqual(
            self.ptav._get_component_quantity(1.92, 5.6, 2.0),
            11.2,
        )
        self.assertAlmostEqual(
            self.ptav._get_dimension_sale_amount(1.92, 5.6),
            560.0,
        )

        self.ptav.write({
            "pricing_mode": "area",
            "dimension_price": 0.0,
            "price_extra": 999.0,
        })
        self.assertEqual(
            self.ptav._get_dimension_sale_amount(1.92, 5.6),
            0.0,
            "El modo explícito debe permitir una tarifa dimensional igual a cero.",
        )

    def test_configurator_keeps_unit_extra_price(self):
        self.ptav.write({
            "price_extra": 742.0,
            "pricing_mode": "attribute",
            "dimension_price": 0.0,
        })
        standard_information = {
            "price": 1242.0,
            "attribute_lines": [{
                "attribute_values": [{
                    "id": self.ptav.id,
                    "price_extra": 742.0,
                }],
            }],
        }
        controller = DimensionSaleProductConfiguratorController()

        with patch.object(
            SaleProductConfiguratorController,
            "_get_product_information",
            return_value=standard_information,
        ):
            information = controller._get_product_information(
                self.finished_template,
                self.ptav,
                self.env.company.currency_id,
                self.env["product.pricelist"],
                None,
                m2=3.6,
                ml=7.6,
            )

        value_information = information["attribute_lines"][0][
            "attribute_values"
        ][0]
        self.assertEqual(value_information["price_extra"], 742.0)
        self.assertEqual(information["price"], 1242.0)
        self.assertEqual(
            value_information["internal_reference"],
            "MOL-NOG-001",
        )

    def test_small_and_large_dimensions(self):
        small = self.env["sale.order.line"].new({
            "width_cm": 10.0,
            "height_cm": 10.0,
        })
        large = self.env["sale.order.line"].new({
            "width_cm": 200.0,
            "height_cm": 500.0,
        })
        (small | large)._compute_dimensions()
        self.assertAlmostEqual(small.m2, 0.01)
        self.assertAlmostEqual(small.ml, 0.4)
        self.assertAlmostEqual(large.m2, 10.0)
        self.assertAlmostEqual(large.ml, 14.0)

    def test_price_dependencies_are_precomputed(self):
        sale_line_fields = self.env["sale.order.line"]._fields
        self.assertTrue(sale_line_fields["m2"].precompute)
        self.assertTrue(sale_line_fields["ml"].precompute)
        self.assertTrue(sale_line_fields["base_dimension_price"].precompute)
        self.assertTrue(sale_line_fields["price_unit"].precompute)

    def test_component_factor_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.ptav.component_qty_factor = 0.0

    def test_mo_replaces_placeholder_with_exact_component(self):
        self.ptav.write({
            "pricing_mode": "perimeter",
            "dimension_price": 100.0,
        })
        partner = self.env["res.partner"].create({"name": "Cliente Mocalli"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.finished_template.product_variant_id.id,
            "product_uom_qty": 1.0,
            "product_uom": self.finished_template.uom_id.id,
            "width_cm": 120.0,
            "height_cm": 160.0,
            "product_no_variant_attribute_value_ids": [Command.set(self.ptav.ids)],
        })
        self.assertAlmostEqual(sale_line.m2, 1.92)
        self.assertAlmostEqual(sale_line.ml, 5.6)
        self.assertAlmostEqual(sale_line.base_dimension_price, 1060.0)
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": self.finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": self.finished_template.uom_id.id,
            "bom_line_ids": [Command.create({
                "product_id": self.placeholder.id,
                "product_qty": 1.0,
                "product_uom_id": self.placeholder.uom_id.id,
                "dimension_attribute_id": self.attribute.id,
            })],
        })
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        production = self.env["mrp.production"].create({
            "product_id": self.finished_template.product_variant_id.id,
            "product_qty": 1.0,
            "product_uom_id": self.finished_template.uom_id.id,
            "bom_id": bom.id,
            "picking_type_id": warehouse.manu_type_id.id,
            "location_src_id": warehouse.manu_type_id.default_location_src_id.id,
            "location_dest_id": warehouse.manu_type_id.default_location_dest_id.id,
            "dimension_sale_line_id": sale_line.id,
            "dimension_width_cm": 120.0,
            "dimension_height_cm": 160.0,
            "dimension_m2": 1.92,
            "dimension_ml": 5.6,
            "dimension_value_ids": [Command.set(self.ptav.ids)],
        })

        active_raw_moves = production.move_raw_ids.filtered(
            lambda move: move.state != "cancel"
        )
        self.assertNotIn(self.placeholder, active_raw_moves.product_id)
        exact_move = active_raw_moves.filtered(
            lambda move: move.dimension_value_id == self.ptav
        )
        self.assertEqual(exact_move.product_id, self.component)
        self.assertAlmostEqual(exact_move.product_uom_qty, 5.6)
        self.assertEqual(exact_move.bom_line_id, bom.bom_line_ids)
        self.assertEqual(exact_move.procure_method, "make_to_order")
        self.assertIn(warehouse.buy_pull_id.route_id, exact_move.route_ids)

        production.action_confirm()
        purchase_line = self.env["purchase.order.line"].search([
            ("product_id", "=", self.component.id),
            ("move_dest_ids", "in", exact_move.ids),
        ], limit=1)
        self.assertTrue(purchase_line)
        self.assertEqual(purchase_line.order_id.partner_id, self.vendor)

    def test_sale_confirmation_creates_mo_and_rfq_for_exact_component(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        warehouse.buy_to_resupply = True
        self.finished_template.route_ids = warehouse.manufacture_pull_id.route_id
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": self.finished_template.id,
            "product_qty": 1.0,
            "product_uom_id": self.finished_template.uom_id.id,
            "bom_line_ids": [Command.create({
                "product_id": self.placeholder.id,
                "product_qty": 1.0,
                "product_uom_id": self.placeholder.uom_id.id,
                "dimension_attribute_id": self.attribute.id,
            })],
        })
        partner = self.env["res.partner"].create({"name": "Cliente venta a compra"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.finished_template.product_variant_id.id,
            "product_uom_qty": 2.0,
            "product_uom": self.finished_template.uom_id.id,
            "width_cm": 120.0,
            "height_cm": 160.0,
            "product_no_variant_attribute_value_ids": [Command.set(self.ptav.ids)],
        })

        order.action_confirm()

        dynamic_bom = sale_line.dimension_bom_id
        self.assertTrue(dynamic_bom.is_dimension_dynamic)
        self.assertFalse(dynamic_bom.active)
        self.assertEqual(dynamic_bom.dimension_source_bom_id, bom)
        self.assertEqual(dynamic_bom.bom_line_ids.product_id, self.component)
        self.assertEqual(dynamic_bom.bom_line_ids.dimension_value_id, self.ptav)
        self.assertAlmostEqual(dynamic_bom.bom_line_ids.product_qty, 5.6)
        production = self.env["mrp.production"].search([
            ("dimension_sale_line_id", "=", sale_line.id),
            ("bom_id", "=", dynamic_bom.id),
        ], limit=1)
        self.assertTrue(production)
        exact_move = production.move_raw_ids.filtered(
            lambda move: move.dimension_value_id == self.ptav and move.state != "cancel"
        )
        self.assertEqual(exact_move.product_id, self.component)
        self.assertIn("[MOL-NOG-001]", exact_move.product_id.display_name)
        self.assertAlmostEqual(exact_move.product_uom_qty, 11.2)
        purchase_line = self.env["purchase.order.line"].search([
            ("product_id", "=", self.component.id),
            ("move_dest_ids", "in", exact_move.ids),
        ], limit=1)
        self.assertTrue(purchase_line)
        self.assertEqual(purchase_line.product_id, exact_move.product_id)
        self.assertIn("[MOL-NOG-001]", purchase_line.product_id.display_name)
        self.assertEqual(purchase_line.order_id.partner_id, self.vendor)
