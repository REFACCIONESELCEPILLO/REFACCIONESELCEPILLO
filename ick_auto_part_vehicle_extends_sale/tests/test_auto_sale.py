# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestElcepilloAutoSale(TransactionCase):
    """Tests for the automotive panel of the sale order form."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Cliente Autopartes",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Filtro de aceite",
            "default_code": "TST-FILTRO",
            "list_price": 100.0,
            "sale_ok": True,
        })
        cls.alternative = cls.env["product.product"].create({
            "name": "Filtro de aire",
            "default_code": "TST-AIRE",
            "list_price": 150.0,
            "sale_ok": True,
        })
        cls.accessory = cls.env["product.product"].create({
            "name": "Llave de tuercas",
            "default_code": "TST-LLAVE",
            "list_price": 50.0,
            "sale_ok": True,
        })
        cls.order = cls.env["sale.order"].create({
            "partner_id": cls.partner.id,
            "order_line": [(0, 0, {
                "product_id": cls.product.id,
                "product_uom_qty": 1.0,
            })],
        })

    def test_panel_structure(self):
        """The panel must always expose the expected sections."""
        panel = self.order.x_auto_panel
        self.assertIsInstance(panel, dict)
        for key in (
            "active_product", "compatible", "equivalents", "optional",
            "accessories", "alternatives",
        ):
            self.assertIn(key, panel, "Falta la sección %s del panel" % key)

    def test_cross_sell_sections(self):
        """Optional / accessory / alternative products of the order lines."""
        template = self.product.product_tmpl_id
        template.write({
            "optional_product_ids": [(6, 0, self.alternative.product_tmpl_id.ids)],
            "accessory_product_ids": [(6, 0, self.accessory.ids)],
        })
        # ``x_auto_panel`` is not stored and its compute does not depend on the
        # written cross-sell fields: the cached value must be dropped.
        self.order.invalidate_recordset(["x_auto_panel"])
        panel = self.order.x_auto_panel
        optional_ids = {item["id"] for item in panel["optional"]}
        accessory_ids = {item["id"] for item in panel["accessories"]}
        self.assertIn(self.alternative.id, optional_ids)
        self.assertIn(self.accessory.id, accessory_ids)
        # A product already in the order is never suggested again.
        self.assertNotIn(self.product.id, optional_ids | accessory_ids)

    def test_add_product(self):
        """``action_auto_add_product`` adds or increments order lines."""
        self.assertEqual(len(self.order.order_line), 1)
        self.order.action_auto_add_product(self.alternative.id)
        self.assertEqual(len(self.order.order_line), 2)
        # Adding an existing product increments its quantity.
        self.order.action_auto_add_product(self.alternative.id)
        self.assertEqual(len(self.order.order_line), 2)
        line = self.order.order_line.filtered(
            lambda line: line.product_id == self.alternative)
        self.assertEqual(line.product_uom_qty, 2.0)

    def test_panel_product_payload(self):
        """Suggested products expose the fields consumed by the OWL panel."""
        template = self.product.product_tmpl_id
        template.write({
            "optional_product_ids": [(6, 0, self.alternative.product_tmpl_id.ids)],
        })
        # Non stored compute field: force a fresh computation (see above).
        self.order.invalidate_recordset(["x_auto_panel"])
        panel = self.order.x_auto_panel
        item = panel["optional"][0]
        for key in (
            "id", "name", "default_code", "brand", "price", "image_url",
            "available_qty", "uom",
        ):
            self.assertIn(key, item)
        self.assertEqual(item["default_code"], "TST-AIRE")
        self.assertIsInstance(item["available_qty"], float)

    def test_recommendation_becomes_active_product(self):
        """A newly added suggestion drives the next recommendations."""
        self.order.x_auto_context_product_id = self.product
        self.order.action_auto_add_product(self.alternative.id)
        self.assertEqual(self.order.x_auto_context_product_id, self.alternative)

    def test_active_product_drives_commercial_relations(self):
        """Only relations belonging to the active product are presented."""
        self.product.product_tmpl_id.optional_product_ids = (
            self.alternative.product_tmpl_id
        )
        self.order.x_auto_context_product_id = self.product
        self.order.invalidate_recordset(["x_auto_panel"])
        panel = self.order.x_auto_panel
        self.assertEqual(panel["active_product"]["id"], self.product.id)
        self.assertIn(
            self.alternative.id,
            {item["id"] for item in panel["optional"]},
        )

    def test_line_can_be_selected_as_active_context(self):
        line = self.order.order_line.filtered(
            lambda sale_line: sale_line.product_id == self.product
        )
        line.action_auto_set_context_product()
        self.assertEqual(self.order.x_auto_context_product_id, self.product)

    def test_sale_line_exposes_sellable_availability(self):
        """The detail exposes free quantity for the quotation warehouse."""
        line = self.order.order_line.filtered(
            lambda sale_line: sale_line.product_id == self.product
        )
        self.assertIsInstance(line.x_auto_available_qty, float)
        action = line.action_auto_open_warehouse_availability()
        self.assertEqual(action["res_model"], "product.warehouse.availability")
        self.assertEqual(action["target"], "new")
        self.assertIn(
            ("product_id", "=", self.product.id),
            action["domain"],
        )
