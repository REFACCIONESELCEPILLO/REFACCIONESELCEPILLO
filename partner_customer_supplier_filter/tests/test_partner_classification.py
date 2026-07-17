from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerClassification(TransactionCase):
    def test_customer_created_from_sale_is_classified(self):
        partner = self.env["res.partner"].with_context(
            res_partner_search_mode="customer"
        ).create({"name": "Cliente desde ventas"})

        categories = partner._classification_categories()
        self.assertTrue(partner.is_customer)
        self.assertFalse(partner.is_supplier)
        self.assertGreaterEqual(partner.customer_rank, 1)
        self.assertIn(categories["customer"], partner.category_id)

    def test_supplier_created_from_purchase_is_classified(self):
        partner = self.env["res.partner"].with_context(
            res_partner_search_mode="supplier"
        ).create({"name": "Proveedor desde compras"})

        categories = partner._classification_categories()
        self.assertTrue(partner.is_supplier)
        self.assertFalse(partner.is_customer)
        self.assertGreaterEqual(partner.supplier_rank, 1)
        self.assertIn(categories["supplier"], partner.category_id)

    def test_manual_checkbox_synchronizes_category(self):
        partner = self.env["res.partner"].create({"name": "Contacto manual"})
        categories = partner._classification_categories()

        partner.is_customer = True
        self.assertIn(categories["customer"], partner.category_id)

        partner.is_customer = False
        self.assertNotIn(categories["customer"], partner.category_id)

    def test_manual_category_synchronizes_checkbox(self):
        partner = self.env["res.partner"].create({"name": "Contacto etiquetado"})
        categories = partner._classification_categories()

        partner.write({
            "category_id": [Command.link(categories["supplier"].id)],
        })
        self.assertTrue(partner.is_supplier)

        partner.write({
            "category_id": [Command.unlink(categories["supplier"].id)],
        })
        self.assertFalse(partner.is_supplier)

    def test_partner_can_be_customer_and_supplier(self):
        partner = self.env["res.partner"].create({
            "name": "Cliente y proveedor",
            "is_customer": True,
            "is_supplier": True,
        })

        categories = partner._classification_categories()
        self.assertIn(categories["customer"], partner.category_id)
        self.assertIn(categories["supplier"], partner.category_id)
        self.assertGreaterEqual(partner.customer_rank, 1)
        self.assertGreaterEqual(partner.supplier_rank, 1)
