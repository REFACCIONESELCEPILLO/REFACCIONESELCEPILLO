from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


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
